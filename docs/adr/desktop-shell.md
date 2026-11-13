# ADR 001: Desktop Application Shell Architecture — Tauri 2 vs Electron

**Status:** Approved  
**Date:** November 12, 2026  
**Architect:** Principal AI Systems & Windows Desktop Architect  
**Project:** REETA (Responsive Executive Engine for Tasks and Automation)

---

## 1. Context & Problem Statement

In Part 1, REETA was constructed and verified as a distributed architecture consisting of a React + TypeScript frontend running on Vite (`localhost:1420`), an asynchronous FastAPI backend on Uvicorn (`127.0.0.1:8765`), a LangGraph multi-agent state machine, PostgreSQL 16 with `pgvector` in Docker, and a 3-tier Zero-Trust security engine.

For Part 2, REETA must transition into a production-grade, single-executable native Windows 11 desktop application:
1. One installer, one desktop/Start Menu shortcut, zero terminal windows.
2. No manual startup of Python, Node, Vite, Docker, or database containers.
3. Audio/voice pipeline must remain responsive in the background when the application is minimized or hidden to the system tray.
4. Clean, guaranteed shutdown with zero orphaned processes.

We evaluate two primary desktop architectures: **Tauri 2** (Rust + Microsoft Edge WebView2) and **Electron** (Chromium + Node.js).

---

## 2. Comparison & Evaluation Matrix

| Architectural Dimension | Tauri 2 (Rust + WebView2) | Electron (Chromium + Node.js) | Evaluation & Verdict for REETA |
| :--- | :--- | :--- | :--- |
| **Installer Size & Disk Footprint** | Extremely compact (~10–15 MB installer for shell + UI). Reuses Evergreen WebView2 preinstalled on Windows 10/11. | Bloated (95–140 MB base installer). Bundles redundant Chromium binary and Node.js runtime. | **Tauri 2 Wins**: Dramatically lighter download and installation footprint. |
| **Idle Memory Consumption (RAM)** | ~45–60 MB RAM for the shell process. | ~160–250 MB RAM base idle consumption across helper processes. | **Tauri 2 Wins**: Leaves maximum system memory for local LLMs, Whisper, and agent operations. |
| **Holographic Canvas / WebGL Performance** | Hardware-accelerated GPU rendering via Evergreen Microsoft Edge WebView2 runtime. Framer Motion and 60 FPS multi-ring particle canvas run smoothly. | Excellent hardware acceleration via bundled Chromium. | **Tie**: Both run REETA Core visual effects at full 60 FPS without frame drops. |
| **Process Supervision & Child Isolation** | Direct Win32 FFI via Rust `windows` crate. Can bind the frozen Python backend and database sidecars to a **Windows Job Object** with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. | Possible via native C++ addons (`node-winjob`), but adds build complexity and node-gyp fragility. | **Tauri 2 Wins**: Kernel-level process lifecycle guarantee with zero orphan risk. |
| **System Tray & Hide-to-Tray** | First-class native support in Tauri 2 core API (`TrayIconBuilder`) with dynamic icon states, tooltips, and background execution. | Mature `Tray` API in Electron. | **Tie**: Both support tray menus, hiding to tray on close, and window focus on wake word. |
| **Security & Surface Area** | Zero-trust default. No Node.js runtime exposed to frontend. Strict IPC message passing. | Requires careful `contextIsolation`, `nodeIntegration: false`, and preload script audits. | **Tauri 2 Wins**: Superior default security posture aligning with REETA Zero-Trust principles. |
| **Single-Instance & Autostart** | Official, hardened plugins: `tauri-plugin-single-instance`, `tauri-plugin-autostart`, and `tauri-plugin-updater`. | `app.requestSingleInstanceLock()`, `app.setLoginItemSettings()`. | **Tie**: Both provide robust single-instance and autostart capabilities. |

---

## 3. Decision

**Adopt Tauri 2 as the primary shell architecture for REETA on Windows 11.**

### Structural Rationale:
1. **Interactive User Session Execution (No Windows Service):**  
   REETA runs strictly as an interactive per-user application in Session 1+. It is intentionally **not** configured as a Windows Service, because Windows Session-0 isolation disables UI automation (UIAutomation, PyAutoGUI, pywinauto), cuts off microphone capture (CoreAudio / WASAPI), and blocks desktop window inspection.
2. **Database Engine: Dual PostgreSQL & SQLite + `sqlite-vec` Architecture:**  
   - In containerized / enterprise environments or automated test suites, REETA connects to PostgreSQL 16 + `pgvector` via `asyncpg`.
   - In standalone Windows desktop deployments, bundling 340MB of portable PostgreSQL binaries and compiling out-of-tree Windows `pgvector.dll` introduces substantial installer bloat and potential service failure modes (elevated privilege blocks, socket locking, stale `postmaster.pid`).
   - Consequently, standalone mode utilizes a unified database abstraction with **SQLite 3 + `sqlite-vec` (v0.1.9)**. `sqlite-vec` executes hardware-accelerated 1536-dimensional cosine distance (`vec_distance_cosine`) in-process with zero external daemon overhead, zero port conflicts, and a sub-300KB footprint.
   - All database models and vector similarity interfaces are unified under SQLAlchemy 2.0 / `aiosqlite`.
3. **Sidecar Process Hierarchy:**  
   The Tauri 2 Rust executable acts as the parent supervisor. It manages:
   - **Child 1:** Managed local database (PostgreSQL 16 with `pgvector` or local vector engine) on an ephemeral localhost port.
   - **Child 2:** Frozen Python backend (`reeta-backend.exe` generated via PyInstaller `--onedir`) running Uvicorn programmatically on an ephemeral localhost port.
3. **Windows Job Object Backstop:**  
   The Rust supervisor places all spawned sidecar PIDs into a Win32 Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. If the Tauri process terminates, crashes, or is killed via Task Manager, the Windows kernel forcefully and immediately terminates all backend and database child processes.
4. **Local Ephemeral Authentication:**  
   At launch, the Rust shell generates a cryptographically random launch token (`REETA_LAUNCH_TOKEN`). The backend requires this token in the `Authorization` header and WebSocket handshake (`?token=...`). The shell injects the base URL and token into the WebView2 window via Tauri IPC, removing all hardcoded ports from the frontend.

---

## 4. Contingency & Fallback Strategy

If native Rust compilation encounters an irreconcilable host-specific blocker on the build runner, the architectural design maps 1-to-1 into Electron:
- Frontend React code remains 100% identical.
- Child process supervision maps to `child_process.spawn()` wrapped with a Job Object native binding.
- Tray and single-instance map to Electron's corresponding APIs.
- The frozen Python sidecar and database architecture remain identical.

---

## 5. Consequences & Compliance

- **Storage Location:** All database data, logs, task outputs, and models must reside in `%LOCALAPPDATA%\REETA`. Nothing may be written to Program Files or next to the executable.
- **Port Flexibility:** All components must bind to `127.0.0.1` only, on dynamically assigned available ports.
- **Test Compatibility:** All 38 existing backend tests continue to execute against the standard FastAPI test client and live database engine.
