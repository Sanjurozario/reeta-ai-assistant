# REETA — Standalone Troubleshooting & Diagnostics Guide

**Responsive Executive Engine for Tasks and Automation**  
*Common Issues, Diagnostics, and Resolutions on Windows 11*

---

## 1. Port Availability & Network Binding

### Symptom: Backend Port Conflict
REETA binds exclusively to loopback address `127.0.0.1`. By default, it attempts to listen on port `8765`.

### Diagnostic & Automated Resolution:
The Tauri desktop shell (`src-tauri/src/lib.rs`) implements dynamic ephemeral port negotiation:
1. It attempts to bind a TCP listener on `127.0.0.1:8765`.
2. If port `8765` is occupied by another service or development instance, it automatically requests an ephemeral port (`127.0.0.1:0`) from the Windows TCP stack.
3. The selected port is passed to the backend sidecar via the `PORT` environment variable and injected into the frontend via Tauri IPC (`get_backend_config`).

### Manual Inspection:
To see if another application is using port 8765:
```powershell
netstat -ano | findstr :8765
```
To terminate a lingering process by PID:
```powershell
Stop-Process -Id <PID> -Force
```

---

## 2. Microphone Capture & Wake-Word Detection

### Symptom: AI Core Waveform Does Not React / Wake-Word "Hey REETA" Not Triggering

### Checklist:
1. **Windows 11 Privacy Permissions:**
   - Open **Windows Settings** (`Win + I`) > **Privacy & security** > **Microphone**.
   - Ensure **"Microphone access"** is set to **On**.
   - Ensure **"Let desktop apps access your microphone"** is set to **On**.
2. **Default Input Device:**
   - Open **Sound Settings** (`Win + R` > `mmsys.cpl`).
   - Under the **Recording** tab, ensure your active microphone is configured as the **Default Device** and **Default Communication Device**.
   - Test speaking into the microphone and verify that the green level meter fluctuates.
3. **Audio Hardware Exclusive Mode:**
   - In microphone properties > **Advanced**, ensure *"Allow applications to take exclusive control of this device"* does not lock out background capture.

---

## 3. Microsoft Edge & WebView2 Runtime

### Symptom: Application Window Fails to Render / White Screen

### Cause:
REETA uses the Evergreen Microsoft Edge WebView2 runtime. On Windows 11 and up-to-date Windows 10 installations, WebView2 is pre-installed as an OS component.

### Diagnostic & Resolution:
1. Verify WebView2 installation:
   ```powershell
   Get-ItemProperty -Path "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-F301-4FA5-B5A3-9EBD66E79E60}" -ErrorAction SilentlyContinue
   ```
2. If missing or damaged, download and install the official Evergreen Bootstrapper:
   - [Microsoft Edge WebView2 Installer](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)

### Browser Automation Notice:
REETA's browser agent drives Microsoft Edge natively via Playwright's `channel="msedge"`. Ensure Edge is installed (standard Windows 11 default).

---

## 4. Antivirus & Windows Defender Heuristics

### Symptom: `reeta-backend.exe` or `REETA.exe` Blocked or Removed

### Cause:
PyInstaller packaged executables and newly compiled unsigned Rust binaries can occasionally trigger heuristic false-positives (SmartScreen or Defender Cloud-delivered protection) because they unpack or launch dynamically.

### Resolution:
Add a Windows Defender exclusion for REETA's installation or project directory:
```powershell
# Run PowerShell as Administrator:
Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\REETA"
Add-MpPreference -ExclusionProcess "REETA.exe"
Add-MpPreference -ExclusionProcess "reeta-backend.exe"
```

---

## 5. Offline Text-to-Speech (Windows SAPI)

### Symptom: Speech Audio Not Heard or SAPI Voice Errors

### Cause:
REETA uses Windows SAPI5 via `pyttsx3` for completely offline, zero-latency voice synthesis.

### Checklist:
1. Open **Windows Settings** > **Time & Language** > **Speech**.
2. Under **Voices**, verify that a standard English voice (such as *Microsoft David*, *Microsoft Zira*, or *Microsoft Mark*) is installed.
3. Test speech output by clicking **"Preview voice"**.
4. If running in a minimal Windows Server environment, install the Windows Desktop Experience or Speech Speech Pack package.

---

## 6. Process Lifecycle & Orphan Processes

### Win32 Job Object Protection:
REETA attaches all child processes to a kernel-level Win32 Job Object configured with:
```c
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
```
When `REETA.exe` closes, crashes, or is killed via Task Manager, the Windows kernel forcefully and instantaneously terminates the backend sidecar and any child helper processes.

### Verifying No Lingering Processes:
```powershell
Get-Process REETA, reeta-backend -ErrorAction SilentlyContinue
```
If any orphaned processes remain from early manual development sessions:
```powershell
Stop-Process -Name REETA, reeta-backend -Force -ErrorAction SilentlyContinue
```

---

## 7. Windows Credential Manager (Secure API Keys)

### Symptom: AI Provider Returns Invalid Key / Key Not Loaded

REETA stores cloud AI keys in the Windows Credential Manager (`keyring`) under target names formatted as:
```
REETA:<PROVIDER>_API_KEY
```
Example: `REETA:OPENAI_API_KEY`, `REETA:ANTHROPIC_API_KEY`.

### Managing Credentials:
1. Press `Win + R`, type `control /name Microsoft.CredentialManager`, and press Enter.
2. Select **Windows Credentials**.
3. Under **Generic Credentials**, look for entries starting with `REETA:`.
4. You can edit, update, or remove credentials securely without editing plain-text `.env` files.

---

## 8. Diagnostic Logs

REETA produces diagnostic logs in the standard Windows application data directory:

| Log File | Path |
| :--- | :--- |
| Backend Engine Logs | `%LOCALAPPDATA%\REETA\logs\backend.log` |
| Native Shell Logs | `%LOCALAPPDATA%\REETA\logs\reeta.log` |
| SQLite Database | `%LOCALAPPDATA%\REETA\data\reeta.db` |

To live-tail the backend logs in PowerShell:
```powershell
Get-Content -Path "$env:LOCALAPPDATA\REETA\logs\backend.log" -Wait -Tail 50
```

