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
        builder.add_edge("execute_step", "verify_step")

        builder.add_conditional_edges(
            "verify_step",
            self._route_after_step,
            {
                "continue": "execute_step",
                "finalize": "finalize_task",
                "halt_approval": END,
                "abort_cancelled": "finalize_task",
            },
        )

        builder.add_edge("finalize_task", END)
        return builder.compile()

    # ========================================================================
    # Graph Nodes
    # ========================================================================

    async def _node_plan_task(self, state: OrchestratorState) -> Dict[str, Any]:
        """Decomposes user objective into an ordered step sequence with assigned agents."""
        objective = state["objective"]
        task_id = state["task_id"]
        logger.info(f"Orchestrator planning task {task_id}: '{objective}'")

        # Decompose using rule-based and intent analysis
        obj_lower = objective.lower()
        steps = []

        if "pdf" in obj_lower or "report" in obj_lower:
            steps = [
                {"step_number": 1, "title": f"Gather research data on '{objective}'", "agent_type": "research"},
                {"step_number": 2, "title": "Synthesize report and generate PDF document", "agent_type": "file"},
            ]
        elif "organize" in obj_lower or "clean" in obj_lower:
            steps = [
                {"step_number": 1, "title": "Scan directory and discover files", "agent_type": "file"},
                {"step_number": 2, "title": "Batch categorize and organize into folders", "agent_type": "file"},
            ]
        elif "app" in obj_lower or "open" in obj_lower or "notepad" in obj_lower or "calc" in obj_lower:
            steps = [
                {"step_number": 1, "title": f"Launch target application for '{objective}'", "agent_type": "computer"},
                {"step_number": 2, "title": "Inspect open windows and verify active UI", "agent_type": "computer"},
            ]
        elif "bug" in obj_lower or "code" in obj_lower or "test" in obj_lower:
            steps = [
                {"step_number": 1, "title": "Search codebase for target symbol or bug", "agent_type": "coding"},
                {"step_number": 2, "title": "Execute test suite to confirm baseline", "agent_type": "coding"},
            ]
        elif "browse" in obj_lower or "http" in obj_lower or "website" in obj_lower or "extract" in obj_lower:
            steps = [
                {"step_number": 1, "title": f"Navigate to website and capture page context", "agent_type": "browser"},
                {"step_number": 2, "title": "Extract structured information from page", "agent_type": "browser"},
            ]
        elif "remind" in obj_lower or "schedule" in obj_lower:
            steps = [
                {"step_number": 1, "title": f"Create scheduled reminder for '{objective}'", "agent_type": "productivity"},
            ]
        else:
            steps = [
                {"step_number": 1, "title": "Analyze request and research context", "agent_type": "research"},
                {"step_number": 2, "title": "Execute objective operations", "agent_type": "file"},
            ]

        # Record steps in DB and notify UI
        async with async_session_factory() as session:
            existing = await TaskManager.get_task(session, uuid.UUID(task_id))
            if existing and existing.steps and len(existing.steps) > 0:
                steps = [
                    {
                        "step_number": s.step_number,
                        "title": s.title,
                        "agent_type": s.agent_type,
                        "input_payload": s.input_payload or {},
                    }
                    for s in sorted(existing.steps, key=lambda x: x.step_number)
                ]
            else:
                await TaskManager.create_steps(session, uuid.UUID(task_id), steps)
            await TaskManager.update_task_status(session, uuid.UUID(task_id), TaskStatus.RUNNING)

        return {
            "steps": steps,
            "current_step_idx": 0,
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

        # Handle Tier 2 Approval interruption
        if step_result.requires_approval:
            logger.info(f"Task {task_id} halted: Ticket {step_result.ticket_id} requires approval.")
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
        if isinstance(step_result.output, dict):
            if "pdf_path" in step_result.output:
                artifacts.append({"type": "pdf", "path": step_result.output["pdf_path"]})
            if "screenshot_path" in step_result.output:
                artifacts.append({"type": "screenshot", "path": step_result.output["screenshot_path"]})

        current_step["result"] = step_result.output
        current_step["verified"] = step_result.verified
        current_step["evidence"] = step_result.verification_evidence

        return {
            "steps": steps,
            "artifacts": artifacts,
            "status": "step_executed",
        }

    async def _node_verify_step(self, state: OrchestratorState) -> Dict[str, Any]:
        """Evaluates empirical evidence of outcome before advancing."""
        idx = state["current_step_idx"]
        current_step = state["steps"][idx]
        task_id = state["task_id"]

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

        return {
            "current_step_idx": idx + 1 if is_verified else idx,
            "status": "step_verified" if is_verified else "verification_failed",
        }

    async def _node_finalize_task(self, state: OrchestratorState) -> Dict[str, Any]:
        """Updates final task status in database and broadcasts completion event."""
        task_id = state["task_id"]
        final_status = TaskStatus.COMPLETED if state.get("current_step_idx", 0) >= len(state.get("steps", [])) else TaskStatus.FAILED

        if state.get("is_cancelled"):
            final_status = TaskStatus.CANCELLED

        async with async_session_factory() as session:
            await TaskManager.update_task_status(
                session=session,
                task_id=uuid.UUID(task_id),
                status=final_status,
                result={"artifacts": state.get("artifacts", []), "steps": state.get("steps", [])},
            )

        logger.info(f"Task {task_id} finalized with status: {final_status.value}")
        return {"status": final_status.value}

    def _route_after_step(self, state: OrchestratorState) -> str:
        if state.get("is_cancelled"):
            return "abort_cancelled"
        if state.get("requires_approval"):
            return "halt_approval"

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
        """Entry point to launch task orchestration."""
        initial_state: OrchestratorState = {
            "task_id": str(task_id),
            "user_id": str(user_id),
            "objective": objective,
            "steps": [],
            "current_step_idx": 0,
            "artifacts": [],
            "status": "pending",
            "is_cancelled": False,
            "requires_approval": False,
            "ticket_id": None,
            "error": None,
            "context": context or {},
        }
        return await self.graph.ainvoke(initial_state)


# Global Orchestrator Singleton
orchestrator = CentralOrchestrator()
