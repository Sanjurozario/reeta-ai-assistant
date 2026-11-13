import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import get_agent, AgentStepResult
from app.core.gateway import model_gateway, GatewayMessage
from app.core.tasks import TaskManager, broadcaster
from app.database.models import Task, TaskStep, TaskStatus
from app.database.session import async_session_factory

logger = logging.getLogger("reeta.orchestrator")


class OrchestratorState(TypedDict):
    task_id: str
    user_id: str
    objective: str
    steps: List[Dict[str, Any]]
    current_step_idx: int
    retry_count: int
    artifacts: List[Dict[str, Any]]
    status: str
    is_cancelled: bool
    requires_approval: bool
    ticket_id: Optional[str]
    error: Optional[str]
    context: Dict[str, Any]


class CentralOrchestrator:
    """Master LangGraph state machine coordinating autonomous task planning and execution."""

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(OrchestratorState)

        builder.add_node("plan_task", self._node_plan_task)
        builder.add_node("execute_step", self._node_execute_step)
        builder.add_node("verify_step", self._node_verify_step)
        builder.add_node("finalize_task", self._node_finalize_task)

        builder.set_entry_point("plan_task")

        builder.add_edge("plan_task", "execute_step")

        builder.add_conditional_edges(
            "execute_step",
            self._route_after_execute,
            {
                "verify": "verify_step",
                "halt_approval": END,
                "abort_cancelled": "finalize_task",
            },
        )

        builder.add_conditional_edges(
            "verify_step",
            self._route_after_step,
            {
                "continue": "execute_step",
                "finalize": "finalize_task",
                "halt_approval": END,
                "abort_cancelled": "finalize_task",
                "abort_failed": "finalize_task",
            },
        )

        builder.add_edge("finalize_task", END)
        return builder.compile()

    # ========================================================================
    # Static Planning Decomposition
    # ========================================================================

    @classmethod
    def plan_steps_for_objective(cls, objective: str, title: str = "") -> List[Dict[str, Any]]:
        """Determines ordered steps and assigned worker agents for a given objective."""
        import re
        raw = f"{title} {objective}".strip()
        # Clean wake word prefix ("hey reeta", "hello reeta", "reeta")
        cleaned = re.sub(r'^(?:hey|hi|hello|ok|okay|yo)?\s*(?:reeta|rita|reta|rhea|jarvis)[\s,.:!?-]*', '', objective, flags=re.I).strip()
        if not cleaned:
            cleaned = objective.strip()
        text = f"{title} {cleaned}".lower()

        # 0. Wake word / Activation Alone
        if not cleaned or cleaned.lower() in {"hey reeta", "reeta", "wake up", "are you there", "listen"}:
            return [
                {"step_number": 1, "title": "Acknowledge activation", "agent_type": "assistant", "input_payload": {"greeting": "Yes, I'm listening. How can I help?"}}
            ]

        # 1. Greetings
        if re.search(r'^(?:hello|hi|hey|good\s+(?:morning|afternoon|evening)|greetings|howdy)(?:\s+reeta)?[\s.!?]*$', cleaned, re.I):
            return [
                {"step_number": 1, "title": "Respond to greeting", "agent_type": "assistant"}
            ]

        # 2. Deletion / Recycle Bin (DEMO 4)
        if "delete" in text or "remove file" in text or "trash" in text:
            return [
                {"step_number": 1, "title": "Delete file and transfer to Windows Recycle Bin", "agent_type": "file"},
                {"step_number": 2, "title": "Empirically verify file is removed from disk location", "agent_type": "file"},
            ]

        # 3. Directory Creation + File Placement (DEMO 2)
        if ("create a folder" in text or "create folder" in text or "folder called" in text or "directory called" in text or "projects/test" in text) and ("file" in text or "notes" in text):
            return [
                {"step_number": 1, "title": "Create directory structure in authorized workspace", "agent_type": "file"},
                {"step_number": 2, "title": "Create and write file inside folder", "agent_type": "file"},
                {"step_number": 3, "title": "Empirically verify directory and file exist on disk", "agent_type": "file"},
            ]

        # 4. Windows Notepad Launch & Keystroke Input (DEMO 1)
        if "notepad" in text and ("write" in text or "type" in text or "note " in text or "say" in text):
            return [
                {"step_number": 1, "title": "Launch Windows Notepad application", "agent_type": "computer"},
                {"step_number": 2, "title": "Type greeting note into active Notepad window", "agent_type": "computer"},
                {"step_number": 3, "title": "Inspect open windows and verify active UI", "agent_type": "computer"},
            ]

        # 5. Generic Windows Desktop Applications (e.g. "open Notepad", "launch calc")
        if any(k in text for k in ["notepad", "calc", "calculator", "open app", "launch", "close window"]):
            return [
                {"step_number": 1, "title": f"Launch target application for '{cleaned[:30]}'", "agent_type": "computer"},
                {"step_number": 2, "title": "Inspect open windows and verify active UI", "agent_type": "computer"},
            ]

        # 6. Coding Task: Script Creation, Execution, & Output Capture (DEMO 6)
        if ("python script" in text or "create a script" in text or "create script" in text or "run script" in text or "small script" in text or ("script" in text and "output" in text)):
            return [
                {"step_number": 1, "title": "Create Python script in authorized workspace", "agent_type": "coding"},
                {"step_number": 2, "title": "Execute script and capture real stdout output", "agent_type": "coding"},
                {"step_number": 3, "title": "Empirically verify script execution and output", "agent_type": "coding"},
            ]

        # 7. Code Search & Testing
        if "bug" in text or "pytest" in text or ("test" in text and ("suite" in text or "unit" in text or "run test" in text or "test suite" in text)):
            return [
                {"step_number": 1, "title": "Search codebase for target symbol or bug", "agent_type": "coding"},
                {"step_number": 2, "title": "Execute test suite to confirm baseline", "agent_type": "coding"},
            ]

        # 8. File Operations: Desktop file or specific file creation
        if "desktop" in text and ("file" in text or "create" in text or "txt" in text or "note" in text):
            return [
                {"step_number": 1, "title": f"Create and write file on Desktop for '{cleaned[:30]}'", "agent_type": "file"},
                {"step_number": 2, "title": "Empirically verify file existence and contents on disk", "agent_type": "file"},
            ]

        # 9. Generic File Creation (Write, Temp, .txt)
        if ("file" in text or "write" in text or "create text" in text or "temp" in text or ".txt" in text) and not ("what is" in text or "how" in text):
            return [
                {"step_number": 1, "title": f"Create and write file content for '{cleaned[:30]}'", "agent_type": "file"},
                {"step_number": 2, "title": "Empirically verify file existence and contents on disk", "agent_type": "file"},
            ]

        # 10. Folder Organization
        if "organize" in text or "clean" in text:
            return [
                {"step_number": 1, "title": "Scan directory and discover files", "agent_type": "file"},
                {"step_number": 2, "title": "Batch categorize and organize into folders", "agent_type": "file"},
            ]

        # 11. PDF Report Generation
        if "pdf" in text or "report" in text:
            return [
                {"step_number": 1, "title": f"Gather research data on '{cleaned[:30]}'", "agent_type": "research"},
                {"step_number": 2, "title": "Synthesize report and generate PDF document", "agent_type": "file"},
            ]

        # 12. Actual Web Research Requests
        if ("research" in text or "search web" in text or "query web" in text or "find news" in text):
            return [
                {"step_number": 1, "title": "Search web for latest information and gather citations", "agent_type": "research"},
                {"step_number": 2, "title": "Synthesize concise research summary with citations", "agent_type": "research"},
            ]

        # 13. Browser Automation
        if "browse" in text or "http" in text or "website" in text or "extract" in text or "wikipedia" in text:
            return [
                {"step_number": 1, "title": f"Navigate to website and capture page context", "agent_type": "browser"},
                {"step_number": 2, "title": "Extract structured information from page", "agent_type": "browser"},
            ]

        # 14. Cognitive Semantic Memory (DEMO 5)
        if "prefer" in text or "remember" in text or "preference" in text or "memory" in text:
            if "what" in text or "tell me" in text or "recall" in text or "show" in text:
                return [
                    {"step_number": 1, "title": "Retrieve semantic preference from pgvector memory", "agent_type": "memory"},
                    {"step_number": 2, "title": "Synthesize response from retrieved memory", "agent_type": "memory"},
                ]
            else:
                return [
                    {"step_number": 1, "title": "Store user preference in cognitive pgvector memory", "agent_type": "memory"},
                    {"step_number": 2, "title": "Confirm memory storage and update status", "agent_type": "memory"},
                ]

        # 15. Reminders & Scheduling
        if "remind" in text or "schedule" in text:
            return [
                {"step_number": 1, "title": f"Create scheduled reminder for '{cleaned[:30]}'", "agent_type": "productivity"},
                {"step_number": 2, "title": "Confirm reminder schedule and status", "agent_type": "productivity"},
            ]

        # 16. Capabilities / What can you do
        if "what can you do" in text or "your capabilities" in text or "who are you" in text or "help" in text:
            return [
                {"step_number": 1, "title": "Explain capabilities and assist user", "agent_type": "assistant"},
                {"step_number": 2, "title": "Present interactive command suggestions", "agent_type": "assistant"},
            ]

        # 17. Math / Factual Questions / General Conversation
        if any(k in text for k in ["multiplied by", "times", "divided by", "plus", "minus", "calculate", "what is", "who is", "why is", "how do", "how to", "tell me about"]):
            return [
                {"step_number": 1, "title": f"Process inquiry: '{cleaned[:40]}'", "agent_type": "assistant"},
                {"step_number": 2, "title": "Synthesize response and verify completion", "agent_type": "assistant"},
            ]

        # 18. Fallback: Direct Assistant Response (NEVER raw ResearchAgent decomposition!)
        return [
            {"step_number": 1, "title": f"Process inquiry: '{cleaned[:40]}'", "agent_type": "assistant"},
            {"step_number": 2, "title": "Synthesize response and verify completion", "agent_type": "assistant"},
        ]

    # ========================================================================
    # Graph Nodes
    # ========================================================================

    async def _node_plan_task(self, state: OrchestratorState) -> Dict[str, Any]:
        """Decomposes user objective into an ordered step sequence with assigned agents."""
        objective = state["objective"]
        task_id = state["task_id"]
        logger.info(f"Orchestrator planning task {task_id}: '{objective}'")

        steps: List[Dict[str, Any]] = []

        # Record or synchronize steps in DB and notify UI
        async with async_session_factory() as session:
            existing = await TaskManager.get_task(session, uuid.UUID(task_id))
            if existing and existing.steps and len(existing.steps) > 0:
                is_placeholder = any(s.title == "Analyze and decompose objective" for s in existing.steps)
                if is_placeholder:
                    # Replace placeholder with domain-specific decomposition
                    real_steps = self.plan_steps_for_objective(objective, existing.title)
                    for old_s in list(existing.steps):
                        await session.delete(old_s)
                    await session.flush()
                    created = await TaskManager.create_steps(session, uuid.UUID(task_id), real_steps)
                    steps = [
                        {
                            "id": str(s.id),
                            "step_number": s.step_number,
                            "title": s.title,
                            "agent_type": s.agent_type,
                            "input_payload": s.input_payload or {},
                        }
                        for s in created
                    ]
                else:
                    steps = [
                        {
                            "id": str(s.id),
                            "step_number": s.step_number,
                            "title": s.title,
                            "agent_type": s.agent_type,
                            "input_payload": s.input_payload or {},
                        }
                        for s in sorted(existing.steps, key=lambda x: x.step_number)
                    ]
            else:
                real_steps = self.plan_steps_for_objective(objective)
                created = await TaskManager.create_steps(session, uuid.UUID(task_id), real_steps)
                steps = [
                    {
                        "id": str(s.id),
                        "step_number": s.step_number,
                        "title": s.title,
                        "agent_type": s.agent_type,
                        "input_payload": s.input_payload or {},
                    }
                    for s in created
                ]
            await TaskManager.update_task_status(session, uuid.UUID(task_id), TaskStatus.RUNNING)

        return {
            "steps": steps,
            "current_step_idx": 0,
            "retry_count": 0,
            "status": "running",
        }

    async def _node_execute_step(self, state: OrchestratorState) -> Dict[str, Any]:
        """Dispatches current step to the designated specialized agent."""
        idx = state["current_step_idx"]
        steps = state["steps"]
        task_id = state["task_id"]

        # Check cancellation
        if state.get("is_cancelled"):
            return {"status": "cancelled"}

        current_step = steps[idx]
        agent_type = current_step.get("agent_type", "research")
        agent = get_agent(agent_type)
        step_id = current_step.get("id")

        if step_id:
            try:
                async with async_session_factory() as session:
                    await TaskManager.update_step_status(session, uuid.UUID(step_id), TaskStatus.RUNNING)
            except Exception as e:
                logger.warning(f"Could not mark step {step_id} running in DB: {e}")

        await broadcaster.broadcast(
            event="step_started",
            task_id=task_id,
            payload={
                "step_number": current_step["step_number"],
                "title": current_step["title"],
                "agent": agent.name,
            },
        )

        async with async_session_factory() as session:
            step_result: AgentStepResult = await agent.run_step(
                step_title=current_step["title"],
                task_objective=state["objective"],
                context=state.get("context", {}),
                session=session,
                task_id=uuid.UUID(task_id),
                user_id=uuid.UUID(state["user_id"]),
            )
            await session.commit()

        # Handle Tier 2 Approval interruption
        if step_result.requires_approval:
            logger.info(f"Task {task_id} halted: Ticket {step_result.ticket_id} requires approval.")
            try:
                async with async_session_factory() as session:
                    await TaskManager.update_task_status(session, uuid.UUID(task_id), TaskStatus.WAITING_APPROVAL)
            except Exception as e:
                logger.warning(f"Could not mark task {task_id} waiting_approval in DB: {e}")

            await broadcaster.broadcast(
                event="approval_required",
                task_id=task_id,
                payload={
                    "ticket_id": step_result.ticket_id,
                    "description": step_result.error,
                    "step_number": current_step["step_number"],
                },
            )
            return {
                "requires_approval": True,
                "ticket_id": step_result.ticket_id,
                "status": "waiting_approval",
            }

        # Store artifacts if produced
        artifacts = list(state.get("artifacts", []))
        context = dict(state.get("context", {}))
        if isinstance(step_result.output, dict):
            if "pdf_path" in step_result.output:
                artifacts.append({"type": "pdf", "path": step_result.output["pdf_path"]})
            if "screenshot_path" in step_result.output:
                artifacts.append({"type": "screenshot", "path": step_result.output["screenshot_path"]})
            if "filepath" in step_result.output:
                context["last_created_file"] = step_result.output["filepath"]
                context["filepath"] = step_result.output["filepath"]
                from app.memory.store import MemoryService
                MemoryService.set_working_memory_key("global", "last_created_file", step_result.output["filepath"])
            if "directory_path" in step_result.output:
                context["last_created_directory"] = step_result.output["directory_path"]
                from app.memory.store import MemoryService
                MemoryService.set_working_memory_key("global", "last_created_directory", step_result.output["directory_path"])
            if "script" in step_result.output:
                context["last_created_script"] = step_result.output["script"]
                from app.memory.store import MemoryService
                MemoryService.set_working_memory_key("global", "last_created_script", step_result.output["script"])

        current_step["result"] = step_result.output
        current_step["verified"] = step_result.verified
        current_step["evidence"] = step_result.verification_evidence

        return {
            "steps": steps,
            "artifacts": artifacts,
            "context": context,
            "status": "step_executed",
        }

    async def _node_verify_step(self, state: OrchestratorState) -> Dict[str, Any]:
        """Evaluates empirical evidence of outcome before advancing."""
        idx = state["current_step_idx"]
        current_step = state["steps"][idx]
        task_id = state["task_id"]
        step_id = current_step.get("id")

        is_verified = current_step.get("verified", False)
        evidence = current_step.get("evidence", "No evidence recorded.")

        logger.info(f"Task {task_id} Step {idx + 1} verification: Verified={is_verified} | Evidence: {evidence}")

        await broadcaster.broadcast(
            event="step_verified",
            task_id=task_id,
            payload={
                "step_number": current_step["step_number"],
                "passed": is_verified,
                "evidence": evidence,
            },
        )

        if is_verified:
            if step_id:
                try:
                    async with async_session_factory() as session:
                        await TaskManager.update_step_status(
                            session,
                            uuid.UUID(step_id),
                            TaskStatus.COMPLETED,
                            output_payload=current_step.get("result", {}),
                        )
                except Exception as e:
                    logger.warning(f"Could not update step {step_id} completed in DB: {e}")

            return {
                "current_step_idx": idx + 1,
                "retry_count": 0,
                "status": "step_verified",
            }
        else:
            retries = state.get("retry_count", 0) + 1
            if retries > 1:
                # Max retries exceeded: abort execution cleanly
                logger.error(f"Task {task_id} Step {idx + 1} failed verification after {retries} attempts.")
                if step_id:
                    try:
                        async with async_session_factory() as session:
                            await TaskManager.update_step_status(
                                session,
                                uuid.UUID(step_id),
                                TaskStatus.FAILED,
                                error_log=f"Verification failed: {evidence}",
                            )
                    except Exception as e:
                        logger.warning(f"Could not update step {step_id} failed in DB: {e}")

                return {
                    "retry_count": retries,
                    "status": "failed",
                    "error": f"Step {idx + 1} ('{current_step['title']}') failed verification: {evidence}",
                }

            return {
                "current_step_idx": idx,
                "retry_count": retries,
                "status": "verification_failed",
            }

    async def _node_finalize_task(self, state: OrchestratorState) -> Dict[str, Any]:
        """Updates final task status in database and broadcasts completion event."""
        task_id = state["task_id"]
        is_cancelled = state.get("is_cancelled", False)
        has_error = bool(state.get("error"))
        all_done = state.get("current_step_idx", 0) >= len(state.get("steps", []))

        if is_cancelled:
            final_status = TaskStatus.CANCELLED
        elif all_done and not has_error:
            final_status = TaskStatus.COMPLETED
        else:
            final_status = TaskStatus.FAILED

        error_detail = {"error": state.get("error")} if state.get("error") else None

        # Synthesize clean, human-readable final response
        final_response = ""
        for s in state.get("steps", []):
            res = s.get("result", {})
            if isinstance(res, dict):
                if res.get("response"):
                    final_response = res["response"]
                elif res.get("answer"):
                    final_response = res["answer"]

        if not final_response and not has_error:
            for s in reversed(state.get("steps", [])):
                res = s.get("result", {})
                if isinstance(res, dict):
                    if res.get("app") and res.get("status") == "launched":
                        app_name = res.get("app", "Application").replace(".exe", "").capitalize()
                        final_response = f"{app_name} has been launched and verified active on your desktop."
                        break
                    elif res.get("filepath") and res.get("status") == "written":
                        fname = Path(res["filepath"]).name
                        final_response = f"Successfully created '{fname}' at {res['filepath']}."
                        break
                    elif res.get("tables_extracted"):
                        final_response = f"Extracted {res['tables_extracted']} tables from webpage."
                        break
                    elif res.get("stdout"):
                        final_response = f"Script execution output:\n{res['stdout']}"
                        break
            if not final_response:
                final_response = "Task execution completed and verified."

        async with async_session_factory() as session:
            await TaskManager.update_task_status(
                session=session,
                task_id=uuid.UUID(task_id),
                status=final_status,
                result={
                    "final_response": final_response,
                    "artifacts": state.get("artifacts", []),
                    "steps": state.get("steps", []),
                },
                error_detail=error_detail,
            )

        logger.info(f"Task {task_id} finalized with status: {final_status.value}")
        return {"status": final_status.value}

    def _route_after_execute(self, state: OrchestratorState) -> str:
        if state.get("is_cancelled"):
            return "abort_cancelled"
        if state.get("requires_approval"):
            return "halt_approval"
        return "verify"

    def _route_after_step(self, state: OrchestratorState) -> str:
        if state.get("is_cancelled"):
            return "abort_cancelled"
        if state.get("requires_approval"):
            return "halt_approval"
        if state.get("status") == "failed" or state.get("error"):
            return "abort_failed"

        idx = state["current_step_idx"]
        total = len(state.get("steps", []))
        if idx >= total:
            return "finalize"
        return "continue"

    async def execute_task_async(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        objective: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Entry point to launch task orchestration with resilient error containment."""
        initial_state: OrchestratorState = {
            "task_id": str(task_id),
            "user_id": str(user_id),
            "objective": objective,
            "steps": [],
            "current_step_idx": 0,
            "retry_count": 0,
            "artifacts": [],
            "status": "pending",
            "is_cancelled": False,
            "requires_approval": False,
            "ticket_id": None,
            "error": None,
            "context": context or {},
        }
        try:
            return await self.graph.ainvoke(initial_state)
        except Exception as e:
            logger.exception(f"Unhandled error during task {task_id} orchestration: {e}")
            try:
                async with async_session_factory() as session:
                    await TaskManager.update_task_status(
                        session=session,
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        error_detail={"unhandled_exception": str(e)},
                    )
            except Exception as dbe:
                logger.error(f"Failed to record task failure for {task_id}: {dbe}")
            return {"status": "failed", "error": str(e)}


# Global Orchestrator Singleton
orchestrator = CentralOrchestrator()
