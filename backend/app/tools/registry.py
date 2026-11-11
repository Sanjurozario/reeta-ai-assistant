import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ToolCall
from app.permissions.policy import ActionTier
from app.permissions.service import PermissionService, AuthCheckResult

logger = logging.getLogger("reeta.tools")


class VerificationResult(BaseModel):
    verified: bool
    evidence: str
    details: Optional[Dict[str, Any]] = None


class ToolExecutionResult(BaseModel):
    success: bool
    tool_name: str
    result: Any
    verification: VerificationResult
    duration_ms: int
    requires_approval: bool = False
    ticket_id: Optional[str] = None
    error: Optional[str] = None


class BaseTool(ABC):
    """Abstract base definition for all REETA tools."""

    name: str
    description: str
    category: str  # 'windows', 'browser', 'terminal', 'files', 'documents', 'research', 'coding', 'productivity'
    args_schema: Type[BaseModel]
    default_tier: ActionTier = ActionTier.AUTONOMOUS
    timeout_seconds: float = 30.0

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Executes the concrete action."""
        pass

    @abstractmethod
    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        """Empirically validates the real-world outcome of the action."""
        pass

    def extract_target_resource(self, **kwargs) -> str:
        """Extracts the principal target resource string for permission policy checking."""
        for key in ["path", "target_path", "filepath", "url", "command", "query", "title"]:
            if key in kwargs and kwargs[key]:
                return str(kwargs[key])
        return ""


class ToolRegistry:
    """Central registry and policy gatekeeper for all tool executions."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool):
        self._tools[tool.name.lower().strip()] = tool
        logger.debug(f"Registered tool: {tool.name} [{tool.category}]")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name.lower().strip())

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "default_tier": t.default_tier.value,
                "schema": t.args_schema.model_json_schema() if t.args_schema else {},
            }
            for t in self._tools.values()
        ]

    async def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        session: AsyncSession,
        actor: str = "agent",
        task_id: Optional[uuid.UUID] = None,
        task_step_id: Optional[uuid.UUID] = None,
        agent_run_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        approval_token: Optional[str] = None,
    ) -> ToolExecutionResult:
        """
        Executes a tool with strict Zero-Trust policy enforcement,
        timeout guards, execution telemetry, and outcome verification.
        """
        tool = self.get_tool(name)
        if not tool:
            return ToolExecutionResult(
                success=False,
                tool_name=name,
                result=None,
                verification=VerificationResult(verified=False, evidence=f"Tool '{name}' is not registered."),
                duration_ms=0,
                error=f"Tool '{name}' is not registered.",
            )

        # 1. Parse and validate arguments against tool's Pydantic schema
        try:
            validated_args = tool.args_schema(**arguments).model_dump()
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                tool_name=name,
                result=None,
                verification=VerificationResult(verified=False, evidence="Argument validation failed."),
                duration_ms=0,
                error=f"Invalid arguments for tool '{name}': {e}",
            )

        target_resource = tool.extract_target_resource(**validated_args)

        # 2. Enforce Central Zero-Trust Permission Check
        auth_res: AuthCheckResult = await PermissionService.evaluate_and_authorize(
            session=session,
            actor=actor,
            action=name,
            target_resource=target_resource,
            task_id=task_id,
            task_step_id=task_step_id,
            approval_token=approval_token,
            user_id=user_id,
        )

        if not auth_res.allowed:
            return ToolExecutionResult(
                success=False,
                tool_name=name,
                result=None,
                verification=VerificationResult(
                    verified=False,
                    evidence=f"Permission check blocked execution: {auth_res.reason}",
                ),
                duration_ms=0,
                requires_approval=auth_res.requires_approval,
                ticket_id=auth_res.ticket_id,
                error=auth_res.reason,
            )

        # 3. Execute with strict timeout guard
        t0 = time.perf_counter()
        raw_result = None
        error_msg = None
        is_success = False

        try:
            raw_result = await asyncio.wait_for(
                tool.execute(**validated_args),
                timeout=tool.timeout_seconds,
            )
            is_success = True
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timed out after {tool.timeout_seconds}s."
            logger.error(f"Timeout executing tool {name}")
        except Exception as e:
            error_msg = f"Tool execution failed: {e}"
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)

        duration_ms = int((time.perf_counter() - t0) * 1000)

        # 4. Perform Empirical Result Verification
        if is_success:
            try:
                verification = await tool.verify_outcome(raw_result, **validated_args)
            except Exception as e:
                verification = VerificationResult(
                    verified=False,
                    evidence=f"Verification routine failed: {e}",
                )
        else:
            verification = VerificationResult(
                verified=False,
                evidence=error_msg or "Execution was unsuccessful.",
            )

        # 5. Persist ToolCall record in DB if run context is present
        if agent_run_id:
            try:
                tool_record = ToolCall(
                    agent_run_id=agent_run_id,
                    task_step_id=task_step_id,
                    tool_name=tool.name,
                    tool_category=tool.category,
                    arguments=arguments,
                    result={"output": str(raw_result), "verification": verification.model_dump()},
                    duration_ms=duration_ms,
                    is_success=is_success and verification.verified,
                    requires_approval=auth_res.requires_approval,
                )
                session.add(tool_record)
                await session.flush()
            except Exception as e:
                logger.warning(f"Failed to record ToolCall row: {e}")

        return ToolExecutionResult(
            success=is_success and verification.verified,
            tool_name=name,
            result=raw_result,
            verification=verification,
            duration_ms=duration_ms,
            error=error_msg,
        )


# Global Tool Registry
tool_registry = ToolRegistry()
