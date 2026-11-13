import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.database.models import User
from app.memory.store import MemoryService

router = APIRouter(prefix="/memory", tags=["Cognitive Memory"])


class StoreMemoryRequest(BaseModel):
    content: str = Field(..., description="Memory content to store")
    memory_type: str = Field("preference", description="'preference', 'semantic', 'episodic', 'procedural'")
    category: str = Field("general", description="Memory classification category")
    metadata: Optional[Dict[str, Any]] = None


class SearchMemoryRequest(BaseModel):
    query: str = Field(..., description="Query text to find semantic vector matches")
    top_k: int = Field(5, ge=1, le=50)
    memory_type: Optional[str] = None


async def _get_or_create_default_user(session: AsyncSession) -> User:
    res = await session.execute(select(User).limit(1))
    user = res.scalars().first()
    if not user:
        user = User(
            username="reeta_operator",
            email="operator@reeta.ai",
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@router.post("")
async def store_memory(req: StoreMemoryRequest, session: AsyncSession = Depends(get_db)):
    user = await _get_or_create_default_user(session)
    mem = await MemoryService.store_memory(
        session=session,
        user_id=user.id,
        content=req.content,
        memory_type=req.memory_type,
        category=req.category,
        metadata=req.metadata,
    )
    return {
        "id": str(mem.id),
        "content": mem.content,
        "memory_type": mem.memory_type,
        "category": mem.category,
        "created_at": mem.created_at.isoformat(),
    }


@router.post("/search")
async def search_memories(req: SearchMemoryRequest, session: AsyncSession = Depends(get_db)):
    user = await _get_or_create_default_user(session)
    results = await MemoryService.search_memories(
        session=session,
        user_id=user.id,
        query=req.query,
        top_k=req.top_k,
        memory_type=req.memory_type,
    )
    return results


@router.get("")
async def list_memories(
    limit: int = 50,
    memory_type: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    """Retrieves all stored cognitive memories for the active user."""
    user = await _get_or_create_default_user(session)
    return await MemoryService.list_memories(
        session=session,
        user_id=user.id,
        limit=limit,
        memory_type=memory_type,
    )


@router.delete("/{memory_id}")
async def delete_memory(memory_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    """Deletes a memory record permanently."""
    success = await MemoryService.delete_memory(session=session, memory_id=memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory record not found.")
    return {"success": True, "message": "Memory removed from pgvector repository."}


class UpdateMemoryRequest(BaseModel):
    content: str = Field(..., description="Updated memory text")


@router.patch("/{memory_id}")
async def update_memory(
    memory_id: uuid.UUID,
    req: UpdateMemoryRequest,
    session: AsyncSession = Depends(get_db),
):
    """Updates memory text and regenerates embedding."""
    updated = await MemoryService.update_memory(
        session=session,
        memory_id=memory_id,
        content=req.content,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Memory record not found.")
    return updated


class ForgetMemoryRequest(BaseModel):
    query: str = Field(..., description="Semantic query of memory to forget (e.g. 'dark mode preference')")


@router.post("/forget")
async def forget_memory(req: ForgetMemoryRequest, session: AsyncSession = Depends(get_db)):
    """Removes closest matching semantic memory based on natural language query."""
    user = await _get_or_create_default_user(session)
    forgotten = await MemoryService.delete_matching_memory(
        session=session,
        user_id=user.id,
        query=req.query,
    )
    if not forgotten:
        return {"forgotten": False, "message": f"No memory found closely matching '{req.query}'."}
    return {
        "forgotten": True,
        "message": f"Successfully forgot: '{forgotten}'",
        "content": forgotten,
    }


@router.get("/working/{task_id}")
async def get_working_memory(task_id: str):
    return {"task_id": task_id, "data": MemoryService.get_working_memory(task_id)}

