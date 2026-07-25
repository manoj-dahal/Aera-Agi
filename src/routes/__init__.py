"""FastAPI route modules mounted by the application (docs/api/REST-API.md)."""

from fastapi import APIRouter

from src.routes.agents import router as agents_router
from src.routes.auth import router as auth_router
from src.routes.automation import router as automation_router
from src.routes.chat import router as chat_router
from src.routes.memory import router as memory_router
from src.routes.models import router as models_router
from src.routes.plugins import router as plugins_router
from src.routes.security import router as security_router
from src.routes.services import router as services_router
from src.routes.system import router as system_router
from src.routes.voice import router as voice_router

api_router = APIRouter(prefix="/api")
api_router.include_router(system_router)
api_router.include_router(chat_router)
api_router.include_router(agents_router)
api_router.include_router(models_router)
api_router.include_router(memory_router)
api_router.include_router(voice_router)
api_router.include_router(services_router)
api_router.include_router(automation_router)
api_router.include_router(auth_router)
api_router.include_router(security_router)
api_router.include_router(plugins_router)

__all__ = ["api_router"]
