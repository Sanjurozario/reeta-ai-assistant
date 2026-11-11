import uuid
import pytest
from sqlalchemy import text, select
from app.database.models import User, Conversation, Message, Task, TaskStep, Memory, TaskStatus
from app.database.session import check_db_health


@pytest.mark.asyncio
async def test_database_health_probe():
    is_healthy = await check_db_health()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_pgvector_extension_active(db_session):
    result = await db_session.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    )
    ext = result.scalar()
    assert ext == "vector"


@pytest.mark.asyncio
async def test_user_and_conversation_crud(db_session):
    # 1. Create User
    unique_user = f"user_{uuid.uuid4().hex[:8]}"
    user = User(
        username=unique_user,
        email=f"{unique_user}@reeta.local",
        password_hash="hashed_pw_xyz",
        preferences={"theme": "obsidian", "voice": "aria"},
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.username == unique_user

    # 2. Create Conversation
    conv = Conversation(
        user_id=user.id,
        title="Testing Memory & DAG",
        mode="coding",
    )
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    assert conv.id is not None
    assert conv.title == "Testing Memory & DAG"

    # 3. Create Message
    msg = Message(
        conversation_id=conv.id,
        sender_type="user",
        content="Execute task test",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)

    assert msg.id is not None
    assert msg.content == "Execute task test"

    # 4. Create Memory with Vector
    test_vec = [0.1] * 1536
    memory = Memory(
        user_id=user.id,
        conversation_id=conv.id,
        memory_type="preference",
        content="Prefers cyan buttons",
        embedding=test_vec,
    )
    db_session.add(memory)
    await db_session.commit()
    await db_session.refresh(memory)

    assert memory.id is not None
    assert len(memory.embedding) == 1536

    # 5. Clean up
    await db_session.delete(user)
    await db_session.commit()
