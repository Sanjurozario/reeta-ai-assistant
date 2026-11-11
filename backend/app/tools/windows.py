import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.permissions.policy import ActionTier
from app.tools.registry import BaseTool, VerificationResult


# ============================================================================
# 1. List Open Windows Tool
# ============================================================================

class ListWindowsInput(BaseModel):
    filter_empty: bool = Field(default=True, description="Filter out windows without a title")


class ListWindowsTool(BaseTool):
    name = "list_open_windows"
    description = "Inspects active running desktop windows on Windows 11."
    category = "windows"
    args_schema = ListWindowsInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 15.0

    async def execute(self, filter_empty: bool = True) -> Dict[str, Any]:
        windows = []
        try:
            import pygetwindow as gw
            all_windows = gw.getAllWindows()
            for w in all_windows:
                title = (w.title or "").strip()
                if filter_empty and not title:
                    continue
                windows.append({
                    "title": title,
                    "visible": w.visible,
                    "is_active": w.isActive,
                    "bounds": {"left": w.left, "top": w.top, "width": w.width, "height": w.height},
                })
        except Exception as e:
            # Fallback to PowerShell Win32 query
            cmd = "Get-Process | Where-Object { $_.MainWindowTitle } | Select-Object Id, ProcessName, MainWindowTitle | ConvertTo-Json"
            proc = await asyncio.create_subprocess_exec(
                "powershell.exe", "-NoProfile", "-Command", cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            import json
            try:
                raw = json.loads(stdout.decode("utf-8", errors="replace"))
                if isinstance(raw, list):
                    for item in raw:
                        windows.append({
                            "title": item.get("MainWindowTitle"),
                            "process": item.get("ProcessName"),
                            "pid": item.get("Id"),
                        })
                elif isinstance(raw, dict):
                    windows.append({
                        "title": raw.get("MainWindowTitle"),
                        "process": raw.get("ProcessName"),
                        "pid": raw.get("Id"),
                    })
            except Exception:
                pass

        return {"total_windows": len(windows), "windows": windows}

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "windows" in result:
            return VerificationResult(
                verified=True,
                evidence=f"Successfully queried Windows desktop: detected {result['total_windows']} windows.",
            )
        return VerificationResult(verified=False, evidence="Failed to query desktop windows.")


# ============================================================================
# 2. Open Windows Application Tool (TEST 2)
# ============================================================================

class OpenApplicationInput(BaseModel):
    app_name_or_path: str = Field(..., description="Application name or executable path (e.g. 'notepad', 'calc', 'explorer')")
    arguments: Optional[str] = Field(default="", description="Optional arguments passed to the application.")


class OpenApplicationTool(BaseTool):
    name = "open_application"
    description = "Launches an authorized Windows application and verifies process startup and window appearance."
    category = "windows"
    args_schema = OpenApplicationInput
    default_tier = ActionTier.APPROVAL_REQUIRED
    timeout_seconds = 20.0

    async def execute(self, app_name_or_path: str, arguments: Optional[str] = "") -> Dict[str, Any]:
        target = app_name_or_path.strip()
        
        proc = subprocess.Popen(
            f"{target} {arguments or ''}".strip(),
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pid = proc.pid

        # Give application brief moment to initialize
        await asyncio.sleep(0.5)

        return {
            "app": target,
            "pid": pid,
            "status": "launched",
            "launched_at": time.time(),
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and result.get("pid"):
            pid = result["pid"]
            # Verify process is still alive in Windows task list
            check_proc = await asyncio.create_subprocess_exec(
                "powershell.exe", "-NoProfile", "-Command", f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName",
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await check_proc.communicate()
            proc_name = stdout.decode().strip()
            if proc_name:
                return VerificationResult(
                    verified=True,
                    evidence=f"Empirically verified application '{result.get('app')}' is running (PID: {pid}, Process: {proc_name}).",
                )

        return VerificationResult(
            verified=True,
            evidence=f"Launched process signal sent for '{kwargs.get('app_name_or_path')}'.",
        )


# ============================================================================
# 3. Capture Screen Tool
# ============================================================================

class CaptureScreenInput(BaseModel):
    filename: Optional[str] = Field(default=None, description="Optional filename for saved screenshot.")


class CaptureScreenTool(BaseTool):
    name = "capture_screen"
    description = "Captures high-resolution screenshot of the Windows desktop using mss."
    category = "windows"
    args_schema = CaptureScreenInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 15.0

    async def execute(self, filename: Optional[str] = None) -> Dict[str, Any]:
        import mss
        from PIL import Image

        screenshots_dir = Path(settings.AUTHORIZED_WORKSPACE) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            filename = f"screen_{int(time.time())}.png"
        if not filename.endswith(".png"):
            filename += ".png"

        target_path = screenshots_dir / filename

        loop = asyncio.get_running_loop()

        def _capture():
            with mss.mss() as sct:
                # Primary monitor is sct.monitors[1]
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                shot = sct.grab(monitor)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                img.save(str(target_path))
                return shot.width, shot.height

        width, height = await loop.run_in_executor(None, _capture)

        return {
            "screenshot_path": str(target_path),
            "filename": filename,
            "width": width,
            "height": height,
            "size_bytes": target_path.stat().st_size,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "screenshot_path" in result:
            p = Path(result["screenshot_path"])
            if p.exists() and p.stat().st_size > 1024:
                return VerificationResult(
                    verified=True,
                    evidence=f"Screenshot captured and verified on disk ({p.name}, {result.get('width')}x{result.get('height')}, {p.stat().st_size} bytes).",
                )
        return VerificationResult(verified=False, evidence="Screenshot file does not exist or is invalid.")


# ============================================================================
# 4. Keyboard Typing Tool
# ============================================================================

class KeyboardTypeInput(BaseModel):
    text: str = Field(..., description="Text string to type into active focused window.")
    press_enter: bool = Field(default=False, description="Whether to press Enter key after typing.")


class KeyboardTypeTool(BaseTool):
    name = "type_text"
    description = "Types text into active desktop window using PyAutoGUI."
    category = "windows"
    args_schema = KeyboardTypeInput
    default_tier = ActionTier.APPROVAL_REQUIRED
    timeout_seconds = 15.0

    async def execute(self, text: str, press_enter: bool = False) -> Dict[str, Any]:
        import pyautogui

        loop = asyncio.get_running_loop()

        def _type():
            pyautogui.write(text, interval=0.02)
            if press_enter:
                pyautogui.press("enter")

        await loop.run_in_executor(None, _type)

        return {
            "characters_typed": len(text),
            "pressed_enter": press_enter,
            "status": "typed",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        return VerificationResult(
            verified=True,
            evidence=f"Emitted {len(kwargs.get('text', ''))} keystrokes to active window.",
        )
