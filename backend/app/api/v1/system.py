import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    HealthResponse,
    EmergencyStopResponse,
    ModelStatusResponse,
    CredentialSetRequest,
    CredentialStatusResponse,
    CredentialTestResponse,
)
from app.config import settings
from app.core.gateway import model_gateway, OpenAIProvider
from app.core.tasks import TaskManager, broadcaster
from app.database.session import check_db_health, get_db

router = APIRouter(prefix="/system", tags=["System"])
_boot_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Returns system status, DB connectivity, and active reasoning engine."""
    db_ok = await check_db_health()
    active_prov = await model_gateway.get_active_provider_name()
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        version="1.0.0",
        database="connected" if db_ok else "disconnected",
        active_provider=active_prov,
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


@router.get("/credentials", response_model=CredentialStatusResponse)
async def get_credentials():
    """Returns honest status of the active AI provider and Windows Credential Manager."""
    data = await model_gateway.get_credential_status()
    return CredentialStatusResponse(**data)


@router.post("/credentials", response_model=CredentialStatusResponse)
async def set_credentials(req: CredentialSetRequest):
    """Saves AI API credentials to Windows Credential Manager and applies immediately."""
    model_gateway.update_openai_credentials(api_key=req.api_key.strip(), model=req.model)
    data = await model_gateway.get_credential_status()
    return CredentialStatusResponse(**data)


@router.post("/credentials/test", response_model=CredentialTestResponse)
async def test_credentials(req: Optional[CredentialSetRequest] = None):
    """Performs live connection test against OpenAI provider."""
    if req and req.api_key:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=req.api_key.strip(), base_url=settings.OPENAI_BASE_URL)
        t0 = time.perf_counter()
        try:
            await asyncio.wait_for(client.models.list(), timeout=10.0)
            latency = int((time.perf_counter() - t0) * 1000)
            return CredentialTestResponse(success=True, provider="openai", model=req.model or "gpt-4o", latency_ms=latency)
        except Exception as e:
            return CredentialTestResponse(success=False, provider="openai", error=str(e))
    else:
        prov = model_gateway.get_provider("openai")
        if isinstance(prov, OpenAIProvider):
            res = await prov.test_connection()
            return CredentialTestResponse(
                success=res.get("success", False),
                provider="openai",
                model=res.get("model"),
                latency_ms=res.get("latency_ms"),
                error=res.get("error"),
            )
        return CredentialTestResponse(success=False, provider="openai", error="OpenAI provider not available")


@router.delete("/credentials", response_model=CredentialStatusResponse)
async def remove_credentials():
    """Removes AI API credentials from Windows Credential Manager and reverts to mock mode."""
    model_gateway.remove_openai_credentials()
    data = await model_gateway.get_credential_status()
    return CredentialStatusResponse(**data)
