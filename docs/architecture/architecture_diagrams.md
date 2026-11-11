# REETA Architecture Diagrams

This document contains visual architectural specifications for the REETA autonomous personal AI operating system using standard GitHub-flavored Mermaid notation.

---

## 1. System Component Topology & Security Boundaries

```mermaid
flowchart TB
    subgraph UI["Windows 11 Desktop Client (Tauri 2 / React)"]
        CC["Command Center UI"]
        LO["Live Operations & DAG"]
        CV["Computer View (Screen Mirror)"]
        MC["Memory Center"]
        PM["Permissions & Approvals UI"]
        VC["Voice Stream & Waveform"]
    end

    subgraph GW["Local API & Event Gateway (FastAPI)"]
        REST["REST API Endpoints (/api/v1)"]
        WS_STREAM["WebSocket Event Bus (/ws/v1/stream)"]
        WS_VOICE["WebSocket Audio Stream (/ws/v1/voice)"]
        AUTH["Token & Policy Gatekeeper"]
    end

    subgraph ORCH["Intelligence & Orchestration Core"]
        MROUTER["Dynamic Model Router\n(Cloud LLMs / Local Ollama)"]
        LG["LangGraph Orchestration Graph"]
        TASK_PLANNER["DAG Task Planner & Decomposer"]
        EXEC_ENGINE["Execution Engine & State Machine"]
        VERIF["Result Verification Engine"]
    end

    subgraph AGENTS["Specialized Worker Agents"]
        A_RES["Research Agent\n(Web, Fact Check, Report)"]
        A_CODE["Coding Agent\n(Codebase, Test, Patch)"]
        A_COMP["Computer Agent\n(pywinauto, PyAutoGUI, OCR)"]
        A_BROW["Browser Agent\n(Playwright, DOM Extraction)"]
        A_FILE["File Agent\n(Search, Batch Org, Docs)"]
        A_PROD["Productivity Agent\n(Reminders, Scheduler, Cron)"]
    end

    subgraph SEC["Security & Policy Subsystem"]
        POLICY["3-Tier Policy Engine\n(Autonomous / Approval / Restricted)"]
        AUDIT["Immutable Audit Logger"]
        ESTOP["Emergency Kill-Switch"]
    end

    subgraph HOST["Windows 11 Host & Automation Runtime"]
        PW["Playwright Chromium Contexts"]
        UIA["Windows UI Automation 3.0 (UIA)"]
        PAG["PyAutoGUI / mss Screen Capture"]
        PS["PowerShell 7 Sandbox Runspace"]
        DK["Docker Sandbox Containers"]
        FS["Host File System (NTFS)"]
    end

    subgraph MEM["Memory Subsystem (PostgreSQL + pgvector)"]
        PG_REL["Relational Stores (Tasks, Users, Audit)"]
        PG_VEC["Vector Store (vector 1536/768)"]
        WK_MEM["Working Memory / Scratchpad"]
    end

    subgraph VOICE_SYS["Voice Pipeline"]
        FW["faster-whisper STT"]
        PIPER["Piper TTS / EdgeTTS"]
        VAD["Silero VAD (Barge-in Detection)"]
        WW["Wake-Word Listener ('Hey Reeta')"]
    end

    %% UI to Gateway
    CC --> REST & WS_STREAM
    VC --> WS_VOICE
    PM --> REST & WS_STREAM
    LO --> WS_STREAM
    CV --> WS_STREAM

    %% Gateway to Orchestration & Security
    REST & WS_STREAM --> AUTH
    AUTH --> POLICY
    AUTH --> LG
    WS_VOICE --> VOICE_SYS

    %% Orchestration to Agents & Router
    LG --> MROUTER
    LG --> TASK_PLANNER
    TASK_PLANNER --> EXEC_ENGINE
    EXEC_ENGINE --> AGENTS
    AGENTS --> VERIF
    VERIF --> EXEC_ENGINE

    %% Security Policy Interception
    AGENTS -.->|Tool Call Verification| POLICY
    POLICY -->|Grant / Require Approval| AGENTS
    POLICY --> AUDIT
    ESTOP -.->|Signal Abort| EXEC_ENGINE & HOST

    %% Agents to Host
    A_BROW --> PW
    A_COMP --> UIA & PAG
    A_CODE --> DK & PS & FS
    A_FILE --> FS
    A_PROD --> HOST

    %% Memory Integrations
    EXEC_ENGINE <--> MEM
    MROUTER <--> MEM
    VOICE_SYS <--> WS_STREAM
```

---

## 2. Autonomous Task Planning & Execution Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Voice / Text)
    participant UI as Desktop Client
    participant API as FastAPI Gateway
    participant Orchestrator as LangGraph Orchestrator
    participant Planner as Task Planner
    participant Policy as Permission Engine
    participant Worker as Specialized Agent
    participant Host as Windows / Automation
    participant Verifier as Verification Engine
    participant DB as PostgreSQL + pgvector

    User->>UI: Submit Objective ("Draft competitor analysis & save to Reports/Q4.pdf")
    UI->>API: POST /api/v1/tasks/create or WebSocket event
    API->>Orchestrator: Initialize task execution state
    Orchestrator->>DB: Persist Task (Status: Planning)
    Orchestrator->>Planner: Analyze objective & synthesize DAG steps
    Planner-->>Orchestrator: Task Plan [Step 1: Research, Step 2: Write PDF, Step 3: Verify]
    Orchestrator->>UI: Stream Plan Generated Event (Live DAG UI)
    
    loop For Each Step in DAG
        Orchestrator->>Worker: Dispatch Step to Specialized Agent (e.g. Research Agent)
        Worker->>Policy: Evaluate Tool Call (e.g., `web_search`)
        Policy-->>Worker: Status: Tier 1 (Autonomous Granted)
        Worker->>Host: Execute Web Search & Extract Content
        Host-->>Worker: Raw Search & Web Content
        Worker-->>Orchestrator: Step Output (Research Synthesis)
        
        Orchestrator->>Worker: Dispatch Step 2 (File Agent: `write_file(Reports/Q4.pdf)`)
        Worker->>Policy: Evaluate Tool Call (`write_file` outside sandbox)
        alt Tier 2: Approval Required
            Policy-->>Orchestrator: Approval Required (Ticket ID: #4829)
            Orchestrator->>UI: Push Approval Dialog to User with Exact File Path & Action
            User->>UI: Click "Approve Action"
            UI->>API: POST /api/v1/permissions/approve
            API->>Policy: Register Cryptographic Approval
            Policy-->>Worker: Approval Token Validated
        end
        Worker->>Host: Write PDF to disk
        Host-->>Worker: File written confirmation
        
        Orchestrator->>Verifier: Verify Step Outcome (Inspect path, size, PDF header)
        Verifier->>Host: Assert file exists and is valid PDF (>0 bytes)
        Host-->>Verifier: Validation Passed
        Verifier-->>Orchestrator: Empirical Verification CONFIRMED
        Orchestrator->>DB: Checkpoint Step Complete
        Orchestrator->>UI: Stream Step Completed & Verified Event
    end

    Orchestrator->>DB: Update Task (Status: Completed)
    Orchestrator->>UI: Final Objective Accomplished with Artifact Link
    UI-->>User: Visual & Audio Report Completion
```

---

## 3. Real-Time Voice & Barge-In Audio Pipeline

```mermaid
flowchart LR
    MIC["Host Microphone"] -->|PCM Audio Stream| VAD["Silero VAD\n(Activity Detector)"]
    VAD -->|Voice Activity Detected| STT["faster-whisper\n(Local STT Engine)"]
    VAD -->|Barge-in Interrupt| INTERRUPT["Interrupt Controller\n(Kill Active TTS)"]
    STT -->|Final Text Transcript| ORCH["Central Orchestrator"]
    ORCH -->|Response Token Stream| TTS["Piper Neural TTS / Edge-TTS"]
    TTS -->|Synthesized Audio Stream| SPK["Desktop Audio Player"]
    INTERRUPT -.->|Immediate Flush| SPK
```

---

## 4. Zero-Trust Security & Permission State Machine

```mermaid
stateDiagram-v2
    [*] --> ToolCallReceived: Agent requests tool execution
    ToolCallReceived --> CheckPolicy: Evaluate resource, action, & user context

    state CheckPolicy <<choice>>
    CheckPolicy --> Tier1_Autonomous: Policy matches Safe List (Read-only, Search, Sandboxed code)
    CheckPolicy --> Tier2_ApprovalRequired: Policy matches Consequential List (FS write, Email, Shell, Install)
    CheckPolicy --> Tier3_Restricted: Policy matches Blocklist (Credentials, SAM, System destruction)

    Tier1_Autonomous --> ExecuteTool: Auto-authorized
    Tier3_Restricted --> RejectTool: Action blocked immediately & audited

    Tier2_ApprovalRequired --> IssueTicket: Generate ephemeral approval ticket (5m TTL)
    IssueTicket --> AwaitUserAction: Prompt user in Desktop UI with diff/payload
    
    state AwaitUserAction <<choice>>
    AwaitUserAction --> UserApproved: User clicks "Approve"
    AwaitUserAction --> UserRejected: User clicks "Deny"
    AwaitUserAction --> TicketExpired: No action within 300 seconds

    UserApproved --> ExecuteTool: Signed Approval Token verified
    UserRejected --> AbortStep: Return PermissionDenied to Agent
    TicketExpired --> AbortStep: Return ApprovalTimeout to Agent

    ExecuteTool --> AuditLog: Record execution telemetry in DB
    AuditLog --> Verification: Pass to Verification Engine
    Verification --> [*]: Completed

    RejectTool --> AuditLog
    AbortStep --> AuditLog
```
