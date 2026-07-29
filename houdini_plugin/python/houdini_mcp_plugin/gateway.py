"""Lifecycle control for the external HTTP MCP gateway."""

from __future__ import annotations

import atexit
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 3055
GATEWAY_URL = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}"

_gateway_process: subprocess.Popen[Any] | None = None
_atexit_registered = False


def is_gateway_running() -> bool:
    """Return whether the external gateway health endpoint responds."""
    try:
        with urllib.request.urlopen(f"{GATEWAY_URL}/health", timeout=0.5) as response:
            payload = json.loads(response.read())
            return (
                response.status == 200
                and payload.get("status") == "healthy"
                and payload.get("service") == "houdini-mcp"
            )
    except Exception:
        return False


def _wait_for_gateway(running: bool, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() <= deadline:
        if is_gateway_running() is running:
            return True
        time.sleep(0.1)
    return False


def _gateway_python(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def start_gateway(
    timeout: float = 10.0,
    *,
    houdini_host: str = "127.0.0.1",
    houdini_port: int = 18811,
) -> dict[str, Any]:
    """Start the configured external gateway if it is not already healthy."""
    global _atexit_registered, _gateway_process

    if is_gateway_running():
        return {
            "status": "already_running",
            "running": True,
            "managed": _gateway_process is not None,
            "endpoint": f"{GATEWAY_URL}/mcp",
        }

    root_value = os.getenv("HOUDINI_MCP_GATEWAY_ROOT", "").strip()
    if not root_value:
        return {
            "status": "error",
            "running": False,
            "message": "HOUDINI_MCP_GATEWAY_ROOT is not configured.",
        }

    root = Path(root_value).expanduser().resolve()
    python = _gateway_python(root)
    if not python.is_file():
        return {
            "status": "error",
            "running": False,
            "message": f"Gateway Python was not found: {python}",
        }

    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "gateway.log"
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env.update(
        {
            "MCP_HOST": GATEWAY_HOST,
            "MCP_PORT": str(GATEWAY_PORT),
            "MCP_TRANSPORT": "http",
            "HOUDINI_HOST": houdini_host,
            "HOUDINI_PORT": str(houdini_port),
        }
    )

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        with log_path.open("a", encoding="utf-8") as log:
            _gateway_process = subprocess.Popen(
                [str(python), "-m", "houdini_mcp"],
                cwd=str(root),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                close_fds=True,
                creationflags=creationflags,
            )
    except OSError as exc:
        _gateway_process = None
        return {"status": "error", "running": False, "message": str(exc)}

    if not _wait_for_gateway(True, timeout):
        _terminate_owned_process()
        return {
            "status": "error",
            "running": False,
            "message": f"Gateway did not become healthy. Check {log_path}",
        }

    if not _atexit_registered:
        atexit.register(_stop_owned_gateway_at_exit)
        _atexit_registered = True

    return {
        "status": "success",
        "running": True,
        "managed": True,
        "endpoint": f"{GATEWAY_URL}/mcp",
        "log_path": str(log_path),
    }


def _terminate_owned_process() -> None:
    global _gateway_process
    process = _gateway_process
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
    _gateway_process = None


def stop_gateway(timeout: float = 5.0) -> dict[str, Any]:
    """Stop the gateway launched by this Houdini session."""
    if _gateway_process is None:
        if is_gateway_running():
            return {
                "status": "error",
                "running": True,
                "managed": False,
                "message": "Gateway is running but was not started by this Houdini session.",
            }
        return {"status": "already_stopped", "running": False, "managed": False}

    _terminate_owned_process()
    stopped = _wait_for_gateway(False, timeout)
    return {
        "status": "success" if stopped else "error",
        "running": not stopped,
        "managed": False,
        "message": "Gateway stopped." if stopped else "Gateway process stopped but port is still active.",
    }


def _stop_owned_gateway_at_exit() -> None:
    if _gateway_process is not None:
        _terminate_owned_process()


def get_gateway_status() -> dict[str, Any]:
    """Return gateway reachability and ownership state."""
    return {
        "running": is_gateway_running(),
        "managed": _gateway_process is not None and _gateway_process.poll() is None,
        "endpoint": f"{GATEWAY_URL}/mcp",
    }
