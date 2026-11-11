import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    TaskCreateRequest,
    TaskDetailResponse,
    TaskStepResponse,
    TaskCancelResponse,
)
from app.core.tasks import TaskManager
from app.database.models import Task, TaskStep, TaskStatus, User
from app.database.session import get_db

router = APIRouter(prefix="/tasks", tags=["Tasks"])


async def get_or_create_default_user(session: AsyncSession) -> User:
    """Ensures at least one local user profile exists for desktop operation."""
    query = select(User).limit(1)
    res = await session.execute(query)
    user = res.scalar_one_or_none()
    if not user:
        user = User(
            username="local_operator",
            display_name="Desktop Operator",
            email="operator@local.reeta",
            password_hash="local_authenticated",
            preferences={"theme": "obsidian", "accent": "cyan"},
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@router.post("", response_model=TaskDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_task(req: TaskCreateRequest, session: AsyncSession = Depends(get_db)):
    """Creates a new autonomous task and initializes planning."""
    user_id = req.user_id
    if not user_id:
        default_user = await get_or_create_default_user(session)
        user_id = default_user.id

    task = await TaskManager.create_task(
        session=session,
        user_id=user_id,
        title=req.title,
        objective=req.objective,
        priority=req.priority,
        conversation_id=req.conversation_id,
    )

    # Initial mock step generation for testing
    steps = [
        {"step_number": 1, "title": "Analyze and decompose objective", "agent_type": "orchestrator"},
        {"step_number": 2, "title": f"Execute '{req.title}'", "agent_type": "research"},
        {"step_number": 3, "title": "Verify outcome and artifacts", "agent_type": "verification"},
    ]
    created_steps = await TaskManager.create_steps(session, task.id, steps)

    return TaskDetailResponse(
        id=task.id,
        title=task.title,
        objective=task.objective,
        status=task.status,
        priority=task.priority,
        plan=task.plan,
        result=task.result,
        error_detail=task.error_detail,
        verification_status=task.verification_status,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
        steps=[
            TaskStepResponse(
                id=s.id,
                step_number=s.step_number,
                title=s.title,
                agent_type=s.agent_type,
                status=s.status,
                input_payload=s.input_payload,
                output_payload=s.output_payload,
                error_log=s.error_log,
                created_at=s.created_at,
            )
            for s in created_steps
        ],
    )


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    """Retrieves full task details with all plan steps."""
    query = (
        select(Task)
        .options(selectinload(Task.steps))
        .where(Task.id == task_id)
    )
    res = await session.execute(query)
    task = res.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    return TaskDetailResponse(
        id=task.id,
        title=task.title,
        objective=task.objective,
        status=task.status,
        priority=task.priority,
        plan=task.plan,
        result=task.result,
        error_detail=task.error_detail,
        verification_status=task.verification_status,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
        steps=[
            TaskStepResponse(
                id=s.id,
                step_number=s.step_number,
                title=s.title,
                agent_type=s.agent_type,
                status=s.status,
                input_payload=s.input_payload,
                output_payload=s.output_payload,
                error_log=s.error_log,
                created_at=s.created_at,
            )
            for s in task.steps
        ],
    )


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(task_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    """Signals immediate cancellation to a running or pending task."""
    success = await TaskManager.cancel_task(session, task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    return TaskCancelResponse(
        success=True,
        task_id=task_id,
        status=TaskStatus.CANCELLED.value,
    )


@router.get("", response_model=List[TaskDetailResponse])
async def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    """Returns paginated task history."""
    query = (
        select(Task)
        .options(selectinload(Task.steps))
        .order_by(desc(Task.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(query)
    tasks = res.scalars().all()

    return [
        TaskDetailResponse(
            id=t.id,
            title=t.title,
            objective=t.objective,
            status=t.status,
            priority=t.priority,
            plan=t.plan,
            result=t.result,
            error_detail=t.error_detail,
            verification_status=t.verification_status,
            started_at=t.started_at,
            completed_at=t.completed_at,
            created_at=t.created_at,
            steps=[
                TaskStepResponse(
                    id=s.id,
                    step_number=s.step_number,
                    title=s.title,
                    agent_type=s.agent_type,
                    status=s.status,
                    input_payload=s.input_payload,
                    output_payload=s.output_payload,
                    error_log=s.error_log,
                    created_at=s.created_at,
                )
                for s in t.steps
            ],
        )
        for t in tasks
    ]
