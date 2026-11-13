import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.permissions.policy import ActionTier
from app.tools.registry import BaseTool, VerificationResult


class PowerShellInput(BaseModel):
    command: str = Field(..., description="PowerShell command line or script to execute.")
    working_directory: Optional[str] = Field(default=None, description="Working directory for the process.")
    timeout_seconds: int = Field(default=30, ge=1, le=180, description="Execution timeout in seconds.")


class PowerShellTool(BaseTool):
    name = "powershell_execute"
    description = "Executes a PowerShell command on the Windows host within strict timeout bounds. Requires Tier 2 permission approval."
    category = "terminal"
    args_schema = PowerShellInput
    default_tier = ActionTier.APPROVAL_REQUIRED
    timeout_seconds = 60.0

    async def execute(
        self,
        command: str,
        working_directory: Optional[str] = None,
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        cwd = working_directory or settings.AUTHORIZED_WORKSPACE

        # Execute using powershell.exe with NonInteractive flag
        process = await asyncio.create_subprocess_exec(
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=float(timeout_seconds),
            )
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"PowerShell command timed out after {timeout_seconds} seconds.")

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        exit_code = process.returncode

        return {
            "command": command,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "success": (exit_code == 0),
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "exit_code" in result:
            code = result["exit_code"]
            if code == 0:
                return VerificationResult(
                    verified=True,
                    evidence=f"PowerShell command exited with status code 0. Captured {len(result.get('stdout', ''))} characters of stdout.",
                )
            else:
                return VerificationResult(
                    verified=False,
                    evidence=f"PowerShell command failed with non-zero exit code {code}: {result.get('stderr') or result.get('stdout')}",
                )
        return VerificationResult(verified=False, evidence="Invalid command execution result.")

