# REETA Technology Dependency Specification

This document details every technology, runtime, package, and system dependency required to build, run, and maintain the REETA Personal AI Operating System on Windows 11.

---

## 1. System Runtime Prerequisites

| Component | Target Version | Status on Development Host | Notes |
|:---|:---|:---|:---|
| **Operating System** | Windows 11 Desktop (Build 22000+) | Verified Active | Host Windows environment |
| **Python** | 3.11.x (tested 3.11.9) | Verified Active (3.11.9) | Standardized backend runtime |
| **Node.js** | v20.x or v22.x/v24.x (v24.15.0 active) | Verified Active (v24.15.0) | Desktop frontend tooling runtime |
| **npm** | 10.x+ (11.12.1 active) | Verified Active (11.12.1 via `npm.cmd`) | Package manager |
| **Docker Desktop** | 25.x+ (29.8.0 active) | Verified Active (29.8.0) | Required for isolated code execution & PostgreSQL |
| **Rust / Cargo** | 1.77+ | Required for Tauri 2 binary build | Documented install step via `rustup-init.exe` |
| **WebView2** | Evergreen Runtime | Native on Windows 11 | Embedded in Tauri 2 desktop shell |

---

## 2. Backend Dependencies (Python 3.11)

### 2.1 Core Framework & Networking
- `fastapi>=0.115.0`: High-performance asynchronous REST API framework.
- `uvicorn[standard]>=0.31.0`: ASGI production web server with uvloop/httptools.
- `websockets>=13.0`: High-concurrency bidirectional WebSocket protocol handler.
- `pydantic>=2.9.0`: Typed data validation and schema definitions.
- `pydantic-settings>=2.5.0`: Environment variable configuration with `.env` loading.
- `httpx>=0.27.0`: High-performance async HTTP client for external integrations.
- `aiofiles>=24.1.0`: Asynchronous file I/O operations.

### 2.2 Intelligence, Agent Orchestration & LLMs
- `langgraph>=0.2.30`: State-graph orchestrator for multi-agent workflows, cycles, and checkpoints.
- `langchain-core>=0.3.0`: Base prompt, tool, and message abstraction contracts.
- `openai>=1.50.0`: Client for OpenAI models (GPT-4o, o1, etc.).
- `anthropic>=0.35.0`: Client for Anthropic Claude (Claude 3.5 Sonnet, Claude 3.5 Haiku).
- `google-genai>=0.1.0`: Official Google Gemini API client.
- `ollama>=0.3.3`: Local LLM orchestration client for locally served open weights.
- `tiktoken>=0.7.0`: Fast BPE token counting for context window budgeting.

### 2.3 Database, ORM & Vector Search
- `sqlalchemy[asyncio]>=2.0.35`: Async object relational mapper.
- `asyncpg>=0.29.0`: Asynchronous PostgreSQL driver.
- `pgvector>=0.3.4`: PostgreSQL pgvector extension bindings for Python.
- `alembic>=1.13.3`: Database schema migration tool.
- `greenlet>=3.1.0`: Required for async SQLAlchemy engine.

### 2.4 Windows 11 & Browser Automation
- `playwright>=1.47.0`: Browser automation framework (Chromium/Firefox/WebKit).
- `pywinauto>=0.6.8`: Native Windows UI Automation (UIA) 3.0 controller.
- `pyautogui>=0.9.54`: Fallback coordinate-based mouse & keyboard automation.
- `mss>=9.0.1`: Fast, cross-platform screen capture.
- `Pillow>=10.4.0`: Image processing, screenshot bounding box drawing, and visual diffs.
- `pytesseract>=0.3.10`: Optical Character Recognition (OCR) for visual desktop analysis.

### 2.5 Voice Pipeline
- `faster-whisper>=1.0.3`: CTranslate2-based optimized Whisper model for fast offline transcription.
- `silero-vad>=5.1.2`: High-speed, low-footprint Voice Activity Detection for real-time barge-in.
- `sounddevice>=0.5.0`: PortAudio wrapper for microphone capture and speaker output.
- `piper-tts>=1.2.0`: Ultra-fast local neural text-to-speech engine.
- `edge-tts>=6.1.12`: Lightweight asynchronous Microsoft Edge neural voice streaming.
- `numpy>=1.26.0`: Numerical array manipulation for PCM audio streaming.

### 2.6 Security, Cryptography & Containerization
- `cryptography>=43.0.1`: AES-256-GCM authenticated encryption for stored credentials.
- `python-jose[cryptography]>=3.3.0`: Cryptographic signing of ephemeral approval tokens.
- `passlib[bcrypt]>=1.7.4`: Password hashing and verification.
- `docker>=7.1.0`: Docker SDK for Python to run isolated, resource-constrained containers.

---

## 3. Desktop Application Dependencies (React 18 + TypeScript + Tauri 2)

### 3.1 Tauri 2 Core
- `@tauri-apps/api>=2.0.0`: Client-side Tauri APIs for window control, FS dialogs, and OS events.
- `@tauri-apps/plugin-shell>=2.0.0`: Safe shell command and URL launch plugin.
- `@tauri-apps/plugin-dialog>=2.0.0`: Native Windows open/save file dialogs.
- `@tauri-apps/plugin-notification>=2.0.0`: Native Windows toast notifications.
- `@tauri-apps/plugin-global-shortcut>=2.0.0`: Global hotkeys (e.g. `Ctrl+Space` for REETA summon).

### 3.2 Frontend UI Framework & State
- `react>=18.3.1`: Declarative component UI library.
- `react-dom>=18.3.1`: React DOM renderer.
- `typescript>=5.5.0`: Static typing for high reliability.
- `vite>=5.4.0`: Fast ESM build tool and development server.
- `tailwindcss>=3.4.10`: Utility-first CSS styling.
- `clsx>=2.1.1` & `tailwind-merge>=2.5.2`: Class merging utilities.
- `framer-motion>=11.5.0`: Production-ready physics-based animations.
- `lucide-react>=0.441.0`: Comprehensive minimalist SVG icon suite.
- `@tanstack/react-query>=5.56.0`: Asynchronous server state caching and sync.
- `zustand>=5.0.0`: Lightweight predictable client state management.

---

## 4. Infrastructure & Container Services

### 4.1 PostgreSQL 16 with pgvector Container
- Image: `pgvector/pgvector:pg16`
- Exposed Port: `5432`
- Default Volumes: `./data/postgres:/var/lib/postgresql/data`
- Purpose: Relational data, task state checkpoints, user preferences, and vector embeddings.

### 4.2 Sandboxed Execution Container
- Image: `python:3.11-slim` or `node:20-slim`
- Execution limits: `--memory=512m`, `--cpus=1.0`, `--pids-limit=100`, `--network=none` (for untrusted code execution).
