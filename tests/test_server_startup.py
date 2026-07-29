"""Server startup configuration tests."""

from houdini_mcp import server


def test_http_defaults_to_loopback(monkeypatch):
    calls = []
    monkeypatch.delenv("MCP_HOST", raising=False)
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))

    server.run_server(transport="http", port=3055)

    assert calls == [{"transport": "http", "host": "127.0.0.1", "port": 3055}]


def test_http_honors_explicit_bind_host(monkeypatch):
    calls = []
    monkeypatch.setenv("MCP_HOST", "100.64.0.10")
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))

    server.run_server(transport="http", port=3055)

    assert calls == [{"transport": "http", "host": "100.64.0.10", "port": 3055}]
