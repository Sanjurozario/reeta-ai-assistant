# REETA — Developer Build & Compilation Guide

**Responsive Executive Engine for Tasks and Automation**  
*Building REETA from Source on Windows 11*

---

## 1. Prerequisites

To build REETA from source, ensure the following developer toolchains are installed on Windows 11:

1. **Rust Toolchain (MSVC Target):**
   - Rust 1.80+ (tested on Rust 1.99.1 `x86_64-pc-windows-msvc`).
   - Cargo package manager.
   - Install via [rustup.rs](https://rustup.rs).

2. **Visual Studio C++ Build Tools & Windows 11 SDK:**
   - Visual Studio 2022 Community or Build Tools with the "Desktop development with C++" workload.
   - Windows 11 SDK (headers and import libraries for `kernel32.lib`, `user32.lib`, etc.).
   - Alternatively, REETA supports standalone SDK header and library unpacking via `xwin` cached in `.xwin-cache\unpack\`.

3. **Node.js & npm:**
   - Node.js 18+ or 20+ LTS (tested with Node 20 / npm 10).
   - Vite 5 build toolchain.

4. **Python Runtime:**
   - Python 3.11.x 64-bit (recommended: Python 3.11.9).
   - Virtual environment at `backend\venv\`.
   - PyInstaller 6.0+ for binary freezing.

---

## 2. One-Command Build Script (`build.ps1`)

REETA includes an automated PowerShell build script in the repository root that orchestrates the entire compilation pipeline:

```powershell
# Build release distribution (optimized)
.\build.ps1

# Build debug distribution (fast compile)
.\build.ps1 -Mode debug

# Selective build flags
.\build.ps1 -SkipFrontend      # Skip Vite frontend build
.\build.ps1 -SkipBackend       # Skip PyInstaller freeze
.\build.ps1 -SkipShell         # Skip Rust Tauri shell compilation
```

### What `build.ps1` Automates:
1. **Environment Setup:** Resolves Visual Studio MSVC tools and Windows 11 SDK headers (`um`, `shared`, `ucrt`, `msvc include`) into `$env:INCLUDE` and linker flags into `$env:PATH`.
2. **Frontend UI Build:** Compiles the React/TypeScript/Tailwind/Framer Motion frontend into `desktop/dist/`.
3. **Backend Sidecar Freeze:** Freezes the FastAPI backend and all dependencies (`aiosqlite`, `sqlite-vec`, `pyttsx3`, `sounddevice`, `faster-whisper`, `playwright`, `keyring`, etc.) into `desktop/src-tauri/binaries/reeta-backend/reeta-backend.exe` using `backend/reeta_backend.spec`.
4. **Tauri Desktop Shell Compilation:** Builds the native Windows 11 shell with Win32 Job Object process supervision, system tray integration, and dynamic IPC into `desktop/src-tauri/target/release/REETA.exe`.
5. **Distribution Packaging:** Bundles the frozen backend sidecar next to `REETA.exe` for immediate portable execution.

---

## 3. Step-by-Step Manual Compilation

If you prefer building each subsystem manually:

### Step 1: Install Python Dependencies
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller
cd ..
```

### Step 2: Build the Frontend Bundle
```cmd
cd desktop
npm install
npm run build
cd ..
```
*Output: `desktop/dist/index.html` and bundled assets.*

### Step 3: Freeze the Backend Sidecar
```powershell
.\backend\venv\Scripts\python.exe -m PyInstaller --noconfirm --clean backend/reeta_backend.spec
```
*Output: `desktop/src-tauri/binaries/reeta-backend/reeta-backend.exe`.*

### Step 4: Compile the Tauri Shell
```powershell
# Configure MSVC environment variables if needed
$env:INCLUDE = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\include;$env:INCLUDE"

# Build with cargo
cargo build --manifest-path desktop/src-tauri/Cargo.toml --release
```
*Output: `desktop/src-tauri/target/release/REETA.exe`.*

### Step 5: Bundle Sidecar with Executable
```powershell
Copy-Item -Path "desktop/src-tauri/binaries/reeta-backend" -Destination "desktop/src-tauri/target/release/" -Recurse -Force
```

---

## 4. Verifying Build Outputs

After a successful build, verify the artifacts:

| Component | Path | Size |
| :--- | :--- | :--- |
| Desktop Executable | `desktop/src-tauri/target/release/REETA.exe` | ~8.7–9.2 MB |
| Backend Sidecar | `desktop/src-tauri/target/release/reeta-backend/reeta-backend.exe` | ~39.7 MB |
| Frontend Assets | `desktop/dist/index.html` | Embedded in `REETA.exe` via Tauri 2 |

To test run the built application:
```powershell
& "desktop\src-tauri\target\release\REETA.exe"
```

---

## 5. Running the Automated Test Suite

Ensure that all backend tests pass before committing or distributing builds:

```powershell
.\backend\venv\Scripts\pytest backend/tests -v
```
All 38 test suites covering API contracts, database operations, LangGraph orchestration, Zero-Trust permission security, and end-to-end demonstrations must report `PASSED`.

