"""Combined Houdini listener and external gateway lifecycle tests."""

import houdini_mcp_plugin.combined as combined


def test_start_all_starts_both_components(monkeypatch):
    gateway_calls = []
    remote_calls = []
    monkeypatch.setattr(combined, "is_hrpyc_running", lambda: False)
    monkeypatch.setattr(
        combined,
        "start_hrpyc_server",
        lambda **kwargs: remote_calls.append(kwargs)
        or {
            "status": "success",
            "host": kwargs["host"],
            "bound_port": kwargs["port"],
        },
    )
    monkeypatch.setattr(
        combined,
        "start_gateway",
        lambda **kwargs: gateway_calls.append(kwargs) or {"status": "success"},
    )

    result = combined.start_all_services(port=18811)

    assert result["status"] == "success"
    assert result["remote"]["bound_port"] == 18811
    assert result["gateway"]["status"] == "success"
    assert remote_calls == [{"host": "127.0.0.1", "port": 18811}]
    assert gateway_calls == [{"houdini_host": "127.0.0.1", "houdini_port": 18811}]


def test_start_all_rolls_back_new_listener_when_gateway_fails(monkeypatch):
    stopped = []
    monkeypatch.setattr(combined, "is_hrpyc_running", lambda: False)
    monkeypatch.setattr(
        combined,
        "start_hrpyc_server",
        lambda port, host=None: {"status": "success", "host": host, "port": port},
    )
    monkeypatch.setattr(
        combined,
        "start_gateway",
        lambda **_kwargs: {"status": "error", "message": "gateway failed"},
    )
    monkeypatch.setattr(
        combined,
        "stop_hrpyc_server",
        lambda: stopped.append(True) or {"status": "success"},
    )

    result = combined.start_all_services()

    assert result["status"] == "error"
    assert stopped == [True]


def test_start_all_preserves_preexisting_listener_on_gateway_failure(monkeypatch):
    stopped = []
    monkeypatch.setattr(combined, "is_hrpyc_running", lambda: True)
    monkeypatch.setattr(combined, "get_hrpyc_status", lambda: {"running": True})
    monkeypatch.setattr(
        combined,
        "start_gateway",
        lambda **_kwargs: {"status": "error", "message": "gateway failed"},
    )
    monkeypatch.setattr(combined, "stop_hrpyc_server", lambda: stopped.append(True))

    result = combined.start_all_services()

    assert result["status"] == "error"
    assert stopped == []


def test_start_all_rejects_preexisting_non_loopback_listener(monkeypatch):
    gateway_calls = []
    monkeypatch.setattr(combined, "is_hrpyc_running", lambda: True)
    monkeypatch.setattr(
        combined,
        "get_hrpyc_status",
        lambda: {"running": True, "host": "0.0.0.0", "bound_port": 18811},
    )
    monkeypatch.setattr(
        combined,
        "start_gateway",
        lambda **kwargs: gateway_calls.append(kwargs) or {"status": "success"},
    )

    result = combined.start_all_services()

    assert result["status"] == "error"
    assert "127.0.0.1:18811" in result["gateway"]["message"]
    assert gateway_calls == []


def test_start_all_rolls_back_new_listener_when_gateway_raises(monkeypatch):
    stopped = []
    monkeypatch.setattr(combined, "is_hrpyc_running", lambda: False)
    monkeypatch.setattr(
        combined,
        "start_hrpyc_server",
        lambda port, host=None: {"status": "success", "host": host, "bound_port": port},
    )
    monkeypatch.setattr(
        combined,
        "start_gateway",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("gateway crashed")),
    )
    monkeypatch.setattr(
        combined,
        "stop_hrpyc_server",
        lambda: stopped.append(True) or {"status": "success"},
    )

    result = combined.start_all_services()

    assert result["status"] == "error"
    assert result["gateway"]["message"] == "gateway crashed"
    assert stopped == [True]


def test_stop_all_attempts_both_components(monkeypatch):
    calls = []
    monkeypatch.setattr(
        combined,
        "stop_gateway",
        lambda: calls.append("gateway") or {"status": "success"},
    )
    monkeypatch.setattr(
        combined,
        "stop_hrpyc_server",
        lambda: calls.append("remote") or {"status": "success"},
    )

    result = combined.stop_all_services()

    assert calls == ["gateway", "remote"]
    assert result["status"] == "success"


def test_stop_all_is_idempotent(monkeypatch):
    monkeypatch.setattr(
        combined,
        "stop_gateway",
        lambda: {"status": "already_stopped", "running": False},
    )
    monkeypatch.setattr(
        combined,
        "stop_hrpyc_server",
        lambda: {"status": "not_running", "running": False},
    )

    result = combined.stop_all_services()

    assert result["status"] == "success"


def test_stop_all_attempts_listener_when_gateway_stop_raises(monkeypatch):
    calls = []
    monkeypatch.setattr(
        combined,
        "stop_gateway",
        lambda: (_ for _ in ()).throw(RuntimeError("gateway stop crashed")),
    )
    monkeypatch.setattr(
        combined,
        "stop_hrpyc_server",
        lambda: calls.append("remote") or {"status": "success"},
    )

    result = combined.stop_all_services()

    assert calls == ["remote"]
    assert result["status"] == "error"
    assert result["gateway"]["message"] == "gateway stop crashed"


def test_all_status_reports_each_component(monkeypatch):
    monkeypatch.setattr(combined, "get_gateway_status", lambda: {"running": True})
    monkeypatch.setattr(combined, "get_hrpyc_status", lambda: {"running": False})

    result = combined.get_all_services_status()

    assert result["running"] is False
    assert result["gateway"]["running"] is True
    assert result["remote"]["running"] is False
