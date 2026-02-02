"""Tests for exec_agent module."""

import hashlib
import hmac
import time

import pytest

from src.exec_agent import (
    AuthenticationError,
    ExecAgent,
    ExecRequest,
    ExecResponse,
    parse_request,
)


class TestExecRequest:
    """Tests for ExecRequest parsing."""

    def test_parse_minimal(self):
        """Parse minimal request."""
        data = {"session_id": "test-123", "command": "echo hello"}
        req = parse_request(data)

        assert req.session_id == "test-123"
        assert req.command == "echo hello"
        assert req.workdir is None
        assert req.env == {}
        assert req.timeout == 300

    def test_parse_full(self):
        """Parse request with all fields."""
        data = {
            "session_id": "test-123",
            "command": "ls -la",
            "workdir": "/workspace/test-123/subdir",
            "env": {"FOO": "bar"},
            "timeout": 60,
            "timestamp": 1234567890,
            "signature": "abc123",
        }
        req = parse_request(data)

        assert req.session_id == "test-123"
        assert req.command == "ls -la"
        assert req.workdir == "/workspace/test-123/subdir"
        assert req.env == {"FOO": "bar"}
        assert req.timeout == 60
        assert req.timestamp == 1234567890
        assert req.signature == "abc123"

    def test_parse_json_string(self):
        """Parse from JSON string."""
        json_str = '{"session_id": "test", "command": "pwd"}'
        req = parse_request(json_str)

        assert req.session_id == "test"
        assert req.command == "pwd"


class TestExecAgent:
    """Tests for ExecAgent."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent with temp workspace."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return ExecAgent(
            hmac_secret=None,  # No auth for tests
            workspace_root=str(workspace),
            default_timeout=10,
        )

    @pytest.fixture
    def agent_with_auth(self, tmp_path):
        """Create agent with HMAC auth."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return ExecAgent(
            hmac_secret="test-secret",
            workspace_root=str(workspace),
            default_timeout=10,
        )

    @pytest.mark.asyncio
    async def test_execute_simple(self, agent, tmp_path):
        """Execute simple command."""
        # Create session workspace
        session_dir = tmp_path / "workspace" / "test-session"
        session_dir.mkdir()

        req = ExecRequest(session_id="test-session", command="echo hello")
        resp = await agent.execute(req)

        assert resp.type == "exit"
        assert "hello" in resp.data
        assert resp.exit_code == 0
        assert resp.duration_ms is not None

    @pytest.mark.asyncio
    async def test_execute_with_env(self, agent, tmp_path):
        """Execute command with environment variables."""
        session_dir = tmp_path / "workspace" / "test-session"
        session_dir.mkdir()

        req = ExecRequest(
            session_id="test-session",
            command="echo $MY_VAR",
            env={"MY_VAR": "test-value"},
        )
        resp = await agent.execute(req)

        assert resp.type == "exit"
        assert "test-value" in resp.data

    @pytest.mark.asyncio
    async def test_execute_stderr(self, agent, tmp_path):
        """Execute command that writes to stderr."""
        session_dir = tmp_path / "workspace" / "test-session"
        session_dir.mkdir()

        req = ExecRequest(
            session_id="test-session", command="echo error >&2"
        )
        resp = await agent.execute(req)

        assert resp.type == "exit"
        assert "error" in resp.data

    @pytest.mark.asyncio
    async def test_execute_nonzero_exit(self, agent, tmp_path):
        """Execute command with non-zero exit code."""
        session_dir = tmp_path / "workspace" / "test-session"
        session_dir.mkdir()

        req = ExecRequest(session_id="test-session", command="exit 42")
        resp = await agent.execute(req)

        assert resp.type == "exit"
        assert resp.exit_code == 42

    @pytest.mark.asyncio
    async def test_execute_workspace_not_found(self, agent):
        """Execute with missing workspace."""
        req = ExecRequest(session_id="nonexistent", command="echo hello")
        resp = await agent.execute(req)

        assert resp.type == "error"
        assert "not found" in resp.data.lower()

    @pytest.mark.asyncio
    async def test_execute_timeout(self, agent, tmp_path):
        """Execute command that times out."""
        session_dir = tmp_path / "workspace" / "test-session"
        session_dir.mkdir()

        req = ExecRequest(
            session_id="test-session", command="sleep 60", timeout=1
        )
        resp = await agent.execute(req)

        assert resp.type == "error"
        assert "timeout" in resp.data.lower()

    def test_verify_signature_valid(self, agent_with_auth):
        """Verify valid signature."""
        timestamp = int(time.time())
        message = f"test-session:echo hello:{timestamp}"
        signature = hmac.new(
            b"test-secret", message.encode(), hashlib.sha256
        ).hexdigest()

        req = ExecRequest(
            session_id="test-session",
            command="echo hello",
            timestamp=timestamp,
            signature=signature,
        )

        assert agent_with_auth._verify_signature(req) is True

    def test_verify_signature_invalid(self, agent_with_auth):
        """Reject invalid signature."""
        req = ExecRequest(
            session_id="test-session",
            command="echo hello",
            timestamp=int(time.time()),
            signature="invalid",
        )

        with pytest.raises(AuthenticationError):
            agent_with_auth._verify_signature(req)

    def test_verify_signature_expired(self, agent_with_auth):
        """Reject expired timestamp."""
        old_timestamp = int(time.time()) - 120  # 2 minutes old
        message = f"test-session:echo hello:{old_timestamp}"
        signature = hmac.new(
            b"test-secret", message.encode(), hashlib.sha256
        ).hexdigest()

        req = ExecRequest(
            session_id="test-session",
            command="echo hello",
            timestamp=old_timestamp,
            signature=signature,
        )

        with pytest.raises(AuthenticationError):
            agent_with_auth._verify_signature(req)
