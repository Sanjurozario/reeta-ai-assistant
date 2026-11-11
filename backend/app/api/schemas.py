import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# System Schemas
# ============================================================================

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    active_provider: str
    uptime_seconds: float
    timestamp: datetime


class EmergencyStopResponse(BaseModel):
    success: bool
    message: str
    timestamp: datetime


class ModelStatusResponse(BaseModel):
    default_provider: str
    providers: Dict[str, Any]


# ============================================================================
# Task Schemas
# ============================================================================

class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    objective: str = Field(..., min_length=1)
    priority: int = Field(default=5, ge=1, le=10)
    user_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None


class TaskStepResponse(BaseModel):
    id: uuid.UUID
    step_number: int
    title: str
    agent_type: str
    status: str
    input_payload: Dict[str, Any]
    output_payload: Dict[str, Any]
    error_log: Optional[str]
    created_at: datetime


class TaskDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    objective: str
    status: str
    priority: int
    plan: Dict[str, Any]
    result: Dict[str, Any]
    error_detail: Optional[Dict[str, Any]]
    verification_status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    steps: List[TaskStepResponse] = []


class TaskCancelResponse(BaseModel):
    success: bool
    task_id: uuid.UUID
    status: str


# ============================================================================
# Permission & Approval Schemas
# ============================================================================

class ApprovalTicketResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    task_step_id: Optional[uuid.UUID]
    description: str
    action_type: str
    target_resource: str
    risk_level: str
    approval_token: str
    status: str
    requested_at: datetime


class ApprovalDecisionRequest(BaseModel):
    ticket_id: str
    decision: str = Field(..., pattern="^(approve|reject)$")
    ttl_seconds: Optional[int] = 300


class ApprovalDecisionResponse(BaseModel):
    success: bool
    ticket_id: str
    status: str
    signed_token: Optional[str] = None
    error: Optional[str] = None


class ScopedPermissionRequest(BaseModel):
    user_id: uuid.UUID
    resource_pattern: str
    action: str
    scope: str = "workspace"
    ttl_hours: Optional[int] = None


class ScopedPermissionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    resource_pattern: str
    action: str
    scope: str
    expires_at: Optional[datetime]
    created_at: datetime


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor: str
    action_type: str
    target_resource: Optional[str]
    payload: Dict[str, Any]
    status: str
    timestamp: datetime
