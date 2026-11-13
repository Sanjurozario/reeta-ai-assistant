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
from app.database.session import check_db_health, engine, init_db_schema
import app.tools  # Initialize tool registry

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
    logger.info(f"Standalone Mode: {settings.is_standalone()} | Launch Token Protection: {bool(settings.REETA_LAUNCH_TOKEN)}")

    # Initialize database schema (ensures SQLite standalone has all tables & default user)
    await init_db_schema()

    # Check database
    db_ok = await check_db_health()
    if db_ok:
        backend_type = "SQLite + sqlite-vec" if settings.DATABASE_URL.startswith("sqlite") else "PostgreSQL + pgvector"
        logger.info(f"Database ({backend_type}) connection: ACTIVE & HEALTHY")
    else:
        logger.warning("Database connection check failed.")

    # Check model gateway
    models_status = await model_gateway.get_active_providers_status()
    configured_providers = [k for k, v in models_status.items() if v.get("configured")]
    logger.info(f"Configured Model Providers: {configured_providers}")
    logger.info(f"Default Reasoning Provider: {settings.DEFAULT_MODEL_PROVIDER}")

    # Start native voice pipeline if enabled
    if settings.VOICE_ENABLED:
        try:
            from app.voice.native_audio import native_audio
            import asyncio
            native_audio.start(loop=asyncio.get_running_loop())
            logger.info("Native Voice Engine: ACTIVE (Mic, VAD, Wake-Word, SAPI TTS)")
        except Exception as e:
            logger.warning(f"Native voice startup notice: {e}")

    yield

    logger.info("=== REETA Backend Shutting Down ===")
    if settings.VOICE_ENABLED:
        try:
            from app.voice.native_audio import native_audio
            native_audio.stop()
        except Exception:
            pass
    await engine.dispose()
    logger.info("Database engine connections closed.")


is_standalone_mode = settings.is_standalone() or bool(settings.REETA_LAUNCH_TOKEN)

app = FastAPI(
    title="REETA Core API",
    description="Responsive Executive Engine for Tasks and Automation — Windows 11 Desktop Agent Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if is_standalone_mode else "/docs",
    redoc_url=None if is_standalone_mode else "/redoc",
)

# Strict Origin allow-list: NO wildcard '*', strictly Tauri WebView and authorized local dev
ALLOWED_ORIGINS = [
    "tauri://localhost",
    "https://tauri.localhost",
    "http://tauri.localhost",
    "http://localhost:1420",
    "http://127.0.0.1:1420",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_token_and_origin_middleware(request: Request, call_next):
    """
    Enforces strict desktop-only isolation:
    1. Origin validation: rejects any request originating from an external browser or disallowed domain.
    2. Per-launch cryptographically random secret token validation on all endpoints (except internal loopback health check).
    """
    origin = request.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        logger.warning(f"Blocked unauthorized external Origin attempt: {origin}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "Forbidden", "detail": f"Origin '{origin}' is rejected by desktop security policy."},
        )

    token = settings.REETA_LAUNCH_TOKEN
    if token:
        # Only internal loopback TCP health check is exempt
        exempt_paths = {"/api/v1/system/health"}
        if request.method != "OPTIONS" and request.url.path not in exempt_paths:
            auth_header = request.headers.get("Authorization", "")
            expected = f"Bearer {token}"
            query_token = request.query_params.get("token")
            if auth_header != expected and query_token != token:
                logger.warning(f"Rejected unauthenticated request to {request.url.path} from external process.")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "Unauthorized", "detail": "Invalid or missing launch token"},
                )

    return await call_next(request)


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
        "platform": "Windows 11 Desktop",
        "version": "1.0.0",
        "status": "operational",
    }
