import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.permissions.policy import ActionTier
from app.tools.registry import BaseTool, VerificationResult


class CreateReminderInput(BaseModel):
    title: str = Field(..., description="Reminder note or task title")
    due_time: Optional[str] = Field(default=None, description="Due date/time string (ISO or readable)")


class CreateReminderTool(BaseTool):
    name = "create_reminder"
    description = "Saves a reminder note for the user."
    category = "productivity"
    args_schema = CreateReminderInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, title: str, due_time: Optional[str] = None) -> Dict[str, Any]:
        return {
            "reminder_id": str(uuid.uuid4()),
            "title": title,
            "due_time": due_time or "today",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "reminder_id" in result:
            return VerificationResult(
                verified=True,
                evidence=f"Reminder created for '{result.get('title')}' (ID: {result.get('reminder_id')[:8]}).",
            )
        return VerificationResult(verified=False, evidence="Failed to create reminder.")
