"""HTTP/WebSocket server for Runner."""

import asyncio
import json
import logging
import time
from typing import Optional

from aiohttp import web, WSMsgType

from .config import Config, load_config
from .exec_agent import ExecAgent, parse_request
from .health import HealthChecker
from .sandbox import Sandbox, SandboxConfig

logger = logging.getLogger(__name__)


class RunnerServer:
    """HTTP/WebSocket server for command execution."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.health = HealthChecker()
        self.sandbox = Sandbox(
            SandboxConfig(
                workspace_root=self.config.workspace_root,
                efs_mount=self.config.efs_mount,
            )
        )
        self.exec_agent = ExecAgent(
            hmac_secret=self.config.exec_hmac_secret,
            workspace_root=self.config.workspace_root,
            default_timeout=self.config.exec_timeout_seconds,
        )
        self._active_sessions: set[str] = set()

    async def health_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        status = self.health.to_dict(time.time())
        http_status = 200 if status["status"] == "healthy" else 503
        return web.json_response(status, status=http_status)

    async def exec_handler(self, request: web.Request) -> web.Response:
        """HTTP exec endpoint (for simple commands)."""
        try:
            data = await request.json()
            exec_request = parse_request(data)

            # Ensure workspace exists
            if not self.sandbox.exists(exec_request.session_id):
                self.sandbox.create(exec_request.session_id)

            response = await self.exec_agent.execute(exec_request)

            return web.json_response({
                "type": response.type,
                "data": response.data,
                "exit_code": response.exit_code,
                "duration_ms": response.duration_ms,
            })

        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        except KeyError as e:
            return web.json_response({"error": f"Missing field: {e}"}, status=400)
        except Exception as e:
            logger.exception("Exec handler error")
            return web.json_response({"error": str(e)}, status=500)

    async def ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket exec endpoint (for streaming)."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        session_id = None

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        exec_request = parse_request(msg.data)
                        session_id = exec_request.session_id

                        # Track active session
                        self._active_sessions.add(session_id)
                        self.health.update_session_count(len(self._active_sessions))

                        # Ensure workspace
                        if not self.sandbox.exists(session_id):
                            self.sandbox.create(session_id)

                        # Execute and send response
                        response = await self.exec_agent.execute(exec_request)
                        await ws.send_json({
                            "type": response.type,
                            "data": response.data,
                            "exit_code": response.exit_code,
                            "duration_ms": response.duration_ms,
                        })

                    except Exception as e:
                        await ws.send_json({"type": "error", "data": str(e)})

                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WS error: {ws.exception()}")

        finally:
            if session_id:
                self._active_sessions.discard(session_id)
                self.health.update_session_count(len(self._active_sessions))

        return ws

    def create_app(self) -> web.Application:
        """Create aiohttp application."""
        app = web.Application()
        app.router.add_get(self.config.health_path, self.health_handler)
        app.router.add_post("/exec", self.exec_handler)
        app.router.add_get(self.config.ws_path, self.ws_handler)
        return app

    def run(self) -> None:
        """Start the server."""
        self.health.start(time.time())
        app = self.create_app()
        logger.info(f"Starting server on {self.config.host}:{self.config.port}")
        web.run_app(app, host=self.config.host, port=self.config.port)


def main():
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    server = RunnerServer()
    server.run()


if __name__ == "__main__":
    main()
