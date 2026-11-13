import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.permissions.policy import ActionTier
from app.tools.registry import BaseTool, VerificationResult


class CreateReminderInput(BaseModel):
    title: str = Field(..., description="Reminder note or task title")
    due_time: Optional[str] = Field(default=None, description="Due date/time string (ISO or readable, e.g. '5:00 PM', 'tomorrow')")


class CreateReminderTool(BaseTool):
    name = "create_reminder"
    description = "Saves a reminder note for the user."
    category = "productivity"
    args_schema = CreateReminderInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, title: str, due_time: Optional[str] = None) -> Dict[str, Any]:
        workspace = Path(settings.AUTHORIZED_WORKSPACE)
        reminders_file = workspace / "reminders.txt"
        reminders_file.parent.mkdir(parents=True, exist_ok=True)

        entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] DUE: {due_time or 'Today'} | {title}\n"
        with open(reminders_file, "a", encoding="utf-8") as f:
            f.write(entry)

        return {
            "reminder_id": str(uuid.uuid4()),
            "title": title,
            "due_time": due_time or "today",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "saved_to_reminders",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "reminder_id" in result:
            return VerificationResult(
                verified=True,
                evidence=f"Reminder created for '{result.get('title')}' (due: {result.get('due_time')}).",
            )
        return VerificationResult(verified=False, evidence="Failed to create reminder.")


# ============================================================================
# 2. Start Timer Tool
# ============================================================================

class StartTimerInput(BaseModel):
    duration_minutes: float = Field(..., ge=0.1, le=1440.0, description="Timer duration in minutes (e.g. 10 for 10 minutes)")
    label: Optional[str] = Field(default="Timer", description="Label or purpose for the timer")


class StartTimerTool(BaseTool):
    name = "start_timer"
    description = "Starts a background countdown timer with desktop notification when complete."
    category = "productivity"
    args_schema = StartTimerInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, duration_minutes: float, label: str = "Timer") -> Dict[str, Any]:
        seconds = int(duration_minutes * 60)
        end_time = time.time() + seconds

        # Spawn non-blocking background notification task
        async def _timer_worker():
            from app.core.tasks import broadcaster
            await asyncio.sleep(min(seconds, 3600))
            await broadcaster.broadcast(
                event="timer_finished",
                payload={
                    "label": label,
                    "duration_minutes": duration_minutes,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        asyncio.create_task(_timer_worker())

        return {
            "label": label,
            "duration_minutes": duration_minutes,
            "seconds": seconds,
            "ends_at": datetime.fromtimestamp(end_time, timezone.utc).isoformat(),
            "status": "running",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        duration = kwargs.get("duration_minutes")
        label = kwargs.get("label", "Timer")
        return VerificationResult(
            verified=True,
            evidence=f"Started {duration}-minute timer for '{label}'.",
        )


# ============================================================================
# 3. Manage Notes / To-Do List Tool
# ============================================================================

class ManageNotesInput(BaseModel):
    action: str = Field(default="add", description="'add', 'list', or 'draft'")
    content: str = Field(..., description="Note text, to-do item, or draft text")
    list_name: Optional[str] = Field(default="todo", description="Name of list (e.g. 'todo', 'notes', 'email_drafts')")


class ManageNotesTool(BaseTool):
    name = "manage_notes"
    description = "Manages user to-do lists, notes, and drafts in the workspace."
    category = "productivity"
    args_schema = ManageNotesInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, content: str, action: str = "add", list_name: str = "todo") -> Dict[str, Any]:
        workspace = Path(settings.AUTHORIZED_WORKSPACE)
        safe_name = "".join(c for c in list_name if c.isalnum() or c in "_-") or "notes"
        target_file = workspace / f"{safe_name}.txt"
        target_file.parent.mkdir(parents=True, exist_ok=True)

        if action in ("add", "draft"):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"[{timestamp}] {content}\n"
            with open(target_file, "a", encoding="utf-8") as f:
                f.write(entry)
            status = "appended"
        else:
            status = "listed"

        all_text = ""
        if target_file.exists():
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                all_text = f.read()

        return {
            "list_name": safe_name,
            "file_path": str(target_file),
            "status": status,
            "total_length": len(all_text),
            "content": all_text,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and result.get("file_path"):
            p = Path(result["file_path"])
            if p.exists():
                return VerificationResult(
                    verified=True,
                    evidence=f"Updated note/to-do list '{result.get('list_name')}' at {p}.",
                )
        return VerificationResult(verified=False, evidence="Failed to save note.")
