"""Tests for sandbox."""

import os
import pytest
from src.sandbox import Sandbox, SandboxConfig, SandboxError


class TestSandbox:
    @pytest.fixture
    def sandbox(self, tmp_path):
        return Sandbox(SandboxConfig(workspace_root=str(tmp_path / "ws")))

    def test_create(self, sandbox):
        path = sandbox.create("sess1")
        assert os.path.isdir(path)
        assert "sess1" in path

    def test_create_idempotent(self, sandbox):
        p1 = sandbox.create("sess1")
        p2 = sandbox.create("sess1")
        assert p1 == p2

    def test_permissions(self, sandbox):
        path = sandbox.create("sess1")
        assert (os.stat(path).st_mode & 0o777) == 0o700

    def test_destroy(self, sandbox):
        path = sandbox.create("sess1")
        open(os.path.join(path, "f.txt"), "w").write("x")
        sandbox.destroy("sess1")
        assert not os.path.exists(path)

    def test_destroy_nonexistent(self, sandbox):
        sandbox.destroy("nope")  # no error

    def test_exists(self, sandbox):
        assert not sandbox.exists("sess1")
        sandbox.create("sess1")
        assert sandbox.exists("sess1")

    def test_list_sessions(self, sandbox):
        sandbox.create("a")
        sandbox.create("b")
        assert set(sandbox.list_sessions()) == {"a", "b"}

    def test_cleanup_stale(self, sandbox):
        sandbox.create("active")
        sandbox.create("stale")
        cleaned = sandbox.cleanup_stale({"active"})
        assert cleaned == 1
        assert sandbox.exists("active")
        assert not sandbox.exists("stale")

    def test_invalid_session_id(self, sandbox):
        with pytest.raises(SandboxError):
            sandbox.create("../../../etc")
        with pytest.raises(SandboxError):
            sandbox.create("")

    def test_isolation(self, sandbox):
        pa = sandbox.create("a")
        pb = sandbox.create("b")
        open(os.path.join(pa, "secret"), "w").write("x")
        assert not os.path.exists(os.path.join(pb, "secret"))
