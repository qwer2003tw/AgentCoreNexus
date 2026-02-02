"""WebSocket Exec Agent for command execution."""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecRequest:
    """Command execution request."""

    session_id: str
    command: str
    workdir: Optional[str] = None
    env: dict[str, str] = field(default_factory=dict)
    timeout: int = 300
    timestamp: int = 0
    signature: str = ""


@dataclass
class ExecResponse:
    """Command execution response."""

    type: str  # "stdout", "stderr", "exit", "error"
    data: str = ""
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None


class AuthenticationError(Exception):
    """HMAC authentication failed."""

    pass


class ExecAgent:
    """Handles command execution with HMAC authentication."""

    def __init__(
        self,
        hmac_secret: Optional[str] = None,
        workspace_root: str = "/workspace",
        default_timeout: int = 300,
        max_timestamp_drift: int = 60,
    ):
        self.hmac_secret = hmac_secret
        self.workspace_root = workspace_root
        self.default_timeout = default_timeout
        self.max_timestamp_drift = max_timestamp_drift

    def _verify_signature(self, request: ExecRequest) -> bool:
        """Verify HMAC signature of request."""
        if not self.hmac_secret:
            logger.warning("HMAC secret not configured, skipping auth")
            return True

        now = int(time.time())
        if abs(now - request.timestamp) > self.max_timestamp_drift:
            raise AuthenticationError("Request timestamp too old or in future")

        message = f"{request.session_id}:{request.command}:{request.timestamp}"
        expected = hmac.new(
            self.hmac_secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, request.signature):
            raise AuthenticationError("Invalid signature")

        return True

    def _get_workdir(self, request: ExecRequest) -> str:
        """Get working directory for command."""
        if request.workdir:
            workdir = os.path.abspath(request.workdir)
            workspace = os.path.join(self.workspace_root, request.session_id)
            if not workdir.startswith(workspace):
                logger.warning(f"Workdir outside workspace, using root")
                return workspace
            return workdir
        return os.path.join(self.workspace_root, request.session_id)

    async def execute(self, request: ExecRequest) -> ExecResponse:
        """Execute command and return response."""
        start_time = time.monotonic()

        try:
            self._verify_signature(request)
        except AuthenticationError as e:
            return ExecResponse(type="error", data=str(e))

        workdir = self._get_workdir(request)
        if not os.path.exists(workdir):
            return ExecResponse(type="error", data=f"Workspace not found: {workdir}")

        env = os.environ.copy()
        env.update(request.env)

        try:
            process = await asyncio.create_subprocess_shell(
                request.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env=env,
            )

            timeout = request.timeout or self.default_timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            output = ""
            if stdout:
                output += stdout.decode("utf-8", errors="replace")
            if stderr:
                output += stderr.decode("utf-8", errors="replace")

            return ExecResponse(
                type="exit",
                data=output,
                exit_code=process.returncode,
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            process.kill()
            return ExecResponse(type="error", data=f"Timeout after {timeout}s")
        except Exception as e:
            return ExecResponse(type="error", data=str(e))


def parse_request(data: str | bytes | dict) -> ExecRequest:
    """Parse exec request from JSON."""
    if isinstance(data, (str, bytes)):
        data = json.loads(data)

    return ExecRequest(
        session_id=data["session_id"],
        command=data["command"],
        workdir=data.get("workdir"),
        env=data.get("env", {}),
        timeout=data.get("timeout", 300),
        timestamp=data.get("timestamp", 0),
        signature=data.get("signature", ""),
    )
