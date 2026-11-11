import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Memory, Message, Conversation, User

logger = logging.getLogger("reeta.memory")


class MemoryService:
    """Manages working memory, conversation context, and vector-backed semantic long-term memory."""

    # Ephemeral working memory cache keyed by task_id
    _working_memory: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_working_memory(cls, task_id: str) -> Dict[str, Any]:
        return cls._working_memory.setdefault(str(task_id), {})

    @classmethod
    def set_working_memory_key(cls, task_id: str, key: str, value: Any):
        cls._working_memory.setdefault(str(task_id), {})[key] = value

    @classmethod
    def clear_working_memory(cls, task_id: str):
        cls._working_memory.pop(str(task_id), None)

    @classmethod
    async def compute_embedding(cls, text_content: str, dimension: int = 1536) -> List[float]:
        """
        Computes a vector embedding for text.
        If OpenAI API key is configured, uses text-embedding-3-small.
        Otherwise, uses a deterministic normalized vector projection for reliable local operation.
        """
        if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 0:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                resp = await client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=text_content[:8000],
                )
                return resp.data[0].embedding
            except Exception as e:
                logger.warning(f"Cloud embedding generation failed: {e}. Falling back to deterministic projection.")

        # Local deterministic normalized bag-of-words random projection
        # Enables semantic word-overlap similarity when cloud API is offline
        words = [w.lower().strip(".,!?;:()[]\"'") for w in text_content.split()]
        words = [w for w in words if len(w) > 2]
        import random
        vec = [0.0] * dimension
        if words:
            for word in words:
                w_seed = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16)
                rnd = random.Random(w_seed)
                for i in range(dimension):
                    vec[i] += rnd.uniform(-1.0, 1.0)
        else:
            seed = int(hashlib.sha256(text_content.encode("utf-8")).hexdigest()[:8], 16)
            rnd = random.Random(seed)
            vec = [rnd.uniform(-1.0, 1.0) for _ in range(dimension)]

        # Normalize to unit length
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [round(x / norm, 6) for x in vec]

    @classmethod
    async def store_memory(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        content: str,
        memory_type: str = "preference",  # 'preference', 'semantic', 'episodic', 'procedural'
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[uuid.UUID] = None,
    ) -> Memory:
        """Stores a new cognitive memory record with a vector embedding."""
        vec = await cls.compute_embedding(content, dimension=settings.EMBEDDING_DIMENSION)

        memory = Memory(
            user_id=user_id,
            conversation_id=conversation_id,
            memory_type=memory_type,
            category=category,
            content=content,
            embedding=vec,
            importance_score=0.8 if memory_type == "preference" else 0.5,
            metadata_=metadata or {},
        )
        session.add(memory)
        await session.commit()
        await session.refresh(memory)
        logger.info(f"Stored {memory_type} memory for user {user_id}: '{content[:40]}...'")
        return memory

    @classmethod
    async def search_memories(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search (<=> cosine distance) in PostgreSQL pgvector.
        """
        query_vec = await cls.compute_embedding(query, dimension=settings.EMBEDDING_DIMENSION)

        # Using pgvector cosine distance operator <=>
        stmt = (
            select(Memory, Memory.embedding.cosine_distance(query_vec).label("distance"))
            .where(Memory.user_id == user_id)
        )
        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)

        stmt = stmt.order_by(text("distance ASC")).limit(top_k)

        res = await session.execute(stmt)
        rows = res.all()

        memories = []
        for mem, distance in rows:
            # Update access count and last_accessed_at
            mem.access_count += 1
            mem.last_accessed_at = datetime.now(timezone.utc)
            similarity = round(max(0.0, 1.0 - float(distance)), 4) if distance is not None else 0.5
            memories.append({
                "id": str(mem.id),
                "content": mem.content,
                "memory_type": mem.memory_type,
                "category": mem.category,
                "similarity_score": similarity,
                "created_at": mem.created_at.isoformat(),
            })

        await session.commit()
        return memories
