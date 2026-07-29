"""Combined controls for the Houdini RPC listener and external MCP gateway."""

from __future__ import annotations

from typing import Any

from .gateway import get_gateway_status, start_gateway, stop_gateway
from .remote import (
    get_hrpyc_status,
    is_hrpyc_running,
    start_hrpyc_server,
    stop_hrpyc_server,
)


def start_all_services(port: int = 18811) -> dict[str, Any]:
    """Start the Houdini listener and external gateway as one operation."""
    required_host = "127.0.0.1"
    remote_was_running = is_hrpyc_running()
    if remote_was_running:
        remote = get_hrpyc_status()
    else:
        remote = start_hrpyc_server(host=required_host, port=port)
        if remote.get("status") == "error":
            return {"status": "error", "remote": remote, "gateway": {"running": False}}

    houdini_host = remote.get("host") or required_host
    houdini_port = remote.get("bound_port", remote.get("port", port))
    if houdini_host != required_host or houdini_port != port:
        if not remote_was_running:
            try:
                stop_hrpyc_server()
            except Exception:
                pass
        return {
            "status": "error",
            "remote": remote,
            "gateway": {
                "status": "error",
                "running": False,
                "message": (
                    f"Start All requires the Houdini listener at {required_host}:{port}; "
                    f"found {houdini_host}:{houdini_port}. Stop it first or use the "
                    "individual controls."
                ),
            },
        }
    try:
        gateway = start_gateway(houdini_host=houdini_host, houdini_port=houdini_port)
    except Exception as exc:  # noqa: BLE001 - preserve rollback on launcher failures
        gateway = {"status": "error", "running": False, "message": str(exc)}
    if gateway.get("status") == "error":
        if not remote_was_running:
            try:
                stop_hrpyc_server()
            except Exception:
                pass
        return {"status": "error", "remote": remote, "gateway": gateway}

    return {"status": "success", "remote": remote, "gateway": gateway}


def stop_all_services() -> dict[str, Any]:
    """Attempt to stop both services even if one stop operation fails."""
    try:
        gateway = stop_gateway()
    except Exception as exc:  # noqa: BLE001 - listener stop must still be attempted
        gateway = {"status": "error", "running": True, "message": str(exc)}
    try:
        remote = stop_hrpyc_server()
    except Exception as exc:  # noqa: BLE001 - return both stop outcomes
        remote = {"status": "error", "running": True, "message": str(exc)}
    ok = gateway.get("status") in {"success", "already_stopped"} and remote.get(
        "status"
    ) in {"success", "already_stopped", "not_running"}
    return {"status": "success" if ok else "error", "remote": remote, "gateway": gateway}


def get_all_services_status() -> dict[str, Any]:
    """Return the independent state of both required services."""
    gateway = get_gateway_status()
    remote = get_hrpyc_status()
    return {
        "running": bool(gateway.get("running") and remote.get("running")),
        "remote": remote,
        "gateway": gateway,
    }
