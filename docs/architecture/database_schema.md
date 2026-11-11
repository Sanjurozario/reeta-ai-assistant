# REETA Database Schema Specification
**Database Engine:** PostgreSQL 16 with `pgvector` Extension  
**ORM / Migration Engine:** SQLAlchemy 2.0 (Async) + Alembic

---

## 1. Schema Overview

The REETA database schema is structured into five operational domains:
1. **Identity & Core Conversation:** `users`, `conversations`, `messages`.
2. **Cognitive Memory & Vector Knowledge:** `memories` (pgvector cosine index).
3. **Task Orchestration & Execution:** `tasks`, `task_steps`, `agent_runs`, `tool_calls`.
4. **Security, Permissions & Audit:** `permissions`, `approval_requests`, `audit_logs`.
5. **Automation & Integrations:** `integrations`, `scheduled_jobs`.

---

## 2. PostgreSQL DDL Specification

```sql
-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. Identity & Conversations
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(150),
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    preferences JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    mode VARCHAR(50) DEFAULT 'general' NOT NULL, -- 'general', 'coding', 'research', 'automation'
    is_archived BOOLEAN DEFAULT FALSE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(30) NOT NULL, -- 'user', 'assistant', 'system', 'agent', 'tool'
    agent_name VARCHAR(50), -- e.g. 'research_agent', 'coding_agent'
    content TEXT NOT NULL,
    tool_calls JSONB DEFAULT '[]'::jsonb,
    tool_results JSONB DEFAULT '[]'::jsonb,
    tokens_prompt INTEGER DEFAULT 0,
    tokens_completion INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at ASC);

-- ============================================================================
-- 2. Cognitive Memory & Vector Embeddings
-- ============================================================================

CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    memory_type VARCHAR(50) NOT NULL, -- 'episodic', 'semantic', 'procedural', 'preference'
    category VARCHAR(100) DEFAULT 'general',
    content TEXT NOT NULL,
    embedding vector(1536), -- Supports OpenAI text-embedding-3-small, configurable to 768 or 384
    importance_score FLOAT DEFAULT 0.5 NOT NULL,
    access_count INTEGER DEFAULT 0 NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_accessed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- HNSW Vector Index for ultra-fast approximate nearest neighbor search
CREATE INDEX idx_memories_embedding_hnsw ON memories 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_memories_user_type ON memories(user_id, memory_type);
CREATE INDEX idx_memories_importance ON memories(importance_score DESC);

-- ============================================================================
-- 3. Autonomous Task Orchestration
-- ============================================================================

CREATE TYPE task_status AS ENUM (
    'pending',
    'planning',
    'running',
    'waiting_approval',
    'paused',
    'completed',
    'failed',
    'cancelled'
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    objective TEXT NOT NULL,
    status task_status DEFAULT 'pending' NOT NULL,
    priority INTEGER DEFAULT 5 NOT NULL, -- 1 (lowest) to 10 (highest)
    plan JSONB DEFAULT '{}'::jsonb, -- DAG specification and step sequences
    execution_state JSONB DEFAULT '{}'::jsonb, -- Checkpointed LangGraph state
    result JSONB DEFAULT '{}'::jsonb, -- Final verified outcomes and artifacts
    error_detail JSONB DEFAULT NULL,
    verification_status VARCHAR(50) DEFAULT 'unverified', -- 'unverified', 'verified', 'verification_failed'
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_user ON tasks(user_id, created_at DESC);

CREATE TABLE task_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL, -- 'research', 'coding', 'computer', 'browser', 'file', 'productivity'
    status task_status DEFAULT 'pending' NOT NULL,
    input_payload JSONB DEFAULT '{}'::jsonb,
    output_payload JSONB DEFAULT '{}'::jsonb,
    error_log TEXT,
    retry_count INTEGER DEFAULT 0 NOT NULL,
    max_retries INTEGER DEFAULT 3 NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_task_step UNIQUE(task_id, step_number)
);

CREATE INDEX idx_task_steps_task ON task_steps(task_id, step_number);

CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    task_step_id UUID REFERENCES task_steps(id) ON DELETE SET NULL,
    agent_name VARCHAR(50) NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER DEFAULT 0 NOT NULL,
    completion_tokens INTEGER DEFAULT 0 NOT NULL,
    execution_state JSONB DEFAULT '{}'::jsonb,
    start_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    end_time TIMESTAMPTZ
);

CREATE INDEX idx_agent_runs_task ON agent_runs(task_id);

CREATE TABLE tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    task_step_id UUID REFERENCES task_steps(id) ON DELETE SET NULL,
    tool_name VARCHAR(100) NOT NULL,
    tool_category VARCHAR(50) NOT NULL, -- 'windows', 'browser', 'terminal', 'files', 'documents'
    arguments JSONB NOT NULL,
    result JSONB,
    duration_ms INTEGER,
    is_success BOOLEAN DEFAULT TRUE NOT NULL,
    requires_approval BOOLEAN DEFAULT FALSE NOT NULL,
    approval_id UUID,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_tool_calls_agent ON tool_calls(agent_run_id);
CREATE INDEX idx_tool_calls_name ON tool_calls(tool_name);

-- ============================================================================
-- 4. Security, Approvals & Audit Logging
-- ============================================================================

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_pattern VARCHAR(255) NOT NULL, -- e.g. 'C:/Users/User/Desktop/Projects/*'
    action VARCHAR(50) NOT NULL, -- 'read', 'write', 'execute', 'network_call'
    tier VARCHAR(30) NOT NULL, -- 'autonomous', 'approval_required', 'restricted'
    scope VARCHAR(50) DEFAULT 'workspace' NOT NULL, -- 'system', 'workspace', 'session'
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_permissions_user ON permissions(user_id);

CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    task_step_id UUID REFERENCES task_steps(id) ON DELETE CASCADE,
    tool_call_id UUID,
    description TEXT NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    target_resource TEXT NOT NULL,
    risk_level VARCHAR(30) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    approval_token VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(30) DEFAULT 'pending' NOT NULL, -- 'pending', 'approved', 'rejected', 'expired'
    requested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    responded_at TIMESTAMPTZ,
    responded_by UUID REFERENCES users(id)
);

CREATE INDEX idx_approvals_token ON approval_requests(approval_token);
CREATE INDEX idx_approvals_task_status ON approval_requests(task_id, status);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor VARCHAR(100) NOT NULL, -- Agent Name or User ID
    action_type VARCHAR(100) NOT NULL,
    target_resource TEXT,
    payload JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45) DEFAULT '127.0.0.1',
    status VARCHAR(50) NOT NULL, -- 'SUCCESS', 'FAILED', 'BLOCKED', 'ABORTED'
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_audit_logs_actor ON audit_logs(actor, timestamp DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action_type);

-- ============================================================================
-- 5. Integrations & Scheduled Jobs
-- ============================================================================

CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider_name VARCHAR(100) NOT NULL, -- 'openai', 'anthropic', 'google', 'github', 'slack'
    encrypted_credentials BYTEA NOT NULL, -- AES-256-GCM ciphertext
    config JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX uq_user_provider ON integrations(user_id, provider_name);

CREATE TABLE scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    cron_expression VARCHAR(100) NOT NULL,
    task_payload JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_scheduled_jobs_active ON scheduled_jobs(is_active, next_run_at);
```
