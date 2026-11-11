# REETA API Contracts & WebSocket Protocol Specification

This document details the REST API endpoints and real-time WebSocket protocol contracts between the Tauri 2 Desktop frontend and the FastAPI backend.

---

## 1. REST Endpoints Specification

Base URL: `http://127.0.0.1:8765/api/v1`  
All JSON requests and responses use `application/json` and standard ISO 8601 timestamps.

### 1.1 System & Diagnostics

#### `GET /system/health`
Returns system health, backend status, database connectivity, and active models.
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "active_provider": "ollama:llama3.1",
  "voice_engine": "ready",
  "uptime_seconds": 3412
}
```

#### `POST /system/emergency-stop`
Immediately aborts all executing agents, kills browser sessions, terminates child processes, and drops pending tool calls.
**Response (200 OK):**
```json
{
  "success": true,
  "message": "Emergency stop invoked. All tasks and child processes terminated.",
  "timestamp": "2026-11-11T15:04:05Z"
}
```

---

### 1.2 Conversations & Messages

#### `POST /conversations`
Creates a new conversation session.
**Request:**
```json
{
  "title": "Build Customer Sentiment Analyzer",
  "mode": "coding"
}
```
**Response (201 Created):**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Build Customer Sentiment Analyzer",
  "mode": "coding",
  "created_at": "2026-11-11T15:05:00Z"
}
```

#### `GET /conversations/{conversation_id}/messages`
Retrieves conversation message history with tool calls and agent metadata.

---

### 1.3 Autonomous Task Lifecycle

#### `POST /tasks`
Initializes a new autonomous multi-step task.
**Request:**
```json
{
  "conversation_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "title": "Competitor Research & PDF Export",
  "objective": "Scrape public pricing of top 3 CRM competitors, compare in a table, and save as reports/crm_pricing.pdf",
  "priority": 8
}
```
**Response (202 Accepted):**
```json
{
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "planning",
  "created_at": "2026-11-11T15:06:00Z"
}
```

#### `GET /tasks/{task_id}`
Retrieves task execution state, step progress, checkpointed graph, and verified artifacts.
**Response (200 OK):**
```json
{
  "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "running",
  "plan": {
    "total_steps": 3,
    "current_step": 2,
    "steps": [
      {
        "step_number": 1,
        "title": "Research CRM competitors and pricing tiers",
        "agent": "research_agent",
        "status": "completed",
        "verification_status": "verified"
      },
      {
        "step_number": 2,
        "title": "Compile data into PDF document",
        "agent": "file_agent",
        "status": "running",
        "verification_status": "unverified"
      }
    ]
  },
  "artifacts": [
    {
      "name": "crm_pricing.pdf",
      "path": "E:/PROJECTS/reeta/reports/crm_pricing.pdf",
      "verified": false
    }
  ]
}
```

#### `POST /tasks/{task_id}/cancel`
Signals immediate cancellation to the task's execution graph.

---

### 1.4 Permissions & Zero-Trust Approvals

#### `GET /permissions/pending`
Lists all pending human-in-the-loop approval tickets.
**Response (200 OK):**
```json
[
  {
    "ticket_id": "ticket_7a8f9b2c",
    "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "step_number": 2,
    "agent": "file_agent",
    "action": "write_file",
    "target_resource": "E:/PROJECTS/reeta/reports/crm_pricing.pdf",
    "risk_level": "medium",
    "description": "File Agent requests permission to create a new PDF file at E:/PROJECTS/reeta/reports/crm_pricing.pdf",
    "expires_at": "2026-11-11T15:15:00Z"
  }
]
```

#### `POST /permissions/respond`
Resolves an approval ticket.
**Request:**
```json
{
  "ticket_id": "ticket_7a8f9b2c",
  "decision": "approve", // "approve" or "reject"
  "scope": "single_action", // "single_action", "task_session", "permanent"
  "reason": "Authorized file creation in reports directory"
}
```
**Response (200 OK):**
```json
{
  "ticket_id": "ticket_7a8f9b2c",
  "status": "approved",
  "signed_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "timestamp": "2026-11-11T15:10:05Z"
}
```

---

### 1.5 Cognitive Memory & Vector Retrieval

#### `POST /memory/search`
Performs hybrid dense vector and keyword search over past interactions and knowledge.
**Request:**
```json
{
  "query": "What is user's preferred color scheme for reports?",
  "top_k": 3,
  "memory_types": ["preference", "semantic"]
}
```
**Response (200 OK):**
```json
{
  "results": [
    {
      "id": "e4b2c1a0-1234-4567-89ab-cdef01234567",
      "memory_type": "preference",
      "content": "User prefers dark mode layouts with high contrast cyan highlights and minimalist tables.",
      "similarity_score": 0.912,
      "created_at": "2026-11-01T10:00:00Z"
    }
  ]
}
```

---

## 2. Real-Time WebSocket Event Bus Protocol

Endpoint: `ws://127.0.0.1:8765/ws/v1/stream`

### 2.1 Message Frame Structure
Every frame transmitted across the WebSocket conforms to this JSON envelope:
```typescript
interface WSFrame<T = any> {
  event: string;           // Event descriptor
  task_id?: string;        // Associated task ID (if applicable)
  conversation_id?: string;// Associated conversation ID
  timestamp: string;       // ISO 8601 timestamp
  payload: T;              // Strongly-typed payload data
}
```

### 2.2 Client-to-Server Events

| Event | Payload Type | Description |
|:---|:---|:---|
| `user_message` | `{ text: string, conversation_id: string }` | Sends user prompt to orchestrator |
| `task_cancel` | `{ task_id: string, reason?: string }` | Requests immediate cancellation of task |
| `approval_response` | `{ ticket_id: string, decision: 'approve' \| 'reject' }` | Transmits human decision on Tier 2 ticket |
| `emergency_stop` | `{}` | Broadcasts kill switch to backend |
| `ping` | `{}` | Heartbeat keep-alive |

### 2.3 Server-to-Client Events

| Event | Payload Type | Description |
|:---|:---|:---|
| `agent_thought` | `{ agent: string, token: string }` | Streaming LLM token / reasoning trace |
| `plan_generated` | `{ task_id: string, steps: PlanStep[] }` | Synthesized DAG step hierarchy |
| `step_started` | `{ task_id: string, step_number: number, agent: string }` | Step execution started |
| `tool_call_started`| `{ step_number: number, tool: string, args: any }` | Agent invoked a specific tool |
| `tool_call_completed`| `{ step_number: number, tool: string, result: any, success: boolean }`| Tool execution finished |
| `approval_required`| `ApprovalTicket` | Demands human permission in UI dialog |
| `step_verified` | `{ step_number: number, evidence: string, passed: boolean }` | Empirical outcome verification result |
| `task_completed` | `{ task_id: string, outcome: string, artifacts: any[] }` | Final task status |
| `error` | `{ code: string, message: string, fatal: boolean }` | Structured error event |

---

## 3. Real-Time Voice WebSocket Protocol

Endpoint: `ws://127.0.0.1:8765/ws/v1/voice`

### 3.1 Audio Protocol Format
- **Format:** Linear PCM 16-bit, 16,000 Hz, 1 channel (Mono), Little-Endian.
- **Client Uplink (Microphone):** Continuous binary stream of raw PCM audio chunks (64ms buffers / 1024 samples).
- **Server Downlink (Speaker Output):** Binary audio chunks containing neural synthesized speech (Piper / EdgeTTS).
- **Control Envelopes (JSON frames interleaved):**
  - `vad_speech_start`: Notifies client that speech has been detected by Silero VAD.
  - `vad_speech_end`: Speech utterance finished, STT decoding triggered.
  - `transcript_partial`: Real-time streaming transcription text from faster-whisper.
  - `transcript_final`: Final decoded transcription text routed to Orchestrator.
  - `barge_in_interrupt`: User spoke while agent was talking; immediately stops audio buffer playback on client.
