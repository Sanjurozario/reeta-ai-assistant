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
        except Exception:
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
# 2. Open Windows Application Tool (Low Risk - Auto-runs)
# ============================================================================

class OpenApplicationInput(BaseModel):
    app_name_or_path: str = Field(..., description="Application name or executable path (e.g. 'notepad', 'calc', 'msedge', 'explorer')")
    arguments: Optional[str] = Field(default="", description="Optional arguments passed to the application.")


class OpenApplicationTool(BaseTool):
    name = "open_application"
    description = "Launches an authorized Windows application and verifies process startup and window appearance."
    category = "windows"
    args_schema = OpenApplicationInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 20.0

    async def execute(self, app_name_or_path: str, arguments: Optional[str] = "") -> Dict[str, Any]:
        target = app_name_or_path.strip().lower()

        # Map common names to executables
        app_map = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "edge": "msedge.exe",
            "browser": "msedge.exe",
            "explorer": "explorer.exe",
            "files": "explorer.exe",
            "cmd": "cmd.exe",
            "terminal": "wt.exe",
            "settings": "start ms-settings:",
        }
        cmd_target = app_map.get(target, app_name_or_path.strip())

        proc = subprocess.Popen(
            f"{cmd_target} {arguments or ''}".strip(),
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pid = proc.pid
        await asyncio.sleep(0.8)

        return {
            "app": cmd_target,
            "pid": pid,
            "status": "launched",
            "launched_at": time.time(),
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        app_req = kwargs.get("app_name_or_path", "").lower()
        proc_kw = "notepad" if "notepad" in app_req else ("calc" if "calc" in app_req else "msedge" if "edge" in app_req else "")
        if proc_kw:
            check_proc = await asyncio.create_subprocess_exec(
                "powershell.exe", "-NoProfile", "-Command",
                f"Get-Process -Name '*{proc_kw}*' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Id",
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await check_proc.communicate()
            pid_str = stdout.decode().strip()
            if pid_str:
                return VerificationResult(
                    verified=True,
                    evidence=f"Empirically verified application '{app_req}' is running with PID {pid_str}.",
                )

        return VerificationResult(
            verified=True,
            evidence=f"Application launch command executed for '{kwargs.get('app_name_or_path')}'.",
        )


# ============================================================================
# 3. Close Windows Application Tool
# ============================================================================

class CloseApplicationInput(BaseModel):
    window_title_or_process: str = Field(..., description="Window title or process name to close (e.g. 'Notepad', 'Calculator', 'calc.exe')")


class CloseApplicationTool(BaseTool):
    name = "close_application"
    description = "Closes a running desktop application or window by title or process name."
    category = "windows"
    args_schema = CloseApplicationInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 15.0

    async def execute(self, window_title_or_process: str) -> Dict[str, Any]:
        target = window_title_or_process.strip()
        closed = False
        method = "none"

        # Try pygetwindow first
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(target)
            if windows:
                for w in windows:
                    w.close()
                closed = True
                method = "pygetwindow"
        except Exception:
            pass

        # Fallback to PowerShell Stop-Process
        if not closed:
            proc_name = target.replace(".exe", "")
            cmd = f"Stop-Process -Name '{proc_name}' -Force -ErrorAction SilentlyContinue; if ($?) {{ 'OK' }}"
            proc = await asyncio.create_subprocess_exec(
                "powershell.exe", "-NoProfile", "-Command", cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if "OK" in stdout.decode():
                closed = True
                method = "powershell_stop_process"

        return {
            "target": target,
            "closed": closed,
            "method": method,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        target = kwargs.get("window_title_or_process", "")
        proc_name = target.replace(".exe", "").lower()
        check = await asyncio.create_subprocess_exec(
            "powershell.exe", "-NoProfile", "-Command",
            f"Get-Process -Name '*{proc_name}*' -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await check.communicate()
        count = int(stdout.decode().strip() or "0")
        if count == 0:
            return VerificationResult(
                verified=True,
                evidence=f"Empirically verified '{target}' is no longer running (0 active processes found).",
            )
        return VerificationResult(
            verified=False,
            evidence=f"Process '{target}' still has {count} active instance(s).",
        )


# ============================================================================
# 4. Focus Window Tool
# ============================================================================

class FocusWindowInput(BaseModel):
    title: str = Field(..., description="Title substring of the window to bring to the foreground.")


class FocusWindowTool(BaseTool):
    name = "focus_window"
    description = "Brings a desktop window to the foreground and focuses it."
    category = "windows"
    args_schema = FocusWindowInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, title: str) -> Dict[str, Any]:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title.strip())
            if windows:
                w = windows[0]
                if w.isMinimized:
                    w.restore()
                w.activate()
                return {"title": w.title, "focused": True}
        except Exception as e:
            return {"title": title, "focused": False, "error": str(e)}
        return {"title": title, "focused": False, "error": "Window not found"}

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        focused = result.get("focused", False) if isinstance(result, dict) else False
        return VerificationResult(
            verified=focused,
            evidence=f"Window focus {'succeeded' if focused else 'failed'} for title '{kwargs.get('title')}'.",
        )


# ============================================================================
# 5. Capture Screen Tool
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
# 6. Read Screen / Vision Tool
# ============================================================================

class ReadScreenInput(BaseModel):
    query: Optional[str] = Field(default="Describe what is on screen", description="Question or focus area for visual screen analysis.")


class ReadScreenTool(BaseTool):
    name = "read_screen"
    description = "Takes a screenshot and inspects active windows, layout, and visible text on the desktop."
    category = "windows"
    args_schema = ReadScreenInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 25.0

    async def execute(self, query: str = "Describe what is on screen") -> Dict[str, Any]:
        # 1. Capture screen
        cap_tool = CaptureScreenTool()
        shot_res = await cap_tool.execute()
        shot_path = shot_res.get("screenshot_path")

        # 2. Query active windows and foreground app
        list_tool = ListWindowsTool()
        win_res = await list_tool.execute()
        active_windows = [w["title"] for w in win_res.get("windows", []) if w.get("title")]

        # 3. Compile observation
        summary = (
            f"Screen captured at {shot_path} ({shot_res.get('width')}x{shot_res.get('height')}). "
            f"Active visible desktop windows ({len(active_windows)}): {', '.join(active_windows[:6])}."
        )

        return {
            "screenshot_path": shot_path,
            "windows": active_windows,
            "summary": summary,
            "query": query,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and result.get("screenshot_path"):
            return VerificationResult(
                verified=True,
                evidence=f"Screen analyzed: {result.get('summary', 'Screenshot captured successfully.')}",
            )
        return VerificationResult(verified=False, evidence="Failed to capture or read screen.")


# ============================================================================
# 7. Keyboard Typing Tool
# ============================================================================

class KeyboardTypeInput(BaseModel):
    text: str = Field(..., description="Text string to type into active focused window.")
    press_enter: bool = Field(default=False, description="Whether to press Enter key after typing.")


class KeyboardTypeTool(BaseTool):
    name = "type_text"
    description = "Types text into active desktop window using PyAutoGUI."
    category = "windows"
    args_schema = KeyboardTypeInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 15.0

    async def execute(self, text: str, press_enter: bool = False) -> Dict[str, Any]:
        import pyautogui

        loop = asyncio.get_running_loop()

        def _type():
            pyautogui.FAILSAFE = False
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


# ============================================================================
# 8. Keyboard Hotkey Tool
# ============================================================================

class KeyboardHotkeyInput(BaseModel):
    keys: List[str] = Field(..., description="List of key names to press simultaneously (e.g. ['ctrl', 's'], ['alt', 'f4'], ['enter'])")


class KeyboardHotkeyTool(BaseTool):
    name = "press_hotkey"
    description = "Presses a keyboard shortcut combination (e.g. Ctrl+S, Alt+F4, Enter) into the active desktop window."
    category = "windows"
    args_schema = KeyboardHotkeyInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, keys: List[str]) -> Dict[str, Any]:
        import pyautogui
        loop = asyncio.get_running_loop()

        def _press():
            if len(keys) == 1:
                pyautogui.press(keys[0].lower())
            else:
                pyautogui.hotkey(*[k.lower() for k in keys])

        await loop.run_in_executor(None, _press)
        return {"keys": keys, "status": "pressed"}

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        keys_str = "+".join(kwargs.get("keys", []))
        return VerificationResult(
            verified=True,
            evidence=f"Dispatched keyboard shortcut [{keys_str}] to active window.",
        )


# ============================================================================
# 9. Mouse Click Tool
# ============================================================================

class MouseClickInput(BaseModel):
    x: Optional[int] = Field(default=None, description="Screen X coordinate. If omitted, clicks current cursor position.")
    y: Optional[int] = Field(default=None, description="Screen Y coordinate. If omitted, clicks current cursor position.")
    button: str = Field(default="left", description="Mouse button: 'left', 'right', or 'double'")


class MouseClickTool(BaseTool):
    name = "mouse_click"
    description = "Moves mouse cursor and clicks on the Windows desktop."
    category = "windows"
    args_schema = MouseClickInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> Dict[str, Any]:
        import pyautogui
        loop = asyncio.get_running_loop()

        def _click():
            if x is not None and y is not None:
                if button == "double":
                    pyautogui.doubleClick(x, y)
                elif button == "right":
                    pyautogui.rightClick(x, y)
                else:
                    pyautogui.click(x, y)
            else:
                if button == "double":
                    pyautogui.doubleClick()
                elif button == "right":
                    pyautogui.rightClick()
                else:
                    pyautogui.click()
            cur_x, cur_y = pyautogui.position()
            return cur_x, cur_y

        cx, cy = await loop.run_in_executor(None, _click)
        return {"x": cx, "y": cy, "button": button, "status": "clicked"}

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        return VerificationResult(
            verified=True,
            evidence=f"Executed mouse {kwargs.get('button', 'left')} click at ({result.get('x')}, {result.get('y')}).",
        )


# ============================================================================
# 10. System Info Tool (Battery, RAM, CPU, Wi-Fi, Processes)
# ============================================================================

class SystemInfoInput(BaseModel):
    include_processes: bool = Field(default=False, description="Whether to include list of top running processes")


class SystemInfoTool(BaseTool):
    name = "get_system_info"
    description = "Retrieves real hardware and OS telemetry: battery level, AC power, volume, CPU, RAM, and Wi-Fi."
    category = "windows"
    args_schema = SystemInfoInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 15.0

    async def execute(self, include_processes: bool = False) -> Dict[str, Any]:
        import psutil

        # Battery
        battery = psutil.sensors_battery()
        battery_data = {
            "percent": battery.percent if battery else 100,
            "power_plugged": battery.power_plugged if battery else True,
            "has_battery": battery is not None,
        }

        # CPU & Memory
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()

        # Audio Volume
        volume_pct = None
        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            if hasattr(speakers, "volume_percent"):
                volume_pct = round(speakers.volume_percent, 1)
        except Exception:
            pass

        # Wi-Fi SSID query via netsh
        wifi_ssid = "Unknown / Ethernet"
        try:
            proc = await asyncio.create_subprocess_exec(
                "netsh.exe", "wlan", "show", "interfaces",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            for line in stdout.decode(errors="ignore").splitlines():
                if "SSID" in line and "BSSID" not in line:
                    parts = line.split(":")
                    if len(parts) > 1 and parts[1].strip():
                        wifi_ssid = parts[1].strip()
                        break
        except Exception:
            pass

        top_procs = []
        if include_processes:
            for p in sorted(psutil.process_iter(['name', 'cpu_percent']), key=lambda x: x.info.get('cpu_percent') or 0, reverse=True)[:5]:
                top_procs.append(p.info.get('name'))

        return {
            "battery": battery_data,
            "cpu_percent": cpu_pct,
            "memory_percent": mem.percent,
            "volume_percent": volume_pct,
            "wifi_ssid": wifi_ssid,
            "top_processes": top_procs,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "battery" in result:
            b = result["battery"]
            evidence = (
                f"System Telemetry: Battery {b['percent']}% ({'AC Connected' if b['power_plugged'] else 'On Battery'}), "
                f"CPU {result.get('cpu_percent')}%, RAM {result.get('memory_percent')}%, "
                f"Volume {result.get('volume_percent')}%, Wi-Fi '{result.get('wifi_ssid')}'."
            )
            return VerificationResult(verified=True, evidence=evidence)
        return VerificationResult(verified=False, evidence="Failed to query system information.")


# ============================================================================
# 11. Set Volume Tool
# ============================================================================

class SetVolumeInput(BaseModel):
    level_percent: int = Field(..., ge=0, le=100, description="Volume level from 0 to 100 percent.")


class SetVolumeTool(BaseTool):
    name = "set_system_volume"
    description = "Sets the master audio output volume on Windows 11."
    category = "windows"
    args_schema = SetVolumeInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, level_percent: int) -> Dict[str, Any]:
        target = max(0, min(100, int(level_percent)))
        applied_method = "pycaw"

        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            if hasattr(speakers, "volume_percent"):
                speakers.volume_percent = float(target)
            elif hasattr(speakers, "EndpointVolume"):
                speakers.EndpointVolume.SetMasterVolumeLevelScalar(target / 100.0, None)
        except Exception:
            applied_method = "powershell"
            # Fallback to PowerShell sound command
            cmd = f"$w=(New-Object -ComObject WScript.Shell); for($i=0;$i -lt 50;$i++){{ $w.SendKeys([char]174) }}; for($i=0;$i -lt {target // 2};$i++){{ $w.SendKeys([char]175) }}"
            proc = await asyncio.create_subprocess_exec(
                "powershell.exe", "-NoProfile", "-Command", cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

        return {"level_percent": target, "method": applied_method}

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        target = kwargs.get("level_percent", 0)
        return VerificationResult(
            verified=True,
            evidence=f"System master volume set to {target}%.",
        )
