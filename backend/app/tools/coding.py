import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.permissions.policy import ActionTier
from app.tools.registry import BaseTool, VerificationResult


class CodeSearchInput(BaseModel):
    pattern: str = Field(..., description="Regex or string pattern to locate in code (e.g. 'def process_order', 'import os')")
    file_extension: Optional[str] = Field(default=".py", description="Filter by file extension")
    directory: Optional[str] = Field(default=None, description="Directory to search")


class CodeSearchTool(BaseTool):
    name = "code_search"
    description = "Searches the codebase for specific functions, classes, bugs, or symbols."
    category = "coding"
    args_schema = CodeSearchInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 20.0

    async def execute(
        self,
        pattern: str,
        file_extension: Optional[str] = ".py",
        directory: Optional[str] = None,
    ) -> Dict[str, Any]:
        root = Path(directory or settings.AUTHORIZED_WORKSPACE).resolve()
        matches = []
        regex = re.compile(pattern, re.IGNORECASE)

        for p in root.rglob(f"*{file_extension}"):
            if p.is_file() and "venv" not in p.parts and "node_modules" not in p.parts and ".git" not in p.parts:
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, start=1):
                            if regex.search(line):
                                matches.append({
                                    "file": str(p),
                                    "relative_file": str(p.relative_to(root)),
                                    "line_number": line_num,
                                    "line_content": line.strip(),
                                })
                                if len(matches) >= 50:
                                    break
                except Exception:
                    pass

        return {
            "pattern": pattern,
            "total_matches": len(matches),
            "matches": matches,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "total_matches" in result:
            return VerificationResult(
                verified=True,
                evidence=f"Code search completed: found {result['total_matches']} occurrences matching '{result.get('pattern')}'.",
            )
        return VerificationResult(verified=False, evidence="Code search failed.")


class CodePatchInput(BaseModel):
    filepath: str = Field(..., description="Target code file path to modify")
    target_block: str = Field(..., description="Exact code block to replace")
    replacement_block: str = Field(..., description="New code block")


class CodePatchTool(BaseTool):
    name = "code_patch"
    description = "Applies a targeted fix or patch to a source code file."
    category = "coding"
    args_schema = CodePatchInput
    default_tier = ActionTier.APPROVAL_REQUIRED
    timeout_seconds = 20.0

    async def execute(self, filepath: str, target_block: str, replacement_block: str) -> Dict[str, Any]:
        path = Path(filepath).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Source file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if target_block not in content:
            raise ValueError(f"Target block to replace was not found in {path.name}.")

        new_content = content.replace(target_block, replacement_block, 1)

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {
            "file": str(path),
            "status": "patched",
            "bytes_before": len(content),
            "bytes_after": len(new_content),
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        path = Path(kwargs.get("filepath", "")).resolve()
        replacement = kwargs.get("replacement_block", "")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                current_text = f.read()
            if replacement in current_text:
                return VerificationResult(
                    verified=True,
                    evidence=f"Empirically confirmed patched block is present in {path.name}.",
                )
        return VerificationResult(verified=False, evidence="Patched block is not present in target file.")


class RunTestsInput(BaseModel):
    test_command: Optional[str] = Field(default="pytest", description="Test runner command (e.g. 'pytest backend/tests -q')")
    working_directory: Optional[str] = Field(default=None, description="Working directory for test runner")


class RunTestsTool(BaseTool):
    name = "run_tests"
    description = "Executes automated tests and verifies all pass."
    category = "coding"
    args_schema = RunTestsInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 60.0

    async def execute(self, test_command: Optional[str] = "pytest", working_directory: Optional[str] = None) -> Dict[str, Any]:
        cwd = working_directory or settings.AUTHORIZED_WORKSPACE
        python_exe = str(Path(settings.AUTHORIZED_WORKSPACE) / "backend" / "venv" / "Scripts" / "python.exe")
        cmd = f'& "{python_exe}" -m {test_command}' if test_command.startswith("pytest") else test_command

        proc = await asyncio.create_subprocess_exec(
            "powershell.exe", "-NoProfile", "-Command", cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        stdout, stderr = await proc.communicate()
        out_str = stdout.decode("utf-8", errors="replace")
        err_str = stderr.decode("utf-8", errors="replace")
        exit_code = proc.returncode

        return {
            "command": test_command,
            "exit_code": exit_code,
            "passed": (exit_code == 0),
            "stdout": out_str[-2000:],  # last 2000 chars
            "stderr": err_str[-2000:],
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "exit_code" in result:
            passed = result.get("passed", False)
            return VerificationResult(
                verified=passed,
                evidence=f"Test run finished with exit code {result['exit_code']} (Passed: {passed}).",
                details={"exit_code": result["exit_code"]},
            )
        return VerificationResult(verified=False, evidence="Test execution produced no result.")
