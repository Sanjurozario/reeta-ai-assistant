# REETA — Responsive Executive Engine for Tasks and Automation

**REETA** is an autonomous personal AI Operating System designed for Windows 11 Desktop. It is built as a general-purpose digital assistant capable of multi-step task synthesis, native Windows UI Automation, browser control, sandboxed code execution, persistent cognitive memory, low-latency interruptible voice interaction, and empirical result verification.

---

## 🌟 Key Highlights

- **Multi-Provider Intelligence:** Provider-agnostic model routing across local Ollama models (Llama 3.1, Qwen 2.5 Coder, DeepSeek) and cloud engines (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Google Gemini 1.5).
- **Native Windows Automation:** Native Windows UI Automation (pywinauto), high-performance screen capture and coordinate control (PyAutoGUI/mss), and PowerShell runspaces.
- **Headless & Headed Browser Control:** Playwright-driven Chromium navigation, DOM extraction, and form automation.
- **Sandboxed Execution:** Code and test evaluation run inside Docker containers with resource and network limits.
- **Cognitive Memory Architecture:** PostgreSQL 16 with `pgvector` indexing episodic, semantic, procedural, and preference memories.
- **Zero-Trust Security & Permissions:** Strict 3-Tier Policy Engine with cryptographic HMAC approval tickets for consequential actions and emergency stop kill-switch.
- **Empirical Verification Engine:** Real-world verification of outcomes (file checksums, DOM assertions, test exit codes, window state shifts) before marking any task as complete.
- **Real-Time Voice Pipeline:** Local offline speech-to-text (`faster-whisper`), voice activity detection (`silero-vad`) with barge-in interrupt capability, and neural speech synthesis.
- **Futuristic Desktop Shell:** Tauri 2 application with React 18, TypeScript, Tailwind CSS, Framer Motion, and a dark obsidian/navy/cyan aesthetic.

---

## 🏛️ Architecture Documentation

Complete specifications and architectural blueprints are available in `docs/`:

1. [System Architecture Document](docs/architecture/system_architecture.md)
2. [Architecture Diagrams (Mermaid)](docs/architecture/architecture_diagrams.md)
3. [Technology Dependencies](docs/architecture/technology_dependencies.md)
4. [Database Schema (pgvector DDL)](docs/architecture/database_schema.md)
5. [API & WebSocket Contracts](docs/api/contracts.md)
6. [Agent Responsibility Matrix](docs/architecture/agent_matrix.md)
7. [Security & Permission Model](docs/architecture/security_model.md)
8. [Repository Structure](docs/architecture/repository_structure.md)
9. [Integrated Implementation Plan](docs/architecture/implementation_plan.md)

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **OS:** Windows 11 Desktop (64-bit)
- **Python:** 3.11.x (Installed: `3.11.9`)
- **Node.js:** v20+ (Installed: `v24.15.0`)
- **Docker Desktop:** Installed & running (Installed: `29.8.0`)

### 2. Environment Configuration
Copy `.env.example` to `.env` and set your configuration:
```powershell
Copy-Item .env.example .env
```

### 3. Start PostgreSQL + pgvector Database
```powershell
docker compose up -d
```

### 4. Setup Python Virtual Environment
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 5. Launch Backend Service
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

### 6. Launch Desktop Application
```powershell
cd desktop
npm.cmd install
npm.cmd run dev
```

---

## 📄 License
Internal Development — REETA Architecture Team.
