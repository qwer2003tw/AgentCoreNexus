"""Sandbox allocator for session workspace isolation."""

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Sandbox configuration."""

    workspace_root: str = "/workspace"
    efs_mount: str = "/efs"
    default_uid: int = 1000
    default_gid: int = 1000
    dir_permissions: int = 0o700


class SandboxError(Exception):
    """Sandbox operation error."""

    pass


class Sandbox:
    """Manages isolated workspace directories for sessions."""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._ensure_workspace_root()

    def _ensure_workspace_root(self) -> None:
        root = Path(self.config.workspace_root)
        if not root.exists():
            root.mkdir(parents=True, mode=0o755)
            logger.info(f"Created workspace root: {root}")

    def _session_path(self, session_id: str) -> Path:
        # Sanitize to prevent directory traversal
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        if not safe_id:
            raise SandboxError(f"Invalid session_id: {session_id}")
        return Path(self.config.workspace_root) / safe_id

    def create(self, session_id: str) -> str:
        """Create isolated workspace for session."""
        workspace_path = self._session_path(session_id)

        if workspace_path.exists():
            logger.warning(f"Workspace already exists: {workspace_path}")
            return str(workspace_path)

        try:
            workspace_path.mkdir(mode=self.config.dir_permissions, parents=True)
            if os.geteuid() == 0:
                os.chown(
                    workspace_path, self.config.default_uid, self.config.default_gid
                )
            logger.info(f"Created sandbox: {workspace_path}")
            return str(workspace_path)
        except OSError as e:
            raise SandboxError(f"Failed to create workspace: {e}") from e

    def destroy(self, session_id: str) -> None:
        """Destroy session workspace."""
        workspace_path = self._session_path(session_id)
        if not workspace_path.exists():
            return
        try:
            shutil.rmtree(workspace_path)
            logger.info(f"Destroyed sandbox: {workspace_path}")
        except OSError as e:
            raise SandboxError(f"Failed to destroy workspace: {e}") from e

    def exists(self, session_id: str) -> bool:
        return self._session_path(session_id).exists()

    def get_path(self, session_id: str) -> Optional[str]:
        path = self._session_path(session_id)
        return str(path) if path.exists() else None

    def list_sessions(self) -> list[str]:
        root = Path(self.config.workspace_root)
        if not root.exists():
            return []
        return [d.name for d in root.iterdir() if d.is_dir()]

    def cleanup_stale(self, active_sessions: set[str]) -> int:
        cleaned = 0
        for session_id in self.list_sessions():
            if session_id not in active_sessions:
                self.destroy(session_id)
                cleaned += 1
        return cleaned
