"""Houdini package layout tests."""

import json
from pathlib import Path


def test_package_root_points_to_sibling_plugin_directory():
    package_file = Path(__file__).parents[2] / "houdini_plugin" / "houdini_mcp.json"
    package = json.loads(package_file.read_text(encoding="utf-8"))

    assert package["env"][0]["HOUDINI_MCP_ROOT"] == (
        "$HOUDINI_PACKAGE_PATH/../houdini_mcp"
    )
