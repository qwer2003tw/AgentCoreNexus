"""Tests for sandbox module."""

import os

import pytest

from src.sandbox import Sandbox, SandboxConfig, SandboxError


class TestSandbox:
    """Tests for Sandbox allocator."""

    @pytest.fixture
    def sandbox(self, tmp_path):
        """Create sandbox with temp workspace."""
        config = SandboxConfig(
            workspace_root=str(tmp_path / "workspace"),
            efs_mount=str(tmp_path / "efs"),
        )
        return Sandbox(config)

    def test_create_workspace(self, sandbox):
        """Create new workspace."""
        path = sandbox.create("test-session-1")

        assert os.path.exists(path)
        assert os.path.isdir(path)
        assert "test-session-1" in path

    def test_create_workspace_already_exists(self, sandbox):
        """Create workspace that already exists."""
        sandbox.create("test-session-1")
        path = sandbox.create("test-session-1")  # Should not raise

        assert os.path.exists(path)

    def test_create_workspace_permissions(self, sandbox):
        """Verify workspace permissions."""
        path = sandbox.create("test-session-1")

        # Check permissions (0o700 = owner only)
        mode = os.stat(path).st_mode & 0o777
        assert mode == 0o700

    def test_destroy_workspace(self, sandbox):
        """Destroy existing workspace."""
        path = sandbox.create("test-session-1")

        # Create a file in workspace
        with open(os.path.join(path, "test.txt"), "w") as f:
            f.write("test")

        sandbox.destroy("test-session-1")

        assert not os.path.exists(path)

    def test_destroy_nonexistent(self, sandbox):
        """Destroy non-existent workspace (should not raise)."""
        sandbox.destroy("nonexistent")  # Should not raise

    def test_exists(self, sandbox):
        """Check workspace existence."""
        assert not sandbox.exists("test-session-1")

        sandbox.create("test-session-1")

        assert sandbox.exists("test-session-1")

    def test_get_path(self, sandbox):
        """Get path to existing workspace."""
        assert sandbox.get_path("test-session-1") is None

        sandbox.create("test-session-1")
        path = sandbox.get_path("test-session-1")

        assert path is not None
        assert "test-session-1" in path

    def test_list_sessions(self, sandbox):
        """List all sessions."""
        assert sandbox.list_sessions() == []

        sandbox.create("session-a")
        sandbox.create("session-b")
        sandbox.create("session-c")

        sessions = sandbox.list_sessions()
        assert len(sessions) == 3
        assert "session-a" in sessions
        assert "session-b" in sessions
        assert "session-c" in sessions

    def test_cleanup_stale(self, sandbox):
        """Cleanup stale workspaces."""
        sandbox.create("session-active")
        sandbox.create("session-stale-1")
        sandbox.create("session-stale-2")

        cleaned = sandbox.cleanup_stale({"session-active"})

        assert cleaned == 2
        assert sandbox.exists("session-active")
        assert not sandbox.exists("session-stale-1")
        assert not sandbox.exists("session-stale-2")

    def test_invalid_session_id(self, sandbox):
        """Reject invalid session IDs."""
        with pytest.raises(SandboxError):
            sandbox.create("../../../etc/passwd")

        with pytest.raises(SandboxError):
            sandbox.create("")

    def test_isolation(self, sandbox):
        """Verify session isolation."""
        path_a = sandbox.create("session-a")
        path_b = sandbox.create("session-b")

        # Write file in session A
        with open(os.path.join(path_a, "secret.txt"), "w") as f:
            f.write("session A secret")

        # Session B should not see session A's file
        assert not os.path.exists(os.path.join(path_b, "secret.txt"))

        # Each session has its own directory
        assert path_a != path_b
        assert "session-a" in path_a
        assert "session-b" in path_b
