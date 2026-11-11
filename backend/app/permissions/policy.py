import fnmatch
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
from app.config import settings


class ActionTier(str, Enum):
    AUTONOMOUS = "autonomous"          # Tier 1: Auto-granted
    APPROVAL_REQUIRED = "approval_required"  # Tier 2: Demands explicit human approval
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

    # Consequential / Approval-Required Patterns (Tier 2)
    CONSEQUENTIAL_ACTIONS = {
        "terminal_execute",
        "powershell_execute",
        "delete_file",
        "delete_folder",
        "install_package",
        "send_email",
        "http_external_post",
        "browser_submit_payment",
        "schedule_recurring_task",
    }

    # Safe Read-only / Autonomous Patterns (Tier 1)
    AUTONOMOUS_ACTIONS = {
        "web_search",
        "fetch_web_page",
        "read_file",
        "list_directory",
        "search_codebase",
        "get_system_metrics",
        "list_open_windows",
        "capture_screen",
        "memory_search",
        "create_local_reminder",
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
                return ActionTier.RESTRICTED, f"Command contains prohibited destructive payload."

        # 2. Workspace Jail check for File Operations
        effective_workspace = Path(workspace_path or settings.AUTHORIZED_WORKSPACE).resolve()
        if action_name in {"write_file", "create_file", "append_file", "modify_file"}:
            if target:
                try:
                    resolved_target = Path(target).resolve()
                    if not resolved_target.is_relative_to(effective_workspace):
                        return (
                            ActionTier.APPROVAL_REQUIRED,
                            f"File operation targets location '{target}' outside authorized workspace '{effective_workspace}'.",
                        )
                    # Within workspace, file writes are Autonomous
                    return ActionTier.AUTONOMOUS, "File creation within authorized workspace is permitted."
                except Exception as e:
                    return ActionTier.APPROVAL_REQUIRED, f"Invalid target path structure: {e}"

        # 3. Tier 2 Check: Consequential actions requiring approval
        if action_name in cls.CONSEQUENTIAL_ACTIONS:
            return ActionTier.APPROVAL_REQUIRED, f"Action '{action_name}' requires explicit user authorization."

        # 4. Tier 1 Check: Autonomous safe list
        if action_name in cls.AUTONOMOUS_ACTIONS:
            return ActionTier.AUTONOMOUS, f"Action '{action_name}' is pre-approved for autonomous execution."

        # 5. Default Fallback: Zero-Trust requires approval for unknown actions
        return (
            ActionTier.APPROVAL_REQUIRED,
            f"Action '{action_name}' is not in the autonomous allowlist. Escalating to human approval.",
        )
