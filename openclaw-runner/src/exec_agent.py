"""WebSocket Exec Agent for command execution.

Handles WebSocket connections, authenticates via HMAC,
and streams command output back to clients.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import signal
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
        """Initialize exec agent.

        Args:
            hmac_secret: Secret key for HMAC authentication
            workspace_root: Root directory for workspaces
            default_timeout: Default command timeout in seconds
            max_timestamp_drift: Maximum allowed timestamp drift in seconds
        """
        self.hmac_secret = hmac_secret
        self.workspace_root = workspace_root
        self.default_timeout = default_timeout
        self.max_timestamp_drift = max_timestamp_drift

    def _verify_signature(self, request: ExecRequest) -> bool:
        """Verify HMAC signature of request.

        Args:
            request: Exec request with signature

        Returns:
            True if signature is valid

        Raises:
            AuthenticationError: If verification fails
        """
        if not self.hmac_secret:
            logger.warning("HMAC secret not configured, skipping auth")
            return True

        # Check timestamp freshness
        now = int(time.time())
        if abs(now - request.timestamp) > self.max_timestamp_drift:
            raise AuthenticationError("Request timestamp too old or in future")

        # Build message to sign
        message = f"{request.session_id}:{request.command}:{request.timestamp}"
        expected = hmac.new(
            self.hmac_secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, request.signature):
            raise AuthenticationError("Invalid signature")

        return True

    def _get_workdir(self, request: ExecRequest) -> str:
        """Get working directory for command.

        Args:
            request: Exec request

        Returns:
            Working directory path
        """
        if request.workdir:
            # Ensure workdir is within workspace
            workdir = os.path.abspath(request.workdir)
            workspace = os.path.join(self.workspace_root, request.session_id)
            if not workdir.startswith(workspace):
                logger.warning(
                    f"Workdir {workdir} outside workspace, using workspace root"
                )
                return workspace
            return workdir
        return os.path.join(self.workspace_root, request.session_id)

    async def execute(self, request: ExecRequest) -> ExecResponse:
        """Execute command and return combined response.

        For simple commands that don't need streaming.

        Args:
            request: Exec request

        Returns:
            ExecResponse with output and exit code
        """
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

            # Combine output
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
            return ExecResponse(type="error", data=f"Command timed out after {timeout}s")
        except Exception as e:
            return ExecResponse(type="error", data=str(e))

    async def execute_stream(self, request: ExecRequest):
        """Execute command and yield output as it arrives.

        Generator that yields ExecResponse objects for each chunk
        of stdout/stderr, and a final exit response.

        Args:
            request: Exec request

        Yields:
            ExecResponse objects
        """
        start_time = time.monotonic()

        try:
            self._verify_signature(request)
        except AuthenticationError as e:
            yield ExecResponse(type="error", data=str(e))
            return

        workdir = self._get_workdir(request)
        if not os.path.exists(workdir):
            yield ExecResponse(type="error", data=f"Workspace not found: {workdir}")
            return

        env = os.environ.copy()
        env.update(request.env)

        try:
            process = await asyncio.create_subprocess_shell(
                request.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env=env,
                start_new_session=True,
            )

            timeout = request.timeout or self.default_timeout

            async def read_stream(stream, stream_type):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    yield ExecResponse(
                        type=stream_type,
                        data=line.decode("utf-8", errors="replace"),
                    )

            # Read both streams concurrently
            async def merged_streams():
                stdout_task = asyncio.create_task(
                    self._collect_stream(process.stdout, "stdout")
                )
                stderr_task = asyncio.create_task(
                    self._collect_stream(process.stderr, "stderr")
                )

                for task in asyncio.as_completed([stdout_task, stderr_task]):
                    for response in await task:
                        yield response

            try:
                async for response in asyncio.timeout(timeout).__aenter__():
                    async for resp in merged_streams():
                        yield resp
            except asyncio.TimeoutError:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                yield ExecResponse(
                    type="error", data=f"Command timed out after {timeout}s"
                )
                return

            await process.wait()
            duration_ms = int((time.monotonic() - start_time) * 1000)

            yield ExecResponse(
                type="exit",
                data="",
                exit_code=process.returncode,
                duration_ms=duration_ms,
            )

        except Exception as e:
            yield ExecResponse(type="error", data=str(e))

    async def _collect_stream(
        self, stream: asyncio.StreamReader, stream_type: str
    ) -> list[ExecResponse]:
        """Collect all output from a stream.

        Args:
            stream: asyncio StreamReader
            stream_type: "stdout" or "stderr"

        Returns:
            List of ExecResponse objects
        """
        responses = []
        while True:
            line = await stream.readline()
            if not line:
                break
            responses.append(
                ExecResponse(
                    type=stream_type,
                    data=line.decode("utf-8", errors="replace"),
                )
            )
        return responses


def parse_request(data: str | bytes | dict) -> ExecRequest:
    """Parse exec request from JSON.

    Args:
        data: JSON string, bytes, or dict

    Returns:
        ExecRequest object
    """
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
