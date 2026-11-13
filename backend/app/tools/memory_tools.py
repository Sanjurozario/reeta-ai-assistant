import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.permissions.policy import ActionTier
from app.tools.registry import BaseTool, VerificationResult
from app.memory.store import MemoryService


class MemoryStoreInput(BaseModel):
    content: str = Field(..., description="Fact, user preference, or context to store in long-term memory")
    memory_type: str = Field(default="preference", description="Type: 'preference', 'fact', or 'context'")
    category: str = Field(default="general", description="Category tag")


class MemoryStoreTool(BaseTool):
    name = "memory_store"
    description = "Stores a user preference, fact, or instruction into long-term vector memory."
    category = "memory"
    args_schema = MemoryStoreInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, content: str, memory_type: str = "preference", category: str = "general") -> Dict[str, Any]:
        mem = await MemoryService.store_memory(
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            content=content,
            memory_type=memory_type,
            category=category,
        )
        return {
            "id": str(mem.id),
            "content": mem.content,
            "type": mem.memory_type,
            "status": "stored",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and result.get("id"):
            return VerificationResult(
                verified=True,
                evidence=f"Stored memory entry: '{result.get('content')[:50]}' (ID: {result.get('id')[:8]}).",
            )
        return VerificationResult(verified=False, evidence="Memory storage failed.")


class MemorySearchInput(BaseModel):
    query: str = Field(..., description="Semantic search query to recall relevant memories or preferences")
    limit: int = Field(default=5, ge=1, le=20)


class MemorySearchTool(BaseTool):
    name = "memory_search"
    description = "Searches long-term cognitive memory using semantic similarity to recall preferences and facts."
    category = "memory"
    args_schema = MemorySearchInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, query: str, limit: int = 5) -> Dict[str, Any]:
        results = await MemoryService.search_memories(
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            query_text=query,
            limit=limit,
        )
        items = [{"id": str(m.id), "content": m.content, "type": m.memory_type, "similarity": round(score, 3)} for m, score in results]
        return {
            "query": query,
            "total_found": len(items),
            "memories": items,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict):
            return VerificationResult(
                verified=True,
                evidence=f"Retrieved {result.get('total_found', 0)} relevant memories matching '{result.get('query')}'.",
            )
        return VerificationResult(verified=False, evidence="Memory search failed.")


class MemoryForgetInput(BaseModel):
    query: str = Field(..., description="Query matching memories or preferences to forget/delete")


class MemoryForgetTool(BaseTool):
    name = "memory_forget"
    description = "Deletes memories matching a semantic search query from long-term memory."
    category = "memory"
    args_schema = MemoryForgetInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, query: str) -> Dict[str, Any]:
        count = await MemoryService.forget_memories(
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            query_text=query,
        )
        return {
            "query": query,
            "deleted_count": count,
            "status": "forgotten",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        return VerificationResult(
            verified=True,
            evidence=f"Removed {result.get('deleted_count', 0)} memory entries matching '{kwargs.get('query')}'.",
        )

