import asyncio
import time
import uuid
import pytest
from sqlalchemy import select
from app.database.models import User, AuditLog
from app.permissions.policy import ActionTier, PolicyEngine
from app.permissions.tickets import TicketManager
from app.permissions.service import PermissionService


def test_policy_classification_tiers():
    # Tier 1: Autonomous
    tier, _ = PolicyEngine.evaluate(action="web_search", target_resource="https://example.com")
    assert tier == ActionTier.AUTONOMOUS

    # Tier 2: Approval Required
    tier, _ = PolicyEngine.evaluate(action="terminal_execute", target_resource="Get-Process")
    assert tier == ActionTier.APPROVAL_REQUIRED

    # Tier 3: Hard Restricted
    tier, _ = PolicyEngine.evaluate(
        action="read_file",
        target_resource="C:/Windows/System32/config/SAM",
    )
    assert tier == ActionTier.RESTRICTED


def test_ticket_manager_hmac_verification():
    ticket_id = TicketManager.create_ticket_id()
    action = "delete_file"
    resource = "E:/PROJECTS/reeta/temp/old_data.txt"

    # Issue signed token with 10s TTL
    token = TicketManager.issue_signed_token(ticket_id, action, resource, ttl_seconds=10)
    assert token is not None

    # Verify valid token
    valid, msg = TicketManager.verify_token(token, action, resource)
    assert valid is True
    assert "verified" in msg.lower()

    # Verify tampering with target resource
    tampered_valid, tampered_msg = TicketManager.verify_token(
        token, action, "E:/PROJECTS/reeta/different_file.txt"
    )
    assert tampered_valid is False
    assert "mismatch" in tampered_msg.lower()


def test_ticket_manager_token_expiration():
    ticket_id = TicketManager.create_ticket_id()
    action = "powershell_execute"
    resource = "dir"

    # Issue token with 1s TTL
    token = TicketManager.issue_signed_token(ticket_id, action, resource, ttl_seconds=1)
    time.sleep(1.2)

    valid, msg = TicketManager.verify_token(token, action, resource)
    assert valid is False
    assert "expired" in msg.lower()


@pytest.mark.asyncio
async def test_permission_service_autonomous_flow(db_session):
    result = await PermissionService.evaluate_and_authorize(
        session=db_session,
        actor="research_agent",
        action="web_search",
        target_resource="https://duckduckgo.com",
    )
    assert result.allowed is True
    assert result.tier == ActionTier.AUTONOMOUS
    assert result.requires_approval is False


@pytest.mark.asyncio
async def test_permission_service_restricted_flow(db_session):
    result = await PermissionService.evaluate_and_authorize(
        session=db_session,
        actor="file_agent",
        action="read_file",
        target_resource="C:/Windows/System32/config/SAM",
    )
    assert result.allowed is False
    assert result.tier == ActionTier.RESTRICTED


@pytest.mark.asyncio
async def test_permission_service_approval_lifecycle(db_session):
    # 1. Create a User and Task
    user = User(username=f"perm_user_{uuid.uuid4().hex[:6]}", password_hash="hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    from app.database.models import Task
    task = Task(user_id=user.id, title="Test Perm Task", objective="Run delete")
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # 2. Evaluate Tier 2 action -> Should demand approval & issue ticket
    action = "delete_file"
    resource = "E:/PROJECTS/reeta/test_artifact.tmp"
    auth_res = await PermissionService.evaluate_and_authorize(
        session=db_session,
        actor="file_agent",
        action=action,
        target_resource=resource,
        task_id=task.id,
        user_id=user.id,
    )
    assert auth_res.allowed is False
    assert auth_res.requires_approval is True
    assert auth_res.ticket_id is not None
    ticket_id = auth_res.ticket_id

    # 3. User approves ticket
    decision_res = await PermissionService.resolve_ticket(
        session=db_session,
        ticket_id=ticket_id,
        decision="approve",
        user_id=user.id,
    )
    assert decision_res["success"] is True
    assert decision_res["status"] == "approved"
    assert "signed_token" in decision_res
    signed_token = decision_res["signed_token"]

    # 4. Agent re-requests execution with signed token -> Should be allowed!
    post_approval = await PermissionService.evaluate_and_authorize(
        session=db_session,
        actor="file_agent",
        action=action,
        target_resource=resource,
        task_id=task.id,
        approval_token=signed_token,
        user_id=user.id,
    )
    assert post_approval.allowed is True

    # 5. Verify audit logs were written
    audit_q = select(AuditLog).where(AuditLog.target_resource == resource)
    audit_res = await db_session.execute(audit_q)
    logs = audit_res.scalars().all()
    assert len(logs) >= 2

    # Clean up
    await db_session.delete(task)
    await db_session.delete(user)
    await db_session.commit()
