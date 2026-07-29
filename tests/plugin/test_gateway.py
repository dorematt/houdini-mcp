"""External MCP gateway lifecycle tests."""

from pathlib import Path

import houdini_mcp_plugin.gateway as gateway
import pytest


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.killed = False

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.killed = True


class FakeHealthResponse:
    def __init__(self, payload):
        self.status = 200
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


@pytest.fixture(autouse=True)
def _reset_gateway_state():
    gateway._gateway_process = None
    yield
    gateway._gateway_process = None


def test_start_gateway_uses_repo_venv_and_loopback(monkeypatch, tmp_path):
    python = tmp_path / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    calls = []
    process = FakeProcess()

    monkeypatch.setenv("HOUDINI_MCP_GATEWAY_ROOT", str(tmp_path))
    monkeypatch.setenv("PYTHONHOME", "C:/Program Files/Side Effects Software/Houdini/python313")
    monkeypatch.setenv("PYTHONPATH", "C:/Program Files/Side Effects Software/Houdini/python313/lib")
    monkeypatch.setattr(gateway, "is_gateway_running", lambda: False)
    monkeypatch.setattr(gateway, "_wait_for_gateway", lambda _running, _timeout: True)
    monkeypatch.setattr(
        gateway.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append((args, kwargs)) or process,
    )

    result = gateway.start_gateway()

    assert result["status"] == "success"
    assert calls[0][0][0] == [str(python), "-m", "houdini_mcp"]
    assert calls[0][1]["cwd"] == str(tmp_path)
    assert calls[0][1]["env"]["MCP_HOST"] == "127.0.0.1"
    assert calls[0][1]["env"]["MCP_PORT"] == "3055"
    assert "PYTHONHOME" not in calls[0][1]["env"]
    assert "PYTHONPATH" not in calls[0][1]["env"]
    assert gateway._gateway_process is process


def test_gateway_health_rejects_unrelated_http_service(monkeypatch):
    monkeypatch.setattr(
        gateway.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeHealthResponse(b'{"status":"healthy","service":"other"}'),
    )

    assert gateway.is_gateway_running() is False


def test_gateway_health_accepts_houdini_mcp_service(monkeypatch):
    monkeypatch.setattr(
        gateway.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeHealthResponse(
            b'{"status":"healthy","service":"houdini-mcp"}'
        ),
    )

    assert gateway.is_gateway_running() is True


def test_start_gateway_reports_missing_root(monkeypatch):
    monkeypatch.delenv("HOUDINI_MCP_GATEWAY_ROOT", raising=False)
    monkeypatch.setattr(gateway, "is_gateway_running", lambda: False)

    result = gateway.start_gateway()

    assert result["status"] == "error"
    assert "HOUDINI_MCP_GATEWAY_ROOT" in result["message"]


def test_start_gateway_reports_missing_python(monkeypatch, tmp_path):
    monkeypatch.setenv("HOUDINI_MCP_GATEWAY_ROOT", str(tmp_path))
    monkeypatch.setattr(gateway, "is_gateway_running", lambda: False)

    result = gateway.start_gateway()

    assert result["status"] == "error"
    assert str(Path(".venv") / "Scripts" / "python.exe") in result["message"]


def test_stop_gateway_terminates_owned_process(monkeypatch):
    process = FakeProcess()
    gateway._gateway_process = process
    monkeypatch.setattr(gateway, "_wait_for_gateway", lambda _running, _timeout: True)

    result = gateway.stop_gateway()

    assert result["status"] == "success"
    assert process.terminated is True
    assert gateway._gateway_process is None


def test_stop_gateway_refuses_unmanaged_process(monkeypatch):
    monkeypatch.setattr(gateway, "is_gateway_running", lambda: True)

    result = gateway.stop_gateway()

    assert result["status"] == "error"
    assert "not started by this Houdini session" in result["message"]
