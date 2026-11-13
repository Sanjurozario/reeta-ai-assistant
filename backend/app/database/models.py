import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    LargeBinary,
    Index,
    JSON,
    Uuid,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB
from sqlalchemy.orm import DeclarativeBase, relationship

try:
    from pgvector.sqlalchemy import Vector
    VectorType = Vector(1536).with_variant(JSON(), "sqlite")
    HAS_PGVECTOR = True
except ImportError:
    VectorType = JSON()
    HAS_PGVECTOR = False

UUIDType = Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql")
JSONType = JSON().with_variant(PG_JSONB, "postgresql")


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PolicyTier(str, Enum):
    AUTONOMOUS = "autonomous"
    APPROVAL_REQUIRED = "approval_required"
    RESTRICTED = "restricted"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ============================================================================
# 1. Identity & Conversations
# ============================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(150), nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    preferences = Column(JSONType, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    permissions = relationship("Permission", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Conversation", nullable=False)
    mode = Column(String(50), default="general", nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    metadata_ = Column("metadata", JSONType, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUIDType, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type = Column(String(30), nullable=False)  # 'user', 'assistant', 'system', 'agent', 'tool'
    agent_name = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    tool_calls = Column(JSONType, default=list, nullable=False)
    tool_results = Column(JSONType, default=list, nullable=False)
    tokens_prompt = Column(Integer, default=0, nullable=False)
    tokens_completion = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


# ============================================================================
# 2. Cognitive Memory & Vector Embeddings
# ============================================================================

class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(UUIDType, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    memory_type = Column(String(50), nullable=False)  # 'episodic', 'semantic', 'procedural', 'preference'
    category = Column(String(100), default="general", nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(VectorType, nullable=True)
    importance_score = Column(Float, default=0.5, nullable=False)
    access_count = Column(Integer, default=0, nullable=False)
    metadata_ = Column("metadata", JSONType, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    user = relationship("User", back_populates="memories")


# ============================================================================
# 3. Autonomous Task Orchestration
# ============================================================================

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUIDType, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    objective = Column(Text, nullable=False)
    status = Column(String(50), default=TaskStatus.PENDING.value, nullable=False, index=True)
    priority = Column(Integer, default=5, nullable=False)
    plan = Column(JSONType, default=dict, nullable=False)
    execution_state = Column(JSONType, default=dict, nullable=False)
    result = Column(JSONType, default=dict, nullable=False)
    error_detail = Column(JSONType, nullable=True)
    verification_status = Column(String(50), default="unverified", nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    user = relationship("User", back_populates="tasks")
    steps = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan", order_by="TaskStep.step_number")
    agent_runs = relationship("AgentRun", back_populates="task", cascade="all, delete-orphan")
    approval_requests = relationship("ApprovalRequest", back_populates="task", cascade="all, delete-orphan")


class TaskStep(Base):
    __tablename__ = "task_steps"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    task_id = Column(UUIDType, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    agent_type = Column(String(50), nullable=False)
    status = Column(String(50), default=TaskStatus.PENDING.value, nullable=False)
    input_payload = Column(JSONType, default=dict, nullable=False)
    output_payload = Column(JSONType, default=dict, nullable=False)
    error_log = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    task = relationship("Task", back_populates="steps")
    __table_args__ = (UniqueConstraint("task_id", "step_number", name="uq_task_step"),)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    task_id = Column(UUIDType, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    task_step_id = Column(UUIDType, ForeignKey("task_steps.id", ondelete="SET NULL"), nullable=True)
    agent_name = Column(String(50), nullable=False)
    model_used = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    execution_state = Column(JSONType, default=dict, nullable=False)
    start_time = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)

    task = relationship("Task", back_populates="agent_runs")
    tool_calls = relationship("ToolCall", back_populates="agent_run", cascade="all, delete-orphan")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    agent_run_id = Column(UUIDType, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    task_step_id = Column(UUIDType, ForeignKey("task_steps.id", ondelete="SET NULL"), nullable=True)
    tool_name = Column(String(100), nullable=False, index=True)
    tool_category = Column(String(50), nullable=False)
    arguments = Column(JSONType, default=dict, nullable=False)
    result = Column(JSONType, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    is_success = Column(Boolean, default=True, nullable=False)
    requires_approval = Column(Boolean, default=False, nullable=False)
    approval_id = Column(UUIDType, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    agent_run = relationship("AgentRun", back_populates="tool_calls")


# ============================================================================
# 4. Security, Approvals & Audit Logging
# ============================================================================

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_pattern = Column(String(255), nullable=False)
    action = Column(String(50), nullable=False)
    tier = Column(String(30), default=PolicyTier.APPROVAL_REQUIRED.value, nullable=False)
    scope = Column(String(50), default="workspace", nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    user = relationship("User", back_populates="permissions")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    task_id = Column(UUIDType, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    task_step_id = Column(UUIDType, ForeignKey("task_steps.id", ondelete="CASCADE"), nullable=True)
    tool_call_id = Column(UUIDType, nullable=True)
    description = Column(Text, nullable=False)
    action_type = Column(String(100), nullable=False)
    target_resource = Column(Text, nullable=False)
    risk_level = Column(String(30), nullable=False)  # 'low', 'medium', 'high', 'critical'
    approval_token = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(30), default=ApprovalStatus.PENDING.value, nullable=False)
    requested_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    responded_by = Column(UUIDType, ForeignKey("users.id"), nullable=True)

    task = relationship("Task", back_populates="approval_requests")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor = Column(String(100), nullable=False, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    target_resource = Column(Text, nullable=True)
    payload = Column(JSONType, default=dict, nullable=False)
    ip_address = Column(String(45), default="127.0.0.1", nullable=False)
    status = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)


# ============================================================================
# 5. Integrations & Scheduled Jobs
# ============================================================================

class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider_name = Column(String(100), nullable=False)
    encrypted_credentials = Column(LargeBinary, nullable=False)
    config = Column(JSONType, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "provider_name", name="uq_user_provider"),)


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    task_payload = Column(JSONType, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
