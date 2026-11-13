# REETA — Installation & Deployment Guide

**Responsive Executive Engine for Tasks and Automation**  
*Target Platform: Windows 11 Desktop (x86_64)*

---

## 1. System Requirements

- **Operating System:** Windows 11 (or Windows 10 64-bit Build 19041+)
- **Runtime Dependencies:**
  - Microsoft Edge WebView2 Evergreen Runtime (pre-installed on Windows 11 and modern Windows 10)
  - Audio input device (Microphone) for voice control and audio-reactive visualization
  - Audio output device (Speakers/Headphones) for Windows SAPI offline voice feedback
- **Hardware Recommendations:**
  - 4 CPU Cores (Intel Core i5 / AMD Ryzen 5 or better)
  - 8 GB RAM minimum (16 GB recommended)
  - 500 MB free disk space for application binaries and cached local voice models

---

## 2. Installation Architecture

REETA is packaged as a **self-contained native Windows desktop application** powered by Tauri 2:

- **Single Installer:** Installs per-user with zero administrative prompt required.
- **Embedded Python Sidecar:** Automatically supervised via Win32 Job Objects (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`). Exiting the app terminates all background processes cleanly with zero orphans.
- **Standalone Database:** Zero-process-overhead SQLite database with vector similarity search (`sqlite-vec` v0.1.9) located at:
  ```
  %LOCALAPPDATA%\REETA\data\reeta.db
  ```
- **Windows Credential Manager:** Cloud AI API keys (OpenAI, Anthropic, Gemini, Groq) are stored securely in the Windows Vault (`keyring`) rather than plaintext configuration files.
- **Microphone & Voice:** Direct native audio capture (`sounddevice`), energy VAD, "Hey REETA" wake-word detection, and offline Windows SAPI (`pyttsx3`) text-to-speech.
- **Browser Automation:** Automates the pre-installed Microsoft Edge browser (`channel="msedge"`) with no heavy Chromium download required.

---

## 3. Launching REETA

### Method A: Native Desktop App (Recommended)

1. Launch **REETA** from the Start Menu or Desktop shortcut.
2. The Tauri shell automatically:
   - Allocates an ephemeral local loopback port on `127.0.0.1`.
   - Generates a cryptographically secure 32-byte session token (`REETA_LAUNCH_TOKEN`).
   - Spawns the background engine with hidden window flags (`CREATE_NO_WINDOW`).
   - Verifies backend health and presents the cinematic holographic interface.
3. The application runs in the **System Tray**:
   - Left-click tray icon: Toggle show/hide.
   - Right-click tray icon: Access menu (Show REETA, Hide to Tray, Quit).
   - Closing the window minimizes REETA to the system tray so background wake-word detection remains active.

### Method B: Development Mode

To run REETA from the repository source code:

1. Ensure the Python virtual environment is set up:
   ```powershell
   backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   ```
2. Build the desktop frontend assets:
   ```cmd
   cd desktop
   npm run build
   ```
3. Run the Tauri desktop shell:
   ```powershell
   cargo run --manifest-path desktop\src-tauri\Cargo.toml
   ```

---

## 4. Persistent Application Directories

REETA stores all runtime state strictly inside the user's local application data:

| Directory | Purpose |
| :--- | :--- |
| `%LOCALAPPDATA%\REETA\data\` | SQLite database (`reeta.db`), cognitive memory embeddings |
| `%LOCALAPPDATA%\REETA\logs\` | Rotating desktop application and backend engine logs |
| `%LOCALAPPDATA%\REETA\models\` | Local speech recognition and embedding models |
| `%USERPROFILE%\.cache\huggingface\` | HuggingFace local model weights cache |

---

## 5. Security & Isolation

- **Localhost Binding:** REETA binds exclusively to `127.0.0.1`. It never listens on `0.0.0.0` or accepts external inbound network connections.
- **Per-Launch Authentication:** Every HTTP route and WebSocket connection requires the dynamically generated launch token (`Bearer <token>` / `?token=<token>`).
- **Consequential Action Protection:** Consequential actions (file deletion, terminal command execution, external network access) demand cryptographic HMAC-SHA256 approval tickets with explicit user authorization before execution.

