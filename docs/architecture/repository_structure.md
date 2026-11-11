# REETA Repository Structure Specification

This document defines the exact layout of files and modules across REETA.

```
REETA/
├── .env.example                     # Environment template with all required keys
├── .gitignore                       # Git ignore patterns (node_modules, venv, data, logs)
├── docker-compose.yml               # PostgreSQL 16 + pgvector container definition
├── README.md                        # Master product documentation and quickstart
│
├── desktop/                         # Tauri 2 + React 18 + TypeScript Desktop App
│   ├── index.html                   # HTML entrypoint
│   ├── package.json                 # Desktop dependencies & scripts
│   ├── tsconfig.json                # TypeScript compiler config
│   ├── vite.config.ts               # Vite bundler config
│   ├── tailwind.config.js           # Futuristic theme, colors, font config
│   ├── postcss.config.js            # PostCSS plugins
│   ├── src-tauri/                   # Rust Tauri 2 host wrapper
│   │   ├── Cargo.toml               # Tauri Rust crate definitions
│   │   ├── tauri.conf.json          # Tauri application, window, and security config
│   │   └── src/
│   │       └── main.rs              # Rust Tauri entrypoint & native hooks
│   └── src/
│       ├── main.tsx                 # React DOM mount point
│       ├── App.tsx                  # Root layout, navigation router & global listeners
│       ├── assets/                  # Logos, icons, audio sound effects
│       ├── components/              # Shared UI design system
│       │   ├── ui/                  # Buttons, cards, modals, inputs, sliders, badges
│       │   ├── Header.tsx           # Global titlebar, connection status & model badge
│       │   ├── Sidebar.tsx          # Navigation rail (Command, Operations, Memory, etc.)
│       │   └── WaveformVisualizer.tsx # Real-time voice audio visualizer
│       ├── pages/                   # Main screens
│       │   ├── CommandCenter.tsx    # Central prompt, audio mic, active task pulse
│       │   ├── LiveOperations.tsx   # Real-time DAG execution graph & streaming logs
│       │   ├── AgentWorkspace.tsx   # Artifacts, diff viewer, report viewer
│       │   ├── ComputerView.tsx     # Live screenshot & UI element bounding boxes
│       │   ├── MemoryCenter.tsx     # Interactive semantic knowledge explorer
│       │   ├── Permissions.tsx      # Approval tickets, audit logs, policy settings
│       │   ├── TaskHistory.tsx      # Past tasks, metrics, token costs, timelines
│       │   ├── Integrations.tsx     # LLM keys, Ollama status, third-party connectors
│       │   └── Settings.tsx         # Voice settings, themes, model routing rules
│       ├── hooks/                   # Custom React hooks (useWebSocket, useVoice, useAudio)
│       ├── stores/                  # Zustand stores (useTaskStore, useVoiceStore, useAuth)
│       ├── services/                # API client & WebSocket client wrappers
│       └── types/                   # TypeScript interfaces matching backend models
│
├── backend/                         # Python 3.11 FastAPI Intelligence Core
│   ├── pyproject.toml               # Poetry/Pip project dependencies & metadata
│   ├── requirements.txt             # Pinned pip requirements
│   ├── alembic.ini                  # Alembic DB migration configuration
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app factory, lifespan, CORS, route registry
│   │   ├── config.py                # Pydantic BaseSettings, env variables & paths
│   │   ├── api/                     # REST & WebSocket API Routers
│   │   │   ├── v1/
│   │   │   │   ├── system.py        # Health, metrics, emergency stop
│   │   │   │   ├── conversations.py # Chat & session management
│   │   │   │   ├── tasks.py         # Autonomous task submission, control, status
│   │   │   │   ├── permissions.py   # Human-in-the-loop tickets & approvals
│   │   │   │   ├── memory.py        # Semantic memory search & preferences
│   │   │   │   └── host.py          # Screen capture, open windows, process list
│   │   │   └── websockets/
│   │   │       ├── stream.py        # Real-time event bus (DAG, thoughts, logs)
│   │   │       └── voice.py         # Bidirectional PCM audio streaming & VAD
│   │   ├── core/                    # Core orchestration & state
│   │   │   ├── state.py             # LangGraph state schema (AgentState)
│   │   │   ├── orchestrator.py      # Master LangGraph compiler and runner
│   │   │   ├── planner.py           # DAG task decomposition engine
│   │   │   └── router.py            # Dynamic Model Gateway & provider selector
│   │   ├── agents/                  # Specialized Worker Agents
│   │   │   ├── base.py              # BaseAgent abstract class & contract
│   │   │   ├── research.py          # Web research, fact checking, synthesis
│   │   │   ├── coding.py            # Codebase search, patch, test runner
│   │   │   ├── computer.py          # pywinauto, PyAutoGUI, Windows UI control
│   │   │   ├── browser.py           # Playwright Chromium navigation & DOM extraction
│   │   │   ├── file.py              # Pathlib, file batching, PDF/DOCX processing
│   │   │   └── productivity.py      # Reminders, cron scheduling, calendar
│   │   ├── tools/                   # Concrete Tool Implementations
│   │   │   ├── base.py              # Tool definition decorator & schema generator
│   │   │   ├── windows/             # UIA automation, window focus, coordinate click
│   │   │   ├── browser/             # Playwright page actions & DOM scrapers
│   │   │   ├── terminal/            # PowerShell execution runspace
│   │   │   ├── files/               # Safe file read, write, copy, move, tree
│   │   │   └── documents/           # PDF generation, markdown converter
│   │   ├── memory/                  # Memory Subsystem
│   │   │   ├── store.py             # PostgreSQL + pgvector client & vector index
│   │   │   ├── semantic.py          # Embedding generation & cosine search
│   │   │   └── working.py           # In-memory execution scratchpad
│   │   ├── permissions/             # Security & Policy Engine
│   │   │   ├── policy.py            # 3-Tier classification logic
│   │   │   ├── tickets.py           # Ephemeral approval ticket generator & HMAC
│   │   │   └── audit.py             # Asynchronous audit log recorder
│   │   ├── voice/                   # Voice & Speech Pipeline
│   │   │   ├── stt.py               # faster-whisper local transcriber
│   │   │   ├── tts.py               # Piper TTS / EdgeTTS neural synthesizer
│   │   │   ├── vad.py               # Silero VAD speech detection & barge-in
│   │   │   └── wakeword.py          # Local wake-word listener loop
│   │   ├── execution/               # Autonomous Execution Engine
│   │   │   ├── engine.py            # Step dispatcher, concurrency & timeouts
│   │   │   ├── checkpoints.py       # LangGraph checkpoint persistence in DB
│   │   │   └── recovery.py          # Exponential backoff retry policies
│   │   ├── verification/            # Result Verification Engine
│   │   │   ├── engine.py            # Verification orchestrator
│   │   │   ├── rules.py             # File, process, DOM, and test assertions
│   │   │   └── verifiers/           # Concrete verifier implementations
│   │   ├── scheduler/               # Background Job Scheduler
│   │   │   └── cron.py              # Async cron runner & reminder notifier
│   │   ├── database/                # Database Layer
│   │   │   ├── session.py           # Async SQLAlchemy session factory
│   │   │   ├── models.py            # Declarative SQLAlchemy ORM models
│   │   │   └── migrations/          # Alembic version files
│   │   └── security/                # Cryptography & Sandboxing
│   │       ├── crypto.py            # AES-256-GCM credential encryption
│   │       └── sandbox.py           # Docker container isolation runner
│   └── tests/                       # Automated Test Suite
│       ├── unit/                    # Unit tests for policy, agents, tools
│       ├── integration/             # API and database integration tests
│       └── e2e/                     # End-to-end task execution tests
│
├── infrastructure/                  # Infrastructure & Deployment
│   ├── docker/                      # Dockerfiles for sandbox & DB
│   │   ├── Dockerfile.backend       # Backend container definition
│   │   └── Dockerfile.sandbox       # Safe execution sandbox container
│   └── database/
│       └── init.sql                 # PostgreSQL 16 + pgvector init script
│
└── docs/                            # Complete Documentation
    ├── architecture/
    │   ├── system_architecture.md   # Master architecture specification
    │   ├── architecture_diagrams.md # Mermaid architecture diagrams
    │   ├── technology_dependencies.md # Complete dependency inventory
    │   ├── database_schema.md       # PostgreSQL + pgvector DDL
    │   ├── agent_matrix.md          # Agent responsibilities & contracts
    │   ├── security_model.md        # 3-Tier Zero-Trust security model
    │   ├── repository_structure.md  # File & module map
    │   └── implementation_plan.md   # Phased development roadmap
    ├── api/
    │   └── contracts.md             # REST & WebSocket protocol specifications
    └── setup/
        └── windows_setup_guide.md   # Windows 11 installation instructions
```
