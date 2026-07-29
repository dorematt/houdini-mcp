"""Shelf definition tests."""

import xml.etree.ElementTree as ET
from pathlib import Path


def test_combined_service_tools_use_requested_icons():
    shelf_path = (
        Path(__file__).parents[2]
        / "houdini_plugin"
        / "toolbar"
        / "houdini_mcp.shelf"
    )
    root = ET.parse(shelf_path).getroot()
    tools = {tool.attrib["name"]: tool for tool in root.findall("tool")}

    assert tools["all_start"].attrib == {
        "name": "all_start",
        "label": "Start All",
        "icon": "hicon:/SVGIcons.index?TOP_commandserver.svg",
    }
    assert tools["all_stop"].attrib == {
        "name": "all_stop",
        "label": "Stop All",
        "icon": "hicon:/SVGIcons.index?TOP_commandserverend.svg",
    }
    assert tools["all_status"].attrib["label"] == "All Status"


def test_existing_shelf_tools_are_preserved():
    shelf_path = (
        Path(__file__).parents[2]
        / "houdini_plugin"
        / "toolbar"
        / "houdini_mcp.shelf"
    )
    root = ET.parse(shelf_path).getroot()
    members = [member.attrib["name"] for member in root.find("toolshelf")]

    assert {"mcp_start", "mcp_stop", "mcp_status"}.issubset(members)
    assert {"hrpyc_start", "hrpyc_stop", "hrpyc_status", "hrpyc_selftest"}.issubset(
        members
    )
    assert {"all_start", "all_stop", "all_status"}.issubset(members)
