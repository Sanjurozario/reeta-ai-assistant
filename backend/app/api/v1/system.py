import asyncio
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import HealthResponse, EmergencyStopResponse, ModelStatusResponse
from app.config import settings
from app.core.gateway import model_gateway
from app.core.tasks import TaskManager, broadcaster
from app.database.session import check_db_health, get_db

router = APIRouter(prefix="/system", tags=["System"])
_boot_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Returns system status, DB connectivity, and active reasoning engine."""
    db_ok = await check_db_health()
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        version="1.0.0",
        database="connected" if db_ok else "disconnected",
        active_provider=settings.DEFAULT_MODEL_PROVIDER,
        uptime_seconds=round(time.time() - _boot_time, 2),
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/emergency-stop", response_model=EmergencyStopResponse)
async def emergency_stop(session: AsyncSession = Depends(get_db)):
    """
    Emergency kill-switch: Immediately cancels all active background task workers,
    signals interruption, and broadcasts emergency stop event across WebSockets.
    """
    # Cancel all active workers in TaskManager
    cancelled_count = 0
    for task_id, worker in list(TaskManager._active_workers.items()):
        if not worker.done():
            worker.cancel()
            cancelled_count += 1
        if task_id in TaskManager._cancellation_events:
            TaskManager._cancellation_events[task_id].set()

    # Clear active registries
    TaskManager._active_workers.clear()
    TaskManager._cancellation_events.clear()

    # Broadcast emergency stop
    await broadcaster.broadcast(
        event="emergency_stop",
        task_id="system",
        payload={"message": f"Emergency stop executed. Terminated {cancelled_count} active workers."},
    )

    return EmergencyStopResponse(
        success=True,
        message=f"Emergency stop executed. {cancelled_count} active agent workers terminated.",
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/models", response_model=ModelStatusResponse)
async def get_models():
    """Returns configuration and availability of all AI model providers."""
    status = await model_gateway.get_active_providers_status()
    return ModelStatusResponse(
        default_provider=settings.DEFAULT_MODEL_PROVIDER,
        providers=status,
    )
