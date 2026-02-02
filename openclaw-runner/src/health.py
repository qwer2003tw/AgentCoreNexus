"""Health check endpoint for ALB."""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health check status."""

    healthy: bool
    version: str
    uptime_seconds: float
    active_sessions: int
    message: Optional[str] = None


class HealthChecker:
    """Manages health check state."""

    def __init__(self, version: str = "0.1.0"):
        """Initialize health checker.

        Args:
            version: Application version
        """
        self.version = version
        self._healthy = True
        self._start_time: Optional[float] = None
        self._active_sessions = 0
        self._message: Optional[str] = None

    def start(self, start_time: float) -> None:
        """Mark service as started.

        Args:
            start_time: Unix timestamp of service start
        """
        self._start_time = start_time
        self._healthy = True
        logger.info("Health checker started")

    def set_unhealthy(self, message: str) -> None:
        """Mark service as unhealthy.

        Args:
            message: Reason for unhealthy status
        """
        self._healthy = False
        self._message = message
        logger.warning(f"Service marked unhealthy: {message}")

    def set_healthy(self) -> None:
        """Mark service as healthy."""
        self._healthy = True
        self._message = None

    def update_session_count(self, count: int) -> None:
        """Update active session count.

        Args:
            count: Number of active sessions
        """
        self._active_sessions = count

    def get_status(self, current_time: float) -> HealthStatus:
        """Get current health status.

        Args:
            current_time: Current Unix timestamp

        Returns:
            HealthStatus object
        """
        uptime = 0.0
        if self._start_time:
            uptime = current_time - self._start_time

        return HealthStatus(
            healthy=self._healthy,
            version=self.version,
            uptime_seconds=uptime,
            active_sessions=self._active_sessions,
            message=self._message,
        )

    def to_dict(self, current_time: float) -> dict:
        """Get health status as dictionary.

        Args:
            current_time: Current Unix timestamp

        Returns:
            Dictionary representation of health status
        """
        status = self.get_status(current_time)
        return {
            "status": "healthy" if status.healthy else "unhealthy",
            "version": status.version,
            "uptime_seconds": round(status.uptime_seconds, 2),
            "active_sessions": status.active_sessions,
            "message": status.message,
        }
