# REETA System Architecture Document
**Responsive Executive Engine for Tasks and Automation**  
*Target Operating System: Windows 11 Desktop | Development Environment: Google Antigravity*

---

## 1. Executive Summary & Vision

REETA is designed as an autonomous, general-purpose personal AI Operating System for Windows 11. Unlike basic reactive conversational chatbots, REETA functions as an **executive agent** capable of:
- Understanding natural language intent across modalities (text, real-time voice, screenshot/visual input).
- Synthesizing complex multi-step execution plans with dependency graphs.
- Operating the host operating system (Windows 11) via native UI Automation (pywinauto), browser drivers (Playwright), coordinate-based control (PyAutoGUI), and isolated PowerShell execution.
- Executing code and scripts within sandboxed Docker containers.
- Enforcing a zero-trust, tiered permission and approval model.
- Continuous result verification where no task is reported as completed without empirical verification.
- Maintaining long-term episodic, semantic, and procedural memory using PostgreSQL with pgvector.

---

## 2. Core Architectural Principles

1. **Provider Agnostic Intelligence:** The intelligence engine abstracts LLM backends through a unified Model Gateway. Local models (Ollama: Llama 3, DeepSeek, Qwen) and Cloud providers (OpenAI, Anthropic Claude, Google Gemini, Groq) are dynamically selected based on task complexity, privacy tier, latency, and token cost.
2. **Deterministic Orchestration over Monolithic Prompts:** Complex goals are decomposed into Directed Acyclic Graphs (DAGs) executed by a LangGraph state machine with explicit state checkpoints, error branches, and retry policies.
3. **Zero-Trust Human-in-the-Loop Security:** Actions are categorized into Autonomous (Tier 1), Approval-Required (Tier 2), and Restricted (Tier 3). Harmful operations are physically prevented, and sensitive system operations require explicit cryptographic approval tickets.
4. **Empirical Result Verification:** Execution is decoupled from verification. After executing a tool or action, specialized verifier routines inspect operating system state (file system checks, process tables, DOM assertions, API responses) before declaring success.
5. **Low-Latency Interruptible Voice Interface:** The voice subsystem integrates local offline speech-to-text (faster-whisper), local high-fidelity neural speech synthesis (Piper TTS) with cloud fallbacks, Silero VAD for low-latency barge-in interruption, and local wake-word detection.

---

## 3. High-Level Architecture Topology

```
+---------------------------------------------------------------------------------------+
|                               WINDOWS 11 DESKTOP SHELL                                |
+---------------------------------------------------------------------------------------+
|  +---------------------------------------------------------------------------------+  |
|  |                 TAURI 2 DESKTOP CLIENT (React 18 + TS + Tailwind)               |  |
|  |  - Command Center           - Live Operations Monitor      - Memory Center      |  |
|  |  - Agent Workspace          - Computer View (Live Screen)  - Permission Manager |  |
|  |  - Audio Capture / Player   - WebSocket Streaming Client   - Global Hotkeys     |  |
|  +---------------------------------------+-----------------------------------------+  |
|                                          | Inter-Process Communication (REST / WSS)   |
|                                          v                                            |
|  +---------------------------------------------------------------------------------+  |
|  |                     REETA FASTAPI BACKEND SERVER (Python 3.11)                  |  |
|  |                                                                                 |  |
|  |  [API / Gateway Layer]                                                          |  |
|  |  - REST Endpoints (/api/v1/*)           - WebSocket Event Stream (/ws/v1/stream)|  |
|  |  - Audio Streaming Gateway (/ws/voice)  - JWT & Local Token Auth Gatekeeper    |  |
|  |                                                                                 |  |
|  |  [Central Intelligence & Orchestration Engine]                                  |  |
|  |  - LangGraph State Machine Graph        - Model Routing & Gateway               |  |
|  |  - Task Planner & DAG Synthesizer       - Execution Engine & Circuit Breaker    |  |
|  |  - Verification Engine                  - Checkpoint & State Manager            |  |
|  |                                                                                 |  |
|  |  [Specialized Worker Agents]                                                    |  |
|  |  +-------------------+  +--------------------+  +----------------------------+  |  |
|  |  |  Research Agent   |  |   Coding Agent     |  |      Computer Agent        |  |  |
|  |  |  (Web/Scrape/PDF) |  | (Docker/Git/Files) |  | (pywinauto/PyAutoGUI/OCR)  |  |  |
|  |  +-------------------+  +--------------------+  +----------------------------+  |  |
|  |  +-------------------+  +--------------------+  +----------------------------+  |  |
|  |  |  Browser Agent    |  |    File Agent      |  |    Productivity Agent      |  |  |
|  |  | (Playwright/DOM)  |  | (OS Search/Org/Doc)|  | (Reminders/Cron/Calendar)  |  |  |
|  |  +-------------------+  +--------------------+  +----------------------------+  |  |
|  |                                                                                 |  |
|  |  [Security & Permission Core]                                                   |  |
|  |  - Policy Engine (Tier 1/2/3)           - Cryptographic Approval Ticket Issuer  |  |
|  |  - System Audit Logger                  - Emergency Kill-Switch Subsystem       |  |
|  |                                                                                 |  |
|  |  [Voice & Audio Pipeline]                                                       |  |
|  |  - faster-whisper (STT)                 - Piper TTS / EdgeTTS (Neural Speech)   |  |
|  |  - Silero VAD (Activity Detection)     - Wake-word Engine ("Hey Reeta")        |  |
|  |                                                                                 |  |
|  |  [Memory & Context Engine]                                                      |  |
|  |  - PostgreSQL 16 + pgvector             - Episodic & Semantic Recall            |  |
|  |  - Working Memory Scratchpad            - Vector Embeddings (MiniLM / OpenAI)   |  |
|  +---------------------------------------+-----------------------------------------+  |
|                                          | OS & Driver Subsystems                     |
|                                          v                                            |
|  +---------------------------------------------------------------------------------+  |
|  |                    WINDOWS 11 NATIVE HOST SUBSYSTEMS                            |  |
|  |  - Windows UI Automation 3.0 (Win32/COM)    - Headless/Headed Chromium Browsers |  |
|  |  - Isolated PowerShell 7.x Runspaces        - Docker Desktop Sandbox Containers |  |
|  |  - Windows Notification System              - Host File System & NTFS Access    |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
```

---

## 4. Subsystem Detailed Specifications

### 4.1 Desktop Client (Tauri 2 + React + TypeScript + Tailwind CSS)
- **Framework:** Tauri 2 bundle utilizing native Windows WebView2 (leveraging the evergreen Edge Chromium engine pre-installed on Windows 11).
- **UI Architecture:** React 18, TypeScript, Tailwind CSS, Framer Motion for hardware-accelerated animations, Radix UI headless accessible components, Lucide icons.
- **Design Aesthetic:** Deep obsidian base (`#0B0E14`), dark navy panels (`#111726`), restrained cyan accents (`#06B6D4`), electric blue telemetry highlights (`#3B82F6`), high-legibility monospace and sans-serif typography (JetBrains Mono / Inter).
- **Key Modules:**
  - `CommandCenter`: Central interactive hub, voice waveform visualizer, input prompt, active task status bar, system telemetry.
  - `LiveOperations`: Visual execution graph of ongoing multi-step plans with real-time log output and step status markers.
  - `AgentWorkspace`: Artifacts viewer, diff inspector, markdown/code editor, PDF viewer.
  - `ComputerView`: Real-time screenshot display with agent target bounding boxes and mouse/click overlays.
  - `MemoryCenter`: Interactive explorer of stored user preferences, episodic memories, and semantic knowledge graph.
  - `Permissions`: Active authorization requests, permission scopes, audit logs, and instant revocation toggles.

### 4.2 Backend Application (FastAPI + Python 3.11)
- **Runtime:** Python 3.11.9 with async-first architecture (AsyncIO event loop).
- **Web Layer:** FastAPI application serving OpenAPI/Swagger specifications, structured REST endpoints, and bidirectional WebSocket streams.
- **Data Validation & Serialization:** Pydantic v2 schemas providing compile-time type validation, serialized JSON outputs, and strict input cleansing.
- **Background Task Management:** AsyncIO task workers with bounded task queues, cancellation tokens, and task timeouts.

### 4.3 Intelligence & Multi-Agent Orchestration
- **Framework:** LangGraph state machine coordinating specialized agents using typed state schemas (`AgentState`).
- **Model Gateway:** Unified adapter interface (`BaseLLMProvider`) supporting:
  - Local: Ollama (Llama 3.1, Qwen 2.5 Coder, DeepSeek R1).
  - Cloud: Anthropic Claude (Claude 3.5 Sonnet), OpenAI (GPT-4o), Google Gemini (Gemini 1.5 Pro / Flash), Groq.
- **Dynamic Router:** Analyzes user query intent, token complexity, and required tool capabilities to route to the most cost-effective and capable model.

### 4.4 Automation & Windows Integration Subsystem
- **Windows UI Automation:** Python `pywinauto` leveraging the UI Automation (UIA) backend to inspect Windows controls, buttons, menus, and text fields deterministically by AutomationId and Name.
- **Low-Level Control:** `PyAutoGUI` and `mss` for high-frequency screen capture, DPI-aware coordinate mapping, mouse clicks, and keyboard shortcuts.
- **Browser Automation:** `Playwright` controlling isolated Chromium, Firefox, and WebKit contexts with DOM-tree accessibility snapshots and stealth browsing profiles.
- **Terminal Execution:** Async PowerShell subprocess manager with command whitelisting, timeout enforcement, output streaming, and non-admin privilege drop.
- **Code Sandbox:** Docker container runner (`docker-py`) mounting transient project directories into ephemeral containers with memory, CPU, and network quotas.

### 4.5 Memory & Semantic Knowledge Subsystem
- **Storage:** PostgreSQL 16 with the `pgvector` extension.
- **Memory Tiers:**
  - *Working Memory:* Short-term execution scratchpad containing active task goals, current step outputs, and intermediate tool results (in-memory Redis / Python state).
  - *Short-Term Memory:* Sliding window of recent conversation turns and active context.
  - *Long-Term Memory:* Semantic facts, user preferences, past project solutions, and episodic interactions indexed with vector embeddings (`vector(1536)`).
- **Retrieval Engine:** Hybrid search combining dense vector similarity (`<=>` cosine distance) and sparse BM25 full-text search with Reciprocal Rank Fusion (RRF).

### 4.6 Voice & Audio Interface
- **Speech-to-Text (STT):** `faster-whisper` running locally with INT8/FP16 quantization, utilizing local GPU (CUDA) or optimized CPU (AVX2/AVX512).
- **Voice Activity Detection (VAD):** `Silero VAD` running in real-time streaming mode to instantly detect when the user starts speaking, immediately halting agent TTS speech (barge-in capability).
- **Text-to-Speech (TTS):** `Piper TTS` (high-quality, fast local neural voice synthesis) with fallback to `Edge-TTS` for natural online streaming.
- **Wake-Word Detection:** Local lightweight wake-word detector ("Hey Reeta") listening on a dedicated low-power audio loop.

### 4.7 Zero-Trust Security & Permission System
- **Tier 1 (Autonomous):** Read-only operations, web research, file reads in authorized workspace, markdown generation, sandboxed test execution.
- **Tier 2 (Approval Required):** Modifying host files, sending external emails/webhooks, executing arbitrary PowerShell scripts, installing software, deleting folders.
- **Tier 3 (Restricted / Blocked):** Reading Windows credential stores, SAM files, registry keys for security policies, accessing raw passwords, unauthorized exfiltration.
- **Approval Mechanics:** Ephemeral, cryptographically signed approval tokens with 5-minute time-to-live and single-action scope.
- **Emergency Stop:** Immediate kill-switch endpoint (`/api/v1/system/emergency-stop`) that terminates all active subprocesses, browser sessions, and agent loops.

---

## 5. Resilience & Fault Tolerance Strategy

1. **Stateful Checkpointing:** LangGraph checkpoints state at every step in PostgreSQL. If the backend restarts or a process crashes, the task can resume from the last valid checkpoint without repeating idempotent actions.
2. **Exponential Backoff & Retries:** Transient network errors or rate limits are automatically retried with jittered exponential backoff.
3. **Graceful Tool Degradation:** If native UI Automation fails to find a control due to a custom framework, the Computer Agent automatically degrades to computer-vision coordinate click (OCR/Screenshot analysis).
4. **Strict Task Timeouts:** Every tool execution and sub-agent step is bound by strict timeouts to prevent hangs or runaway processes.
