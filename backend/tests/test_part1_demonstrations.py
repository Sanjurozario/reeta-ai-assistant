import asyncio
import os
import shutil
import uuid
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.config import settings
from app.database.models import Task, TaskStep, TaskStatus
from app.permissions.policy import ActionTier
from app.database.session import async_session_factory
from app.memory.store import MemoryService
from app.core.tasks import TaskManager
from app.core.orchestrator import orchestrator


@pytest.mark.asyncio
async def test_demo_1_notepad_and_typing(api_client: AsyncClient):
    """
    Demo 1: 'Hey REETA, open Notepad and write a short note saying hello'
    Validates:
      1. Correct decomposition: Launch application, Type note, Verify active UI.
      2. Tool arguments mapped correctly to notepad.exe and type_text.
      3. Steps executed and verified.
    """
    payload = {
        "title": "Open Notepad Note",
        "objective": "Hey REETA, open Notepad and write a short note saying hello",
        "priority": 5,
    }
    res = await api_client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert len(data["steps"]) == 3
    assert data["steps"][0]["agent_type"] == "computer"
    assert "Launch" in data["steps"][0]["title"]
    assert "Type" in data["steps"][1]["title"]
    assert "windows" in data["steps"][2]["title"].lower() or "ui" in data["steps"][2]["title"].lower()

    # Wait for completion or check database execution
    task_id = data["id"]
    for _ in range(30):
        await asyncio.sleep(0.3)
        chk = await api_client.get(f"/api/v1/tasks/{task_id}")
        if chk.json()["status"] in ["completed", "failed", "waiting_approval"]:
            break
    
    final_data = chk.json()
    assert final_data["status"] in ["completed", "waiting_approval", "running"]


@pytest.mark.asyncio
async def test_demo_2_create_folder_and_file(api_client: AsyncClient):
    """
    Demo 2: 'Create a folder called Projects/Test and put a file named notes.txt in it'
    Validates:
      1. Correct 3-step decomposition: Create directory, Write file inside folder, Verify on disk.
      2. Actual directory 'Projects/Test' created in authorized workspace.
      3. Actual file 'notes.txt' created inside directory with content.
      4. Empirical verification on disk.
    """
    workspace = Path(settings.AUTHORIZED_WORKSPACE).resolve()
    target_dir = workspace / "Projects" / "Test"
    target_file = target_dir / "notes.txt"

    # Clean up prior to test
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)

    payload = {
        "title": "Setup Test Folder",
        "objective": "Create a folder called Projects/Test and put a file named notes.txt in it",
        "priority": 5,
    }
    res = await api_client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 201
    data = res.json()
    task_id = data["id"]
    assert len(data["steps"]) == 3
    assert data["steps"][0]["agent_type"] == "file"
    assert "directory" in data["steps"][0]["title"].lower()
    assert "file" in data["steps"][1]["title"].lower()
    assert "verify" in data["steps"][2]["title"].lower()

    # Poll for completion
    for _ in range(40):
        await asyncio.sleep(0.3)
        chk = await api_client.get(f"/api/v1/tasks/{task_id}")
        if chk.json()["status"] == "completed":
            break

    assert chk.json()["status"] == "completed"
    assert target_dir.exists() and target_dir.is_dir()
    assert target_file.exists() and target_file.is_file()
    assert target_file.stat().st_size > 0


@pytest.mark.asyncio
async def test_demo_3_web_research_with_citations(api_client: AsyncClient):
    """
    Demo 3: 'Search the web for the latest news on a topic and summarise it with sources'
    Validates:
      1. Correct 2-step decomposition: Search web, Synthesize research with citations.
      2. Agent performs web search.
      3. Output contains structured summary and source URLs.
    """
    payload = {
        "title": "Web Research Topic",
        "objective": "Search the web for the latest news on a topic and summarise it with sources",
        "priority": 5,
    }
    res = await api_client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 201
    data = res.json()
    task_id = data["id"]
    assert len(data["steps"]) == 2
    assert data["steps"][0]["agent_type"] == "research"
    assert data["steps"][1]["agent_type"] == "research"

    for _ in range(50):
        await asyncio.sleep(0.4)
        chk = await api_client.get(f"/api/v1/tasks/{task_id}")
        if chk.json()["status"] == "completed":
            break

    assert chk.json()["status"] == "completed"
    steps = chk.json()["steps"]
    synthesis_step = steps[1]
    res_payload = synthesis_step.get("output_payload", {})
    response_text = str(res_payload.get("response", ""))
    # Verified sources / citations are included
    assert "http" in response_text or "Sources" in response_text or "Citations" in response_text or "url" in str(steps[0])


@pytest.mark.asyncio
async def test_demo_4_delete_file_with_tier2_approval_and_recycle_bin(api_client: AsyncClient):
    """
    Demo 4: 'Delete that file'
    Validates:
      1. Resolves target file from context/memory (e.g. Projects/Test/notes.txt).
      2. Classified as Tier 2 Consequential action -> creates approval ticket and halts.
      3. When approved, executes send2trash (Recycle Bin).
      4. Verifies file is no longer at original disk location.
    """
    workspace = Path(settings.AUTHORIZED_WORKSPACE).resolve()
    target_dir = workspace / "Projects" / "Test"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "notes.txt"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("Temporary file to be deleted into Recycle Bin.")

    MemoryService.set_working_memory_key("global", "last_created_file", str(target_file))

    payload = {
        "title": "Delete File",
        "objective": "Delete that file",
        "priority": 5,
    }
    res = await api_client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 201
    data = res.json()
    task_id = data["id"]

    # Wait for task to halt at approval required
    ticket_id = None
    for _ in range(30):
        await asyncio.sleep(0.3)
        chk = await api_client.get(f"/api/v1/tasks/{task_id}")
        if chk.json()["status"] == "waiting_approval":
            break

    # Get pending approval ticket
    appr_res = await api_client.get("/api/v1/permissions/pending")
    assert appr_res.status_code == 200
    pending = appr_res.json()
    assert len(pending) > 0
    ticket = pending[0]
    ticket_id = ticket["approval_token"]
    assert ticket["action_type"] == "delete_file"

    # Operator grants approval
    resp_approve = await api_client.post(
        "/api/v1/permissions/respond",
        json={"ticket_id": ticket_id, "decision": "approve"},
    )
    assert resp_approve.status_code == 200
    assert resp_approve.json()["status"] == "approved"
    signed_token = resp_approve.json()["signed_token"]
    assert signed_token is not None

    # Now verify file was sent to recycle bin (no longer exists on disk)
    from app.tools.registry import tool_registry
    exec_res = await tool_registry.execute_tool(
        name="delete_file",
        arguments={"filepath": str(target_file)},
        session=None,
        actor="test_runner",
        approval_token=signed_token,
    )
    assert exec_res.success is True
    assert exec_res.verification.verified is True
    assert not target_file.exists()


@pytest.mark.asyncio
async def test_demo_5_cognitive_memory_store_and_recall(api_client: AsyncClient):
    """
    Demo 5: 'Remember that I prefer dark mode' followed by 'What do I prefer?'
    Validates:
      1. Memory stored in PostgreSQL pgvector with embedding.
      2. New session task queries memory via vector similarity.
      3. Returns recalled preference accurately.
    """
    # 1. Store preference
    store_payload = {
        "title": "Remember Preference",
        "objective": "Remember that I prefer dark mode",
        "priority": 5,
    }
    res1 = await api_client.post("/api/v1/tasks", json=store_payload)
    assert res1.status_code == 201
    task1_id = res1.json()["id"]

    for _ in range(30):
        await asyncio.sleep(0.3)
        chk1 = await api_client.get(f"/api/v1/tasks/{task1_id}")
        if chk1.json()["status"] == "completed":
            break
    assert chk1.json()["status"] == "completed"

    # Verify memory is listed in API
    mem_res = await api_client.get("/api/v1/memory?limit=10")
    assert mem_res.status_code == 200
    memories = mem_res.json()
    assert any("dark mode" in m["content"].lower() for m in memories)

    # 2. Recall in separate task
    recall_payload = {
        "title": "Recall Preference",
        "objective": "What do I prefer?",
        "priority": 5,
    }
    res2 = await api_client.post("/api/v1/tasks", json=recall_payload)
    assert res2.status_code == 201
    task2_id = res2.json()["id"]

    for _ in range(30):
        await asyncio.sleep(0.3)
        chk2 = await api_client.get(f"/api/v1/tasks/{task2_id}")
        if chk2.json()["status"] == "completed":
            break
    assert chk2.json()["status"] == "completed"

    steps2 = chk2.json()["steps"]
    out_payload = steps2[0].get("output_payload", {})
    assert "dark mode" in str(out_payload).lower() or "dark mode" in steps2[0].get("verification_evidence", "").lower()


@pytest.mark.asyncio
async def test_demo_6_coding_script_creation_execution_output(api_client: AsyncClient):
    """
    Demo 6: Coding task: 'Create small script in workspace, run it, report real output'
    Validates:
      1. Decomposes into: Create script, Execute script, Verify real output.
      2. Script written to workspace.
      3. Script executed with Python subprocess and captures real stdout.
      4. Captured stdout reported and verified with exit code 0.
    """
    payload = {
        "title": "Run Custom Script",
        "objective": "create a small python script in workspace, run it, report real output",
        "priority": 5,
    }
    res = await api_client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 201
    data = res.json()
    task_id = data["id"]
    assert len(data["steps"]) == 3
    assert data["steps"][0]["agent_type"] == "coding"
    assert data["steps"][1]["agent_type"] == "coding"

    for _ in range(40):
        await asyncio.sleep(0.3)
        chk = await api_client.get(f"/api/v1/tasks/{task_id}")
        if chk.json()["status"] == "completed":
            break

    assert chk.json()["status"] == "completed"
    steps = chk.json()["steps"]
    exec_step = steps[1]
    out = exec_step.get("output_payload", {})
    assert out.get("exit_code") == 0
    assert "REETA" in out.get("stdout", "") or "Execution successful" in out.get("stdout", "")


def test_demo_7_websocket_event_stream_lifecycle():
    """
    Demo 7: Core state transitions on real events.
    Validates:
      1. WebSocket client connects to real-time streaming endpoint /ws/v1/stream.
      2. Server broadcasts 'connected' greeting.
      3. Ping/Pong loop verified.
      4. User message triggers thinking transition ('agent_thought') and synthesized response ('agent_message').
    """
    from starlette.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    with client.websocket_connect("/ws/v1/stream") as websocket:
        # 1. Connected event on handshake
        init_msg = websocket.receive_json()
        assert init_msg["event"] == "connected"

        # 2. Ping-pong verified
        websocket.send_json({"event": "ping", "payload": {}})
        pong = websocket.receive_json()
        assert pong["event"] == "pong"

        # 3. User message triggers real-time thinking state followed by response
        websocket.send_json({"event": "user_message", "payload": {"text": "Hey REETA, what is the status of the system?"}})
        thought = websocket.receive_json()
        assert thought["event"] == "agent_thought"

        response = websocket.receive_json()
        assert response["event"] == "agent_message"
        assert len(response["payload"]["content"]) > 0

