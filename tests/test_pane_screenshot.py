"""Tests for Houdini pane screenshot Qt compatibility."""

import pytest

import houdini_mcp.tools.pane_screenshot as pane_screenshot
from houdini_mcp.tools.pane_screenshot import _get_qt_modules


class FakeModules:
    def __init__(self, available):
        self.available = available

    def __getitem__(self, name):
        if name not in self.available:
            raise ModuleNotFoundError(name)
        return self.available[name]


def test_get_qt_modules_uses_pyside6_when_pyside2_is_unavailable():
    qt_modules = {
        "PySide6.QtWidgets": object(),
        "PySide6.QtCore": object(),
        "PySide6.QtGui": object(),
    }
    hou = type("FakeHou", (), {})()
    hou.____conn__ = type("FakeConnection", (), {"modules": FakeModules(qt_modules)})()

    assert _get_qt_modules(hou) == (
        qt_modules["PySide6.QtWidgets"],
        qt_modules["PySide6.QtCore"],
        qt_modules["PySide6.QtGui"],
    )


def test_get_qt_modules_falls_back_to_pyside2():
    qt_modules = {
        "PySide2.QtWidgets": object(),
        "PySide2.QtCore": object(),
        "PySide2.QtGui": object(),
    }
    hou = type("FakeHou", (), {})()
    hou.____conn__ = type("FakeConnection", (), {"modules": FakeModules(qt_modules)})()

    assert _get_qt_modules(hou) == (
        qt_modules["PySide2.QtWidgets"],
        qt_modules["PySide2.QtCore"],
        qt_modules["PySide2.QtGui"],
    )


def test_get_qt_modules_preserves_transport_errors():
    class BrokenModules:
        def __getitem__(self, _name):
            raise EOFError("connection closed")

    hou = type("FakeHou", (), {})()
    hou.____conn__ = type("FakeConnection", (), {"modules": BrokenModules()})()

    with pytest.raises(EOFError, match="connection closed"):
        _get_qt_modules(hou)


def test_capture_pane_reports_transport_failure_as_connection_error(monkeypatch):
    monkeypatch.setattr(pane_screenshot, "ensure_connected", lambda *_args: object())
    monkeypatch.setattr(
        pane_screenshot,
        "_get_qt_modules",
        lambda _hou: (_ for _ in ()).throw(EOFError("connection closed")),
    )

    result = pane_screenshot.capture_pane_screenshot()

    assert result["error_type"] == "connection_error"
    assert result["exception"] == "EOFError"
