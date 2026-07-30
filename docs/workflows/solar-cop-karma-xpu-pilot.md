# Solaris, Copernicus, and Karma XPU pilot

## Purpose

This live Houdini 22.0.368 pilot validates the workflow for importing SOP
geometry into USD, creating a Copernicus ground texture, binding a MaterialX
shader to a USD ground prim, and rendering with Karma XPU.

## Validated network

```text
/obj/mcp_forest_scene
  OUT_DECORATIONS = tree_normals + rock_normals
  ground_normals

/stage/mcp_solaris_pilot
  import_forest (OUT_DECORATIONS, /World/Forest)
  import_ground (ground_normals, /World/Forest/Ground)
  key_sun -> forest_camera -> ground_material_library
  -> karma_xpu_settings -> render_karma_xpu

/img/mcp_ground_texture
  Layer (1024x1024) -> Fractal Noise -> Height to Normal -> OUT_NORMAL
                         -> Mono to RGB -> OUT_ALBEDO

ground_material_library
  MaterialX shader-builder subnet (Material Flag)
    MtlX Image nodes read op:/img/mcp_ground_texture/OUT_ALBEDO and OUT_NORMAL
  Material Library matnode = *
```

The ground mesh is `/World/Forest/Ground/mesh_0`. Its
`material:binding` target is `/materials/mcp_ground`. The Material Library LOP
contains an `mtlxstandard_surface`, two `mtlximage` nodes, an
`mtlxnormalmap`, and an `mtlxsurfacematerial` output. Karma XPU rendered the
result at 640x360 with 16 primary samples. The `op:`-driven MaterialX graph
also rendered successfully with Karma XPU. The ground currently has no UV
primvar, so the graph must not use MtlX Place2D until the geometry has an
explicit texture-coordinate source.

## Important Houdini 22 behaviour

- SOP Import uses `enable_pathprefix` and `pathprefix` for ordinary geometry
  imports. Its `primpath` parameter does not establish the resulting mesh
  path in this mode.
- `hou.LopNode` exposes `errors()` and `warnings()`, not `error()`.
- USD light attributes can have encoded instantiated parameter names. For
  example, the Distant Light intensity parameter was
  `xn__inputsintensity_i0a`, despite the template label being `Intensity`.
  Helpers should resolve supported controls deliberately instead of assuming
  a display label is a parameter name.
- Karma Render Settings needs `res_mode="manual"` before a manually selected
  height can be changed. The Karma ROP also needs `soho_foreground=True` when
  callers must wait for and verify a render artifact.
- `/img` is a `CopNet` container; create a `copnet` inside it before creating
  Copernicus (`Cop`) nodes. It does not accept a generic `subnet`.
- `Mono to RGB` takes the mono texture on its `source` input. Do not reuse a
  generic Ramp COP with the same name: its inputs have a different meaning.
- A merged SOP result becomes one USD mesh. To bind a material only to ground,
  import ground and decorations as separate USD prims before binding.
- Use named Null COPs such as `OUT_ALBEDO` and `OUT_NORMAL` as stable network
  contracts. Point `mtlximage` at their `op:` paths to avoid writing an
  Apprentice-watermarked texture to disk and then reading it back. The final
  Apprentice render still carries its normal render watermark.
- Feed both image nodes from a shared `mtlxplace2d`. Its scale divides UVs, so
  `(4, 4)` makes the texture appear four times larger without increasing the
  Copernicus resolution. This requires a valid `primvars:st` (or an explicit
  replacement) on the USD mesh. The pilot ground has no `uv` attribute in SOPs
  and no `primvars:st` in USD, so Place2D has no valid sampling coordinate
  instead of providing a safe scaling control. Set the normal image signature to `vector3`
  before connecting it to `mtlxnormalmap`.
- Build MaterialX shaders inside a MaterialX shader-builder subnet with its
  Material Flag set. Put the individual MtlX nodes inside that subnet and let
  the Material Library's `matnode` stay `*`; this exports the intended material
  boundary without promoting every internal shader node.

## Candidate MCP helpers

The pilot identifies three narrow, high-value helpers:

1. `import_sop_to_usd`: import a specific SOP output under an explicit USD
   root path and verify the authored prim.
2. `create_cop_texture_set`: build a named Copernicus texture network with
   explicit resolution and named Null output contracts; optionally write
   artifacts only when an external file is actually required.
3. `create_materialx_texture_material`: author a MaterialX surface from
   texture paths (including `op:` COP sources) inside a MaterialX builder,
   verify a texture-coordinate primvar before adding placement, and bind it to
   an explicit USD prim pattern.
4. `ensure_usd_texture_coordinates` (candidate): verify an imported mesh has
   the requested USD texture-coordinate primvar and provide an actionable
   result when a preceding SOP UV-generation step is needed.

Do not combine these into one opaque scene-generator tool. Each has a stable
boundary, can be independently tested, and lets an agent inspect or edit the
result between stages.

## Sources

- [SOP Import](https://www.sidefx.com/docs/houdini/nodes/lop/sopimport.html)
- [Material Library](https://www.sidefx.com/docs/houdini/nodes/lop/materiallibrary.html)
- [Assign Material](https://www.sidefx.com/docs/houdini/nodes/lop/assignmaterial.html)
- [Fractal Noise COP](https://www.sidefx.com/docs/houdini/nodes/cop/fractalnoise.html)
- [Mono to RGB COP](https://www.sidefx.com/docs/houdini/nodes/cop/monotorgb.html)
- [Working with Copernicus nodes](https://www.sidefx.com/docs/houdini/copernicus/working_with_cops.html)
- [MtlX Place2D](https://www.sidefx.com/docs/houdini/nodes/vop/mtlxplace2d.html)
- [MtlX Image](https://www.sidefx.com/docs/houdini/nodes/vop/mtlximage.html)
- [Karma XPU](https://www.sidefx.com/docs/houdini/solaris/karma_xpu.html)
