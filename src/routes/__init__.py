"""FastAPI route modules mounted by the application (docs/api/REST-API.md)."""

from fastapi import APIRouter

from src.routes.agents import router as agents_router
from src.routes.chat import router as chat_router
from src.routes.memory import router as memory_router
from src.routes.models import router as models_router
from src.routes.system import router as system_router

api_router = APIRouter(prefix="/api")
api_router.include_router(system_router)
api_router.include_router(chat_router)
api_router.include_router(agents_router)
api_router.include_router(models_router)
api_router.include_router(memory_router)

__all__ = ["api_router"]
