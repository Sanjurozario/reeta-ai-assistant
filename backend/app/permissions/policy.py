import fnmatch
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
from app.config import settings


class ActionTier(str, Enum):
    AUTONOMOUS = "autonomous"          # Tier 1: Low risk, auto-granted
    APPROVAL_REQUIRED = "approval_required"  # Tier 2: High risk / consequential, demands human approval
    RESTRICTED = "restricted"          # Tier 3: Hard-blocked by security policy


class PolicyEngine:
    """Evaluates requested tool executions against strict 3-tier security rules."""

    # Permanent Hard-blocked Patterns (Tier 3)
    RESTRICTED_RESOURCES = [
        "*Windows/System32/config*",  # SAM hive
        "*Windows/System32/SAM*",
        "*.env*",                      # Environment secrets
        "*AppData/Local/Google/Chrome/User Data/Default/Login Data*",
        "*AppData/Roaming/Mozilla/Firefox/Profiles/*/logins.json*",
        "*id_rsa*",
        "*id_ed25519*",
        "*.pem*",
        "*.key*",
    ]

    RESTRICTED_COMMANDS = [
        "*rmdir /s /q c:\\*",
        "*rm -rf /*",
        "*format c:*",
        "*netsh firewall set opmode disable*",
        "*Set-MpPreference -DisableRealtimeMonitoring $true*",
    ]

    # Consequential / Approval-Required Patterns (Tier 2 - High Risk)
    CONSEQUENTIAL_ACTIONS = {
        "delete_file",
        "delete_folder",
        "powershell_execute",
        "terminal_execute",
        "install_package",
        "send_email",
        "browser_submit_payment",
        "http_external_post",
    }

    # Safe Read-only / Low-risk Autonomous Patterns (Tier 1)
    AUTONOMOUS_ACTIONS = {
        "open_application",
        "close_application",
        "focus_window",
        "list_open_windows",
        "capture_screen",
        "read_screen",
        "type_text",
        "press_hotkey",
        "mouse_click",
        "get_system_info",
        "set_system_volume",
        "read_clipboard",
        "write_clipboard",
        "file_search",
        "search_files",
        "read_file",
        "write_file",
        "move_file",
        "copy_file",
        "rename_file",
        "create_directory",
        "organize_folder",
        "create_pdf_report",
        "browser_navigate",
        "browser_extract_tables",
        "browser_search",
        "browser_download",
        "web_search",
        "code_search",
        "code_patch",
        "run_tests",
        "run_script",
        "create_reminder",
        "start_timer",
        "manage_notes",
        "memory_store",
        "memory_search",
        "memory_forget",
    }

    @classmethod
    def evaluate(
        cls,
        action: str,
        target_resource: Optional[str] = None,
        workspace_path: Optional[str] = None,
    ) -> Tuple[ActionTier, str]:
        """
        Evaluates a requested action and target resource against policy.
        Returns (ActionTier, reason).
        """
        target = (target_resource or "").strip()
        action_name = action.lower().strip()

        # 1. Tier 3 Check: Hard Restricted Prohibitions
        for pattern in cls.RESTRICTED_RESOURCES:
            if fnmatch.fnmatch(target.lower(), pattern.lower()):
                return ActionTier.RESTRICTED, f"Target resource '{target}' matches restricted credential/system pattern."

        for pattern in cls.RESTRICTED_COMMANDS:
            if fnmatch.fnmatch(target.lower(), pattern.lower()):
                return ActionTier.RESTRICTED, f"Command '{target}' is permanently prohibited by safety policy."

        # 2. Tier 2 Check: Explicit Consequential Actions
        if action_name in cls.CONSEQUENTIAL_ACTIONS:
            return (
                ActionTier.APPROVAL_REQUIRED,
                f"Action '{action}' is classified as Tier 2 consequential and requires operator authorization.",
            )

        # 3. Path-based containment check for file mutations
        if action_name in {"write_file", "create_directory", "move_file", "copy_file", "rename_file", "delete_file"}:
            if target:
                ws = Path(workspace_path or settings.AUTHORIZED_WORKSPACE).resolve()
                try:
                    tp = Path(target).resolve()
                    # If outside authorized workspace and outside temp / projects, ask permission
                    if not str(tp).lower().startswith(str(ws).lower()):
                        # Allow standard user Downloads/Desktop/temp if safe
                        user_profile = Path(os.environ.get("USERPROFILE", "")).resolve()
                        safe_subdirs = [user_profile / "Downloads", user_profile / "Desktop", user_profile / "Documents"]
                        is_safe_subdir = any(str(tp).lower().startswith(str(d).lower()) for d in safe_subdirs)
                        if not is_safe_subdir:
                            return (
                                ActionTier.APPROVAL_REQUIRED,
                                f"Resource '{target}' is outside authorized workspace ({ws}). Requires operator authorization.",
                            )
                except Exception:
                    pass

        # 4. Tier 1 Check: Known Autonomous Actions
        if action_name in cls.AUTONOMOUS_ACTIONS:
            return ActionTier.AUTONOMOUS, f"Action '{action}' is authorized for autonomous execution."

        # Default fallback: Low risk autonomous if not explicitly dangerous
        return ActionTier.AUTONOMOUS, f"Action '{action}' permitted under default low-risk policy."
