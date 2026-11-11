import uuid
import pytest
from app.database.models import User, TaskStatus
from app.core.tasks import TaskManager


@pytest.mark.asyncio
async def test_task_lifecycle_and_cancellation(db_session):
    # 1. Create User
    user = User(username=f"task_u_{uuid.uuid4().hex[:6]}", password_hash="pw")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 2. Create Task
    task = await TaskManager.create_task(
        session=db_session,
        user_id=user.id,
        title="Automated Test Workflow",
        objective="Verify state transitions",
    )
    assert task.status == TaskStatus.PENDING.value
    assert task.title == "Automated Test Workflow"

    # 3. Add Steps
    steps_def = [
        {"step_number": 1, "title": "Scrape website", "agent_type": "browser"},
        {"step_number": 2, "title": "Extract tables", "agent_type": "research"},
    ]
    created_steps = await TaskManager.create_steps(db_session, task.id, steps_def)
    assert len(created_steps) == 2
    assert created_steps[0].step_number == 1

    # 4. Update Step 1 to RUNNING, then COMPLETED
    step1 = await TaskManager.update_step_status(
        db_session,
        step_id=created_steps[0].id,
        status=TaskStatus.RUNNING,
    )
    assert step1.status == TaskStatus.RUNNING.value
    assert step1.started_at is not None

    step1 = await TaskManager.update_step_status(
        db_session,
        step_id=created_steps[0].id,
        status=TaskStatus.COMPLETED,
        output_payload={"url": "https://example.com", "rows": 10},
    )
    assert step1.status == TaskStatus.COMPLETED.value
    assert step1.output_payload["rows"] == 10

    # 5. Cancel Task
    cancelled = await TaskManager.cancel_task(db_session, task.id)
    assert cancelled is True

    # 6. Check History
    history = await TaskManager.get_task_history(db_session, user.id, limit=5)
    assert len(history) >= 1
    assert history[0].status == TaskStatus.CANCELLED.value

    # Cleanup
    await db_session.delete(task)
    await db_session.delete(user)
    await db_session.commit()
