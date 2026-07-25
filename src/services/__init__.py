"""Internal service layer — Background Service Manager (docs/24-BACKGROUND-SERVICES.md)."""

from src.services.manager import BackgroundService, ServiceManager, ServiceState

__all__ = ["BackgroundService", "ServiceManager", "ServiceState"]
