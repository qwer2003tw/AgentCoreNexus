"""Health check endpoint."""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    healthy: bool
    version: str
    uptime_seconds: float
    active_sessions: int
    message: Optional[str] = None


class HealthChecker:
    """Manages health check state."""

    def __init__(self, version: str = "0.1.0"):
        self.version = version
        self._healthy = True
        self._start_time: Optional[float] = None
        self._active_sessions = 0
        self._message: Optional[str] = None

    def start(self, start_time: float) -> None:
        self._start_time = start_time
        self._healthy = True

    def set_unhealthy(self, message: str) -> None:
        self._healthy = False
        self._message = message
        logger.warning(f"Service unhealthy: {message}")

    def set_healthy(self) -> None:
        self._healthy = True
        self._message = None

    def update_session_count(self, count: int) -> None:
        self._active_sessions = count

    def to_dict(self, current_time: float) -> dict:
        uptime = current_time - self._start_time if self._start_time else 0.0
        return {
            "status": "healthy" if self._healthy else "unhealthy",
            "version": self.version,
            "uptime_seconds": round(uptime, 2),
            "active_sessions": self._active_sessions,
            "message": self._message,
        }
