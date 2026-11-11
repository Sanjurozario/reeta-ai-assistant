import asyncio
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path
import pytest
import pytest_asyncio
import psutil

from app.config import settings
from app.database.models import User, Task, TaskStatus
from app.core.tasks import TaskManager
from app.tools.registry import tool_registry
from app.memory.store import MemoryService
from app.voice.service import VoiceService


# ============================================================================
# TEST 1: PDF Report Creation via Research/File Agent
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_1_pdf_report_creation():
    """TEST 1: Generate styled PDF report and verify disk bytes and %PDF- header."""
    pdf_tool = tool_registry.get_tool("create_pdf_report")
    assert pdf_tool is not None

    test_filename = f"reeta_test_report_{int(time.time())}.pdf"
    sections = [
        {"heading": "Executive Summary", "body": "REETA autonomous personal operating system testing suite."},
        {"heading": "System Architecture", "body": "Autonomous zero-trust execution with empirical verification receipts."},
    ]

    result = await pdf_tool.execute(
        title="REETA Verification Report 2026",
        sections=sections,
        filename=test_filename,
        author="REETA Integration Suite",
    )

    pdf_path = Path(result["pdf_path"])
    try:
        # 1. Empirically verify file exists on disk
        assert pdf_path.exists(), f"PDF report not found at {pdf_path}"
        # 2. Empirically verify file size > 0
        file_size = pdf_path.stat().st_size
        assert file_size > 1000, f"PDF file size suspiciously small: {file_size} bytes"
        # 3. Empirically verify binary magic bytes '%PDF-'
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-", f"Invalid PDF magic header: {header}"

        # 4. Verify tool verification logic
        verif = await pdf_tool.verify_outcome(result)
        assert verif.verified is True
        assert "Empirically validated PDF" in verif.evidence
    finally:
        if pdf_path.exists():
            pdf_path.unlink()


# ============================================================================
# TEST 2: Open Windows Application & Process PID Verification
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_2_open_windows_application():
    """TEST 2: Launch Windows application (notepad.exe) and verify PID in OS tasklist."""
    app_tool = tool_registry.get_tool("open_application")
    assert app_tool is not None

    result = await app_tool.execute(app_name_or_path="notepad.exe", arguments="")
    pid = result.get("pid")
    assert pid is not None and pid > 0, f"Expected valid PID, got {pid}"

    try:
        # Verify process PID is active in Windows OS
        assert psutil.pid_exists(pid), f"PID {pid} does not exist in Windows process table"

        # Check empirical verification
        verif = await app_tool.verify_outcome(result, app_name_or_path="notepad.exe")
        assert verif.verified is True
    finally:
        # Terminate test process cleanly
        try:
            if psutil.pid_exists(pid):
                p = psutil.Process(pid)
                p.terminate()
        except Exception:
            pass


# ============================================================================
# TEST 3: Organize Project Folder into Categorized Subfolders
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_3_organize_project_folder():
    """TEST 3: Batch organize mixed extension files into categorized subfolders."""
    organize_tool = tool_registry.get_tool("organize_folder")
    assert organize_tool is not None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create unorganized test files
        (tmp_path / "notes.txt").write_text("Meeting notes", encoding="utf-8")
        (tmp_path / "spec.pdf").write_text("%PDF-mock", encoding="utf-8")
        (tmp_path / "script.py").write_text("print('hello')", encoding="utf-8")
        (tmp_path / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        result = await organize_tool.execute(directory=str(tmp_path))
        assert result["total_organized"] == 4

        # Empirically verify destination files exist in categorized subfolders
        assert (tmp_path / "Documents" / "notes.txt").exists()
        assert (tmp_path / "Documents" / "spec.pdf").exists()
        assert (tmp_path / "Code" / "script.py").exists()
        assert (tmp_path / "Images" / "icon.png").exists()

        # Verify tool verification receipt
        verif = await organize_tool.verify_outcome(result)
        assert verif.verified is True
        assert "moved 4 files" in verif.evidence


# ============================================================================
# TEST 4: Code Search, Patch, and Automated Test Execution
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_4_code_search_patch_and_test():
    """TEST 4: Search buggy code, patch source with fix, and execute pytest to verify."""
    search_tool = tool_registry.get_tool("code_search")
    patch_tool = tool_registry.get_tool("code_patch")
    test_tool = tool_registry.get_tool("run_tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        calc_path = tmp_path / "calculator.py"
        test_calc_path = tmp_path / "test_calculator.py"

        # 1. Write buggy source code
        calc_path.write_text(
            "def add(a, b):\n    return a - b  # Bug: subtraction instead of addition\n",
            encoding="utf-8",
        )
        test_calc_path.write_text(
            "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )

        # 2. Search for the bug
        search_res = await search_tool.execute(pattern="def add", directory=str(tmp_path))
        assert search_res["total_matches"] >= 1
        assert "calculator.py" in search_res["matches"][0]["file"]

        # 3. Patch the bug
        patch_res = await patch_tool.execute(
            filepath=str(calc_path),
            target_block="return a - b",
            replacement_block="return a + b",
        )
        assert patch_res["status"] == "patched"

        # Verify patch on disk
        patched_content = calc_path.read_text(encoding="utf-8")
        assert "return a + b" in patched_content

        # 4. Execute test suite and empirically verify test pass
        test_res = await test_tool.execute(
            test_command=f"pytest {test_calc_path.name} -q",
            working_directory=str(tmp_path),
        )
        assert test_res["passed"] is True
        assert test_res["exit_code"] == 0

        verif = await test_tool.verify_outcome(test_res)
        assert verif.verified is True
        assert "exit code 0" in verif.evidence


# ============================================================================
# TEST 5: Browser Navigation and DOM Table Extraction
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_5_browser_navigation_and_extraction():
    """TEST 5: Scrape structured tabular information using Playwright Chromium."""
    extract_tool = tool_registry.get_tool("browser_extract_tables")
    assert extract_tool is not None

    with tempfile.TemporaryDirectory() as tmpdir:
        html_file = Path(tmpdir) / "sample_matrix.html"
        html_content = """<!DOCTYPE html>
<html>
<head><title>System Tiers</title></head>
<body>
    <h1>Security Classification</h1>
    <table>
        <tr><th>Tier</th><th>Name</th><th>Approval</th></tr>
        <tr><td>Tier 1</td><td>Autonomous</td><td>None</td></tr>
        <tr><td>Tier 2</td><td>Consequential</td><td>Required</td></tr>
    </table>
</body>
</html>"""
        html_file.write_text(html_content, encoding="utf-8")
        file_url = html_file.resolve().as_uri()

        result = await extract_tool.execute(url=file_url)
        assert result["tables_extracted"] >= 1
        table_rows = result["data"][0]
        assert len(table_rows) >= 2
        assert "Tier 1" in table_rows[1][0]
        assert "Autonomous" in table_rows[1][1]

        verif = await extract_tool.verify_outcome(result)
        assert verif.verified is True


# ============================================================================
# TEST 6: Voice Endpoint, Wake-Word Detection, and Modes
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_6_voice_endpoint_and_modes(api_client):
    """TEST 6: Voice transcription with wake-word detection, speech synthesis, and mode switching."""
    # 1. Transcribe with wake-word
    res = await api_client.post(
        "/api/v1/voice/transcribe",
        json={"text_mock": "Hey Reeta, generate executive summary"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["wake_word_detected"] is True
    assert data["command_text"] == "generate executive summary"

    # 2. Switch conversation mode
    mode_res = await api_client.post("/api/v1/voice/mode", json={"mode": "voice"})
    assert mode_res.status_code == 200
    assert mode_res.json()["conversation_mode"] == "voice"

    # 3. Speech synthesis
    synth_res = await api_client.post(
        "/api/v1/voice/synthesize",
        json={"text": "Task completed successfully.", "voice": "en_US-lessac-medium"},
    )
    assert synth_res.status_code == 200
    assert synth_res.json()["format"] == "wav"

    # 4. Speech interruption
    interrupt_res = await api_client.post("/api/v1/voice/interrupt")
    assert interrupt_res.status_code == 200
    assert interrupt_res.json()["status"] == "interrupted"

    # Restore default mode
    await api_client.post("/api/v1/voice/mode", json={"mode": "text"})


# ============================================================================
# TEST 7: Memory Storage and Semantic Vector Retrieval via pgvector
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_7_memory_pgvector_semantic_retrieval(db_session):
    """TEST 7: Store user preference and perform cosine distance similarity search via pgvector."""
    # Ensure user exists with unique credentials
    user_id = uuid.uuid4()
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        id=user_id,
        username=f"vector_tester_{unique_suffix}",
        email=f"tester_{unique_suffix}@reeta.ai",
        password_hash="test_secret_hash",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 1. Store preference memory
    pref_text = "The operator prefers obsidian dark interfaces (#0B0E14) and concise terminal summaries."
    mem = await MemoryService.store_memory(
        session=db_session,
        user_id=user_id,
        content=pref_text,
        memory_type="preference",
        category="ui_preferences",
    )
    assert mem.id is not None

    # 2. Query memory via semantic vector search
    results = await MemoryService.search_memories(
        session=db_session,
        user_id=user_id,
        query="The operator prefers obsidian dark interfaces",
        top_k=3,
        memory_type="preference",
    )
    assert len(results) > 0
    top_result = results[0]
    assert "obsidian dark" in top_result["content"]
    assert top_result["similarity_score"] > 0.4


# ============================================================================
# TEST 8: Zero-Trust Tier 2 Consequential Action Approval Trigger
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_8_tier2_consequential_action_approval(db_session):
    """TEST 8: Consequential action without approval halts execution and issues ticket."""
    result = await tool_registry.execute_tool(
        name="powershell_execute",
        arguments={"command": "Get-Date"},
        session=db_session,
        approval_token=None,
    )

    # Must require approval
    assert result.requires_approval is True
    assert result.success is False
    assert result.ticket_id is not None


# ============================================================================
# TEST 9: Cancel Active Task & Verify Execution Halts
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_9_cancel_active_task(db_session):
    """TEST 9: Cancel active task and verify cancellation event is signaled."""
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"cancel_tester_{unique_suffix}",
        email=f"cancel_{unique_suffix}@reeta.ai",
        password_hash="cancel_secret_hash",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    task = await TaskManager.create_task(
        session=db_session,
        user_id=user.id,
        title="Long Running Job",
        objective="Execute long multi-step background processing",
    )

    # Register worker with cancel event
    cancel_event = asyncio.Event()

    async def dummy_worker():
        while not cancel_event.is_set():
            await asyncio.sleep(0.1)

    worker_task = asyncio.create_task(dummy_worker())
    TaskManager.register_worker(str(task.id), worker_task, cancel_event)

    # Cancel task
    cancelled = await TaskManager.cancel_task(db_session, task.id)
    assert cancelled is True
    assert cancel_event.is_set() is True

    # Check database status
    task_db = await TaskManager.get_task(db_session, task.id)
    assert task_db is not None
    assert task_db.status == TaskStatus.CANCELLED.value

    # Await worker termination and verify task cancelled or finished
    try:
        await asyncio.wait_for(worker_task, timeout=2.0)
    except asyncio.CancelledError:
        pass
    assert worker_task.done()


# ============================================================================
# TEST 10: Task Failure Accurately Reported Without False Success
# ============================================================================
@pytest.mark.asyncio
async def test_workflow_10_task_failure_reported_accurately(db_session):
    """TEST 10: Verify tool failure is reported with verified=False and accurate error details."""
    result = await tool_registry.execute_tool(
        name="read_file",
        arguments={"filepath": "C:/invalid_non_existent_path_xyz_9999.txt"},
        session=db_session,
    )

    assert result.success is False
    assert result.verification.verified is False
    assert "not found" in result.error.lower() or "failed" in result.verification.evidence.lower()
