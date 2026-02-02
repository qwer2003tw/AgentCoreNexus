"""Tests for exec_agent."""

import hashlib
import hmac
import time

import pytest

from src.exec_agent import (
    AuthenticationError,
    ExecAgent,
    ExecRequest,
    parse_request,
)


class TestParseRequest:
    def test_minimal(self):
        req = parse_request({"session_id": "s1", "command": "echo hi"})
        assert req.session_id == "s1"
        assert req.command == "echo hi"

    def test_full(self):
        req = parse_request({
            "session_id": "s1",
            "command": "ls",
            "workdir": "/tmp",
            "env": {"X": "1"},
            "timeout": 60,
            "timestamp": 123,
            "signature": "abc",
        })
        assert req.timeout == 60
        assert req.env == {"X": "1"}


class TestExecAgent:
    @pytest.fixture
    def agent(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return ExecAgent(workspace_root=str(workspace), default_timeout=10)

    @pytest.fixture
    def agent_auth(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return ExecAgent(
            hmac_secret="secret",
            workspace_root=str(workspace),
            default_timeout=10,
        )

    @pytest.mark.asyncio
    async def test_execute_simple(self, agent, tmp_path):
        (tmp_path / "workspace" / "sess").mkdir()
        req = ExecRequest(session_id="sess", command="echo hello")
        resp = await agent.execute(req)
        assert resp.type == "exit"
        assert "hello" in resp.data
        assert resp.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_env(self, agent, tmp_path):
        (tmp_path / "workspace" / "sess").mkdir()
        req = ExecRequest(session_id="sess", command="echo $VAR", env={"VAR": "val"})
        resp = await agent.execute(req)
        assert "val" in resp.data

    @pytest.mark.asyncio
    async def test_workspace_not_found(self, agent):
        req = ExecRequest(session_id="nope", command="echo")
        resp = await agent.execute(req)
        assert resp.type == "error"
        assert "not found" in resp.data.lower()

    @pytest.mark.asyncio
    async def test_timeout(self, agent, tmp_path):
        (tmp_path / "workspace" / "sess").mkdir()
        req = ExecRequest(session_id="sess", command="sleep 60", timeout=1)
        resp = await agent.execute(req)
        assert resp.type == "error"
        assert "timeout" in resp.data.lower()

    def test_auth_valid(self, agent_auth):
        ts = int(time.time())
        msg = f"sess:echo:{ts}"
        sig = hmac.new(b"secret", msg.encode(), hashlib.sha256).hexdigest()
        req = ExecRequest(session_id="sess", command="echo", timestamp=ts, signature=sig)
        assert agent_auth._verify_signature(req)

    def test_auth_invalid(self, agent_auth):
        req = ExecRequest(
            session_id="sess",
            command="echo",
            timestamp=int(time.time()),
            signature="bad",
        )
        with pytest.raises(AuthenticationError):
            agent_auth._verify_signature(req)
