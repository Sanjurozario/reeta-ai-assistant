import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Task, TaskStep, TaskStatus, User
from app.database.session import async_session_factory

logger = logging.getLogger("reeta.tasks")


class TaskBroadcaster:
    """Manages active WebSocket client connections for real-time task progress."""

    def __init__(self):
        self._active_connections: List[Any] = []

    def connect(self, websocket: Any):
        self._active_connections.append(websocket)

    def disconnect(self, websocket: Any):
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)

    async def broadcast(self, event: str, task_id: str, payload: Dict[str, Any]):
        """Dispatches an event frame to all active WebSocket connections."""
        message = {
            "event": event,
            "task_id": str(task_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        dead_connections = []
        for ws in self._active_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to WebSocket client: {e}")
                dead_connections.append(ws)

        for dead in dead_connections:
            self.disconnect(dead)


broadcaster = TaskBroadcaster()


class TaskManager:
    """Orchestrates task lifecycle, background execution, cancellation, and progress."""

    _active_workers: Dict[str, asyncio.Task] = {}
    _cancellation_events: Dict[str, asyncio.Event] = {}

    @classmethod
    async def create_task(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        objective: str,
        priority: int = 5,
        conversation_id: Optional[uuid.UUID] = None,
    ) -> Task:
        """Initializes a new task in PENDING state."""
        task = Task(
            user_id=user_id,
            conversation_id=conversation_id,
            title=title,
            objective=objective,
            priority=priority,
            status=TaskStatus.PENDING.value,
            plan={"steps": []},
            execution_state={},
            result={},
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

        # Notify clients
        await broadcaster.broadcast(
            event="task_created",
            task_id=str(task.id),
            payload={"title": task.title, "status": task.status, "objective": task.objective},
        )
        return task

    @classmethod
    async def create_steps(
        cls,
        session: AsyncSession,
        task_id: uuid.UUID,
        steps: List[Dict[str, Any]],
    ) -> List[TaskStep]:
        """Creates initial execution steps for a task."""
        created = []
        for s in steps:
            step = TaskStep(
                task_id=task_id,
                step_number=s.get("step_number", len(created) + 1),
                title=s.get("title", f"Step {len(created) + 1}"),
                agent_type=s.get("agent_type", "research"),
                status=TaskStatus.PENDING.value,
                input_payload=s.get("input_payload", {}),
            )
            session.add(step)
            created.append(step)

        # Update task plan
        task_query = select(Task).where(Task.id == task_id)
        task_res = await session.execute(task_query)
        task = task_res.scalar_one_or_none()
        if task:
            task.plan = {"steps": [s.get("title") for s in steps], "total_steps": len(steps)}
            task.status = TaskStatus.PLANNING.value

        await session.commit()

        await broadcaster.broadcast(
            event="plan_generated",
            task_id=str(task_id),
            payload={"total_steps": len(steps), "steps": [s.get("title") for s in steps]},
        )
        return created

    @classmethod
    async def update_task_status(
        cls,
        session: AsyncSession,
        task_id: uuid.UUID,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error_detail: Optional[Dict[str, Any]] = None,
    ) -> Optional[Task]:
        """Transitions task status with timestamp recording and broadcast."""
        query = select(Task).where(Task.id == task_id)
        res = await session.execute(query)
        task = res.scalar_one_or_none()

        if not task:
            return None

        task.status = status.value
        now = datetime.now(timezone.utc)

        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = now
        elif status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            task.completed_at = now

        if result:
            task.result = result
        if error_detail:
            task.error_detail = error_detail

        await session.commit()
        await session.refresh(task)

        await broadcaster.broadcast(
            event=f"task_{status.value}",
            task_id=str(task.id),
            payload={"status": task.status, "result": task.result, "error": task.error_detail},
        )
        return task

    @classmethod
    async def update_step_status(
        cls,
        session: AsyncSession,
        step_id: uuid.UUID,
        status: TaskStatus,
        output_payload: Optional[Dict[str, Any]] = None,
        error_log: Optional[str] = None,
    ) -> Optional[TaskStep]:
        """Updates a specific step's status and outputs."""
        query = select(TaskStep).where(TaskStep.id == step_id)
        res = await session.execute(query)
        step = res.scalar_one_or_none()

        if not step:
            return None

        step.status = status.value
        now = datetime.now(timezone.utc)
        if status == TaskStatus.RUNNING:
            step.started_at = now
        elif status in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
            step.completed_at = now

        if output_payload:
            step.output_payload = output_payload
        if error_log:
            step.error_log = error_log

        await session.commit()
        await session.refresh(step)

        await broadcaster.broadcast(
            event="step_updated",
            task_id=str(step.task_id),
            payload={
                "step_number": step.step_number,
                "title": step.title,
                "status": step.status,
                "output": step.output_payload,
            },
        )
        return step

    @classmethod
    async def cancel_task(cls, session: AsyncSession, task_id: uuid.UUID) -> bool:
        """Cancels a task and interrupts its active background worker."""
        task_str = str(task_id)

        # Trigger cancellation event if worker is listening
        if task_str in cls._cancellation_events:
            cls._cancellation_events[task_str].set()

        # Cancel the asyncio task
        if task_str in cls._active_workers:
            worker = cls._active_workers[task_str]
            if not worker.done():
                worker.cancel()

        # Update DB
        task = await cls.update_task_status(session, task_id, TaskStatus.CANCELLED)
        return task is not None

    @classmethod
    def register_worker(cls, task_id: str, worker: asyncio.Task, cancel_event: asyncio.Event):
        cls._active_workers[task_id] = worker
        cls._cancellation_events[task_id] = cancel_event

    @classmethod
    def unregister_worker(cls, task_id: str):
        cls._active_workers.pop(task_id, None)
        cls._cancellation_events.pop(task_id, None)

    @classmethod
    async def get_task_history(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Task]:
        """Retrieves paginated task execution history."""
        query = (
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(desc(Task.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await session.execute(query)
        return list(res.scalars().all())
