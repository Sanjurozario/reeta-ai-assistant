import fnmatch
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditLog,
    Permission,
    PolicyTier,
)
from app.permissions.policy import ActionTier, PolicyEngine
from app.permissions.tickets import TicketManager

logger = logging.getLogger("reeta.permissions")


class AuthCheckResult(BaseModel):
    allowed: bool
    tier: ActionTier
    reason: str
    ticket_id: Optional[str] = None
    requires_approval: bool = False


class PermissionService:
    """Central Zero-Trust security gateway that authorises all agent actions."""

    @classmethod
    async def evaluate_and_authorize(
        cls,
        session: AsyncSession,
        actor: str,
        action: str,
        target_resource: str,
        task_id: Optional[uuid.UUID] = None,
        task_step_id: Optional[uuid.UUID] = None,
        approval_token: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> AuthCheckResult:
        """
        Evaluates a tool action request.
        If autonomous, grants immediately.
        If approval required:
          - If a valid approval token is provided, verifies it and grants.
          - If active scoped permission exists in DB, grants.
          - Otherwise, creates an ApprovalRequest ticket and halts execution.
        If restricted, rejects permanently.
        Writes to AuditLog on all decisions.
        """
        # 1. Base Policy Classification
        tier, reason = PolicyEngine.evaluate(action=action, target_resource=target_resource)

        # 2. Handle Restricted Tier (Hard Deny)
        if tier == ActionTier.RESTRICTED:
            await cls._record_audit(
                session=session,
                actor=actor,
                action_type=action,
                target_resource=target_resource,
                status="BLOCKED",
                user_id=user_id,
                payload={"reason": reason, "tier": tier.value},
            )
            return AuthCheckResult(allowed=False, tier=tier, reason=reason)

        # 3. Handle Autonomous Tier (Auto Grant)
        if tier == ActionTier.AUTONOMOUS:
            await cls._record_audit(
                session=session,
                actor=actor,
                action_type=action,
                target_resource=target_resource,
                status="AUTONOMOUS_APPROVED",
                user_id=user_id,
                payload={"reason": reason, "tier": tier.value},
            )
            return AuthCheckResult(allowed=True, tier=tier, reason=reason)

        # 4. Handle Approval-Required Tier
        # 4a. Check if valid cryptographic token was supplied
        if approval_token:
            is_valid, token_msg = TicketManager.verify_token(
                token=approval_token,
                expected_action=action,
                expected_resource=target_resource,
            )
            if is_valid:
                await cls._record_audit(
                    session=session,
                    actor=actor,
                    action_type=action,
                    target_resource=target_resource,
                    status="TOKEN_APPROVED",
                    user_id=user_id,
                    payload={"token_msg": token_msg},
                )
                return AuthCheckResult(allowed=True, tier=tier, reason="Authorized via valid cryptographic approval token.")
            else:
                logger.warning(f"Invalid approval token presented: {token_msg}")

        # 4b. Check if active persistent scoped permission exists in DB
        if user_id:
            now = datetime.now(timezone.utc)
            query = select(Permission).where(
                Permission.user_id == user_id,
                Permission.action == action,
                (Permission.expires_at == None) | (Permission.expires_at > now),
            )
            result = await session.execute(query)
            permissions = result.scalars().all()
            for perm in permissions:
                if fnmatch.fnmatch(target_resource.lower(), perm.resource_pattern.lower()):
                    await cls._record_audit(
                        session=session,
                        actor=actor,
                        action_type=action,
                        target_resource=target_resource,
                        status="PERSISTENT_POLICY_APPROVED",
                        user_id=user_id,
                        payload={"permission_id": str(perm.id), "pattern": perm.resource_pattern},
                    )
                    return AuthCheckResult(
                        allowed=True,
                        tier=tier,
                        reason=f"Authorized by persistent permission scope '{perm.resource_pattern}'.",
                    )

        # 4c. Not pre-approved: Issue ephemeral ApprovalRequest ticket
        ticket_id = TicketManager.create_ticket_id()
        if task_id:
            approval_record = ApprovalRequest(
                task_id=task_id,
                task_step_id=task_step_id,
                description=f"Agent '{actor}' requests permission to perform '{action}' on '{target_resource}'.",
                action_type=action,
                target_resource=target_resource,
                risk_level="medium",
                approval_token=ticket_id,
                status=ApprovalStatus.PENDING.value,
            )
            session.add(approval_record)
            await session.commit()

        await cls._record_audit(
            session=session,
            actor=actor,
            action_type=action,
            target_resource=target_resource,
            status="APPROVAL_REQUIRED",
            user_id=user_id,
            payload={"ticket_id": ticket_id, "reason": reason},
        )

        return AuthCheckResult(
            allowed=False,
            tier=tier,
            reason=reason,
            ticket_id=ticket_id,
            requires_approval=True,
        )

    @classmethod
    async def resolve_ticket(
        cls,
        session: AsyncSession,
        ticket_id: str,
        decision: str,  # "approve" | "reject"
        user_id: Optional[uuid.UUID] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        User approves or rejects a pending ticket.
        If approved, issues signed JWT token for the tool executor.
        """
        # Match by approval_token or primary key UUID
        query = select(ApprovalRequest).where(ApprovalRequest.approval_token == ticket_id)
        result = await session.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            try:
                u = uuid.UUID(ticket_id)
                query = select(ApprovalRequest).where(ApprovalRequest.id == u)
                result = await session.execute(query)
                record = result.scalar_one_or_none()
            except Exception:
                pass

        if not record:
            return {"success": False, "error": f"Ticket '{ticket_id}' not found."}

        if record.status != ApprovalStatus.PENDING.value:
            return {"success": False, "error": f"Ticket is already resolved ({record.status})."}

        now = datetime.now(timezone.utc)
        record.responded_at = now
        record.responded_by = user_id

        if decision.lower() == "approve":
            record.status = ApprovalStatus.APPROVED.value
            signed_token = TicketManager.issue_signed_token(
                ticket_id=ticket_id,
                action=record.action_type,
                target_resource=record.target_resource,
                ttl_seconds=ttl_seconds,
            )
            await cls._record_audit(
                session=session,
                actor="user",
                action_type=record.action_type,
                target_resource=record.target_resource,
                status="USER_APPROVED_TICKET",
                user_id=user_id,
                payload={"ticket_id": ticket_id},
            )
            return {
                "success": True,
                "ticket_id": ticket_id,
                "status": "approved",
                "signed_token": signed_token,
            }
        else:
            record.status = ApprovalStatus.REJECTED.value
            await cls._record_audit(
                session=session,
                actor="user",
                action_type=record.action_type,
                target_resource=record.target_resource,
                status="USER_REJECTED_TICKET",
                user_id=user_id,
                payload={"ticket_id": ticket_id},
            )
            return {"success": True, "ticket_id": ticket_id, "status": "rejected"}

    @classmethod
    async def grant_scoped_permission(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        resource_pattern: str,
        action: str,
        expires_at: Optional[datetime] = None,
        scope: str = "workspace",
    ) -> Permission:
        """Creates a persistent scoped permission in DB."""
        perm = Permission(
            user_id=user_id,
            resource_pattern=resource_pattern,
            action=action,
            tier=PolicyTier.APPROVAL_REQUIRED.value,
            scope=scope,
            expires_at=expires_at,
        )
        session.add(perm)
        await session.commit()
        await session.refresh(perm)
        return perm

    @classmethod
    async def revoke_permission(
        cls,
        session: AsyncSession,
        permission_id: uuid.UUID,
    ) -> bool:
        """Revokes a persistent permission."""
        query = select(Permission).where(Permission.id == permission_id)
        result = await session.execute(query)
        perm = result.scalar_one_or_none()
        if perm:
            await session.delete(perm)
            await session.commit()
            return True
        return False

    @classmethod
    async def _record_audit(
        cls,
        session: Optional[AsyncSession],
        actor: str,
        action_type: str,
        target_resource: str,
        status: str,
        user_id: Optional[uuid.UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
    ):
        if session is not None:
            audit = AuditLog(
                user_id=user_id,
                actor=actor,
                action_type=action_type,
                target_resource=target_resource,
                status=status,
                payload=payload or {},
            )
            session.add(audit)
            await session.flush()
