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
  Layer (1024x1024) -> Fractal Noise -> Height to Normal -> ROP Image
                         -> Mono to RGB -> ROP Image
```

The ground mesh is `/World/Forest/Ground/mesh_0`. Its
`material:binding` target is `/materials/mcp_ground`. The Material Library LOP
contains an `mtlxstandard_surface`, two `mtlximage` nodes, an
`mtlxnormalmap`, and an `mtlxsurfacematerial` output. Karma XPU rendered the
result at 640x360 with 16 primary samples.

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

## Candidate MCP helpers

The pilot identifies three narrow, high-value helpers:

1. `import_sop_to_usd`: import a specific SOP output under an explicit USD
   root path and verify the authored prim.
2. `create_cop_texture_set`: build a named Copernicus texture network with
   explicit resolution and write verified albedo/normal artifacts.
3. `create_materialx_texture_material`: author a MaterialX surface from
   texture paths and bind it to an explicit USD prim pattern.

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
- [Karma XPU](https://www.sidefx.com/docs/houdini/solaris/karma_xpu.html)
