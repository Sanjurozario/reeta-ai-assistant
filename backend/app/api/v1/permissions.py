import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ApprovalTicketResponse,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ScopedPermissionRequest,
    ScopedPermissionResponse,
    AuditLogResponse,
)
from app.database.models import ApprovalRequest, ApprovalStatus, AuditLog, Permission
from app.database.session import get_db
from app.permissions.service import PermissionService

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("/pending", response_model=List[ApprovalTicketResponse])
async def list_pending_approvals(session: AsyncSession = Depends(get_db)):
    """Lists all active human-in-the-loop approval tickets awaiting user decision."""
    query = (
        select(ApprovalRequest)
        .where(ApprovalRequest.status == ApprovalStatus.PENDING.value)
        .order_by(desc(ApprovalRequest.requested_at))
    )
    res = await session.execute(query)
    records = res.scalars().all()

    return [
        ApprovalTicketResponse(
            id=r.id,
            task_id=r.task_id,
            task_step_id=r.task_step_id,
            description=r.description,
            action_type=r.action_type,
            target_resource=r.target_resource,
            risk_level=r.risk_level,
            approval_token=r.approval_token,
            status=r.status,
            requested_at=r.requested_at,
        )
        for r in records
    ]


@router.post("/respond", response_model=ApprovalDecisionResponse)
async def respond_to_ticket(
    req: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db),
):
    """Submits user decision ('approve' or 'reject') on a pending ticket."""
    result = await PermissionService.resolve_ticket(
        session=session,
        ticket_id=req.ticket_id,
        decision=req.decision,
        ttl_seconds=req.ttl_seconds,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to resolve ticket."))

    return ApprovalDecisionResponse(
        success=True,
        ticket_id=req.ticket_id,
        status=result.get("status", "unknown"),
        signed_token=result.get("signed_token"),
    )


@router.post("/scoped", response_model=ScopedPermissionResponse)
async def create_scoped_permission(
    req: ScopedPermissionRequest,
    session: AsyncSession = Depends(get_db),
):
    """Grants a persistent or time-bounded scoped permission in DB."""
    expires_at = None
    if req.ttl_hours:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=req.ttl_hours)

    perm = await PermissionService.grant_scoped_permission(
        session=session,
        user_id=req.user_id,
        resource_pattern=req.resource_pattern,
        action=req.action,
        expires_at=expires_at,
        scope=req.scope,
    )

    return ScopedPermissionResponse(
        id=perm.id,
        user_id=perm.user_id,
        resource_pattern=perm.resource_pattern,
        action=perm.action,
        scope=perm.scope,
        expires_at=perm.expires_at,
        created_at=perm.created_at,
    )


@router.delete("/{permission_id}")
async def revoke_permission(
    permission_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Revokes a persistent scoped permission."""
    revoked = await PermissionService.revoke_permission(session, permission_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Permission not found.")
    return {"success": True, "message": f"Permission '{permission_id}' revoked."}


@router.get("/audit", response_model=List[AuditLogResponse])
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    actor: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    """Queries security audit trail."""
    query = select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit)
    if actor:
        query = query.where(AuditLog.actor == actor)

    res = await session.execute(query)
    logs = res.scalars().all()

    return [
        AuditLogResponse(
            id=log.id,
            actor=log.actor,
            action_type=log.action_type,
            target_resource=log.target_resource,
            payload=log.payload,
            status=log.status,
            timestamp=log.timestamp,
        )
        for log in logs
    ]
