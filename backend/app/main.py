import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_v1_router
from app.api.websockets import ws_router
from app.config import settings
from app.core.gateway import model_gateway
from app.database.session import check_db_health, engine

# Configure Structured Logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("reeta.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI application."""
    logger.info("=== REETA Personal AI Operating System Backend Booting ===")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Host: {settings.HOST}:{settings.PORT}")

    # Check database
    db_ok = await check_db_health()
    if db_ok:
        logger.info("PostgreSQL + pgvector connection: ACTIVE & HEALTHY")
    else:
        logger.warning("PostgreSQL connection check failed. Ensure container is running on port 5433.")

    # Check model gateway
    models_status = await model_gateway.get_active_providers_status()
    configured_providers = [k for k, v in models_status.items() if v.get("configured")]
    logger.info(f"Configured Model Providers: {configured_providers}")
    logger.info(f"Default Reasoning Provider: {settings.DEFAULT_MODEL_PROVIDER}")

    yield

    logger.info("=== REETA Backend Shutting Down ===")
    await engine.dispose()
    logger.info("Database engine connections closed.")


app = FastAPI(
    title="REETA Core API",
    description="Responsive Executive Engine for Tasks and Automation — Windows 11 Desktop Agent Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration for Tauri desktop and local web tooling
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# Register API Routers
app.include_router(api_v1_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "name": "REETA",
        "description": "Responsive Executive Engine for Tasks and Automation",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/api/v1/system/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
