# Houdini MCP agent guide

## Scope

This repository is a Python FastMCP server that controls a live Houdini
session through `hou`/RPyC. Keep Houdini semantics and the MCP gateway in
Python; see [ADR 0001](docs/adr/0001-language-and-process-boundaries.md)
before proposing structural changes.

## Houdini knowledge

Before implementing or changing Houdini-specific behaviour, consult the
relevant SideFX documentation:

- [Houdini documentation](https://www.sidefx.com/docs/houdini/)
- [Houdini Object Model (HOM) reference](https://www.sidefx.com/docs/houdini/hom/hou/index.html)

Prefer the `get_houdini_help` MCP tool for targeted node and HOM lookups. Use
the installed Houdini session to verify node type names, parameter names,
menus, input labels, cook errors, and authored USD before encoding them in a
helper. Document durable workflow discoveries under `docs/workflows/`.

## Live-scene work

- Inspect first; do not overwrite existing nodes or scenes.
- Put experimental nodes in clearly named `mcp_*` networks.
- Verify LOP results through the USD stage and `errors()`/`warnings()`; LOP
  nodes do not use the SOP-style `error()` API.
- Build MaterialX shaders inside a MaterialX shader-builder subnet with its
  Material Flag set. Keep Material Library `matnode` at `*` when that subnet is
  the intended export boundary; do not place MtlX VOPs directly in the Material
  Library.
- Before wiring MtlX Image texture placement, verify the target USD prim has
  the required texture-coordinate primvar (normally `primvars:st`). A COP
  texture or a Place2D VOP does not create missing geometry UVs. When creating
  UVs for a deformed surface, place the named SOP UV-generation node upstream
  of the deformation and verify SOP `uv` translates to USD `primvars:st`. Pick
  the projection for the geometry: Rows & Columns repeats per grid quad, while
  a flat terrain should normally use Orthographic projection on its normal axis.
- Do not treat generic pane screenshots as proof of a COP image. Verify that a
  Compositor Viewer is bound to the requested Null output and, until a direct
  COP-output capture helper exists, distinguish a UI screenshot from the image
  data itself.
- Treat rendering and file output as external side effects: use a small
  resolution first and verify the output artifact before reporting success.

## Development

- Follow the existing focused module layout in `houdini_mcp/tools/` and
  register public tools in `houdini_mcp/server.py`.
- Add focused unit tests before implementation and run the relevant test file,
  then the full non-integration test suite and Ruff before committing.
- Keep wrappers narrow. Promote a workflow to a dedicated tool only after it
  has been validated in a live Houdini session and has clear, stable inputs.
- Work on a `codex/` feature branch. Commit and push completed work to the
  configured fork.
