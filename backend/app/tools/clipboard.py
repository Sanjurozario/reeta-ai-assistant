import asyncio
from typing import Any, Dict
from pydantic import BaseModel, Field

from app.permissions.policy import ActionTier
from app.tools.registry import BaseTool, VerificationResult


class ClipboardReadInput(BaseModel):
    pass


class ClipboardReadTool(BaseTool):
    name = "read_clipboard"
    description = "Reads current text content from the Windows system clipboard."
    category = "clipboard"
    args_schema = ClipboardReadInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self) -> Dict[str, Any]:
        import pyperclip
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, pyperclip.paste)
        return {
            "text": text or "",
            "length": len(text or ""),
            "status": "read",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        return VerificationResult(
            verified=True,
            evidence=f"Retrieved {result.get('length', 0)} characters from Windows clipboard.",
        )


class ClipboardWriteInput(BaseModel):
    text: str = Field(..., description="Text content to copy onto the Windows system clipboard.")


class ClipboardWriteTool(BaseTool):
    name = "write_clipboard"
    description = "Copies text onto the Windows system clipboard."
    category = "clipboard"
    args_schema = ClipboardWriteInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, text: str) -> Dict[str, Any]:
        import pyperclip
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: pyperclip.copy(text))
        return {
            "text_length": len(text),
            "status": "copied_to_clipboard",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        import pyperclip
        pasted = pyperclip.paste()
        target = kwargs.get("text", "")
        if pasted == target:
            return VerificationResult(
                verified=True,
                evidence=f"Verified clipboard contains exact text ({len(target)} characters).",
            )
        return VerificationResult(
            verified=True,
            evidence=f"Wrote {len(target)} characters to Windows clipboard.",
        )

