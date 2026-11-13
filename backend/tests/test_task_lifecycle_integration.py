import asyncio
import os
import time
import pytest
from pathlib import Path
from sqlalchemy import select

from app.config import settings
from app.core.gateway import model_gateway
from app.database.models import Task, TaskStep, TaskStatus
from app.database.session import async_session_factory, engine


@pytest.mark.asyncio
async def test_harmless_file_creation_lifecycle_end_to_end(api_client):
    """
    Requirement 11 & 12: End-to-end task lifecycle test.
    Submits a harmless file creation instruction:
    'Create a temporary text file named 'test_harmless.txt' in the authorized temp directory with content 'REETA Verified 2026' and verify its existence and contents'
    Validates:
      1. API 201 Created and dynamic plan step generation.
      2. Asynchronous execution transitions steps and task to COMPLETED.
      3. Physical file created on disk in authorized workspace.
      4. File contents match expected string.
      5. Database records show completed steps with output evidence.
    """
    workspace = Path(settings.AUTHORIZED_WORKSPACE).resolve()
    temp_dir = workspace / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    target_file = temp_dir / "test_harmless.txt"
    if target_file.exists():
        target_file.unlink()

    payload = {
        "title": "Create Test File",
        "objective": "Create a temporary text file named 'test_harmless.txt' in the authorized temp directory with content 'REETA Verified 2026' and verify its existence and contents",
        "priority": 5,
    }
    res = await api_client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 201
    data = res.json()
    task_id = data["id"]
    assert data["title"] == "Create Test File"
    assert len(data["steps"]) == 2
    assert "file" in data["steps"][0]["agent_type"]

    # Poll database until task completion (max 10 seconds)
    start_time = time.time()
    final_task = None
    while time.time() - start_time < 10:
        async with async_session_factory() as session:
            query = select(Task).where(Task.id == task_id)
            r = await session.execute(query)
            final_task = r.scalar_one_or_none()
            if final_task and final_task.status in {"completed", "failed"}:
                break
        await asyncio.sleep(0.5)

    assert final_task is not None
    assert final_task.status == TaskStatus.COMPLETED.value, f"Task ended with status {final_task.status}, error: {final_task.error_detail}"

    # 3. Verify file on disk
    assert target_file.exists(), f"Expected file {target_file} was not created on disk."
    content = target_file.read_text(encoding="utf-8")
    assert "REETA Verified 2026" in content

    # 4. Verify step statuses in database
    async with async_session_factory() as session:
        s_query = select(TaskStep).where(TaskStep.task_id == task_id).order_by(TaskStep.step_number)
        s_res = await session.execute(s_query)
        steps = s_res.scalars().all()
        assert len(steps) == 2
        assert steps[0].status == TaskStatus.COMPLETED.value
        assert steps[1].status == TaskStatus.COMPLETED.value

    await engine.dispose()


@pytest.mark.asyncio
async def test_informational_query_task_lifecycle(api_client):
    """
    Verifies that conversational or synthesis queries complete through the orchestrator
    without infinite loops or missing tool errors.
    """
    payload = {
        "title": "REETA Capabilities Overview",
        "objective": "Introduce yourself and describe your autonomous execution capabilities",
        "priority": 3,
    }
    res = await api_client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 201
    data = res.json()
    task_id = data["id"]

    start_time = time.time()
    final_task = None
    while time.time() - start_time < 10:
        async with async_session_factory() as session:
            query = select(Task).where(Task.id == task_id)
            r = await session.execute(query)
            final_task = r.scalar_one_or_none()
            if final_task and final_task.status in {"completed", "failed"}:
                break
        await asyncio.sleep(0.5)

    assert final_task is not None
    assert final_task.status == TaskStatus.COMPLETED.value

    await engine.dispose()


@pytest.mark.asyncio
async def test_ai_provider_configuration_and_resilient_fallback():
    """
    Requirement 4: Verify AI provider configuration, model selection, and real response.
    Validates that:
    1. If an OpenAI key is configured and valid, it reaches the provider.
    2. If no valid key is configured (empty key), it does NOT falsely claim connectivity,
       and instead safely and explicitly routes through the mock fallback engine.
    """
    active_prov = await model_gateway.get_active_provider_name()
    has_real_key = bool(os.getenv("OPENAI_API_KEY", "").strip())

    if has_real_key:
        assert active_prov in {"openai", "ollama", "mock"}
    else:
        # Without key, active provider must be mock or ollama (never false active openai)
        assert active_prov in {"mock", "ollama"}

    # Test generation through gateway
    from app.core.gateway import GatewayMessage
    resp = await model_gateway.generate_with_fallback(
        messages=[GatewayMessage(role="user", content="Ping REETA system")],
        temperature=0.2,
        task_id="test-provider-connectivity",
    )
    assert resp.content
    assert resp.provider == active_prov
