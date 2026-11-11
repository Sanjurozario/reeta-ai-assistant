from fastapi import APIRouter
from app.api.v1.system import router as system_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.permissions import router as permissions_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(system_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(permissions_router)

__all__ = ["api_v1_router"]
