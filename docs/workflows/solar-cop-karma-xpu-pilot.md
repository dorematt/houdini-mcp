# Solaris, Copernicus, and Karma XPU pilot

## Purpose

This live Houdini 22.0.368 pilot validates the workflow for importing SOP
geometry into USD, creating a Copernicus ground texture, binding a MaterialX
shader to a USD ground prim, and rendering with Karma XPU.

## Validated network

```text
/obj/mcp_forest_scene
  OUT_DECORATIONS = tree_normals + rock_normals
  ground_to_xz -> ground_uvs (UV Texture, Orthographic/Y, vertex uv, scale 4)
    -> terrain_undulation -> ground_normals

/stage/mcp_solaris_pilot
  import_forest (OUT_DECORATIONS, /World/Forest)
  import_ground (ground_normals, /World/Forest/Ground)
  key_sun -> forest_camera -> ground_material_library -> texture_eval_camera
  -> karma_xpu_settings -> render_karma_xpu

/img/mcp_ground_texture
  Layer (1024x1024) -> high-frequency Fractal Noise -> Height to Normal -> OUT_NORMAL
                         -> Mono to RGB ----------------------------+\
  Layer -> macro Fractal Noise -> Mono to RGB (dirt/grass) ----------> Blend -> OUT_ALBEDO
                              -> Mono to RGB (roughness) -------------------> OUT_ROUGHNESS

ground_material_library
  MaterialX shader-builder subnet (Material Flag)
    MtlX Image nodes read OUT_ALBEDO, OUT_NORMAL, and OUT_ROUGHNESS through op:
  Material Library matnode = *
```

The ground mesh is `/World/Forest/Ground/mesh_0`. Its
`material:binding` target is `/materials/mcp_ground`. The Material Library LOP
contains an `mtlxstandard_surface`, two `mtlximage` nodes, an
`mtlxnormalmap`, and an `mtlxsurfacematerial` output. Karma XPU rendered the
result at 640x360 with 16 primary samples. The `op:`-driven MaterialX graph
also rendered successfully with Karma XPU. The ground has a vertex `uv` SOP
attribute, inserted before `terrain_undulation`; SOP Import translates this to
face-varying `primvars:st` on the USD mesh. For this flat ground, UV Texture
uses Orthographic projection along Y with a scale of `(4, 4, 4)`; no MtlX
Place2D is needed.

The macro branch uses an independent low-frequency Fractal Noise to create a
subtle dirt/grass color blend and a correlated roughness map. `OUT_ROUGHNESS`
feeds the Standard Surface Specular Roughness input through a float MtlX Image.
The high-frequency Height to Normal scale is `0.5`; the MaterialX Normalmap
scale is `0.1`. A dedicated `/World/Cameras/texture_eval_camera` gives a
repeatable, closer Karma XPU material evaluation render.

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
- Use the SOP UV projection's scale for a simple flat surface. In this pilot,
  `ground_uvs` uses UV Texture's Orthographic projection along Y, writes vertex
  `uv`, and sits before `terrain_undulation`; SOP Import authors it as
  face-varying `primvars:st`. Rows & Columns is wrong here because it assigns a
  UV tile per grid quad. Reserve MtlX Place2D for a genuine downstream
  coordinate transform after confirming a valid texture-coordinate primvar.
  Set the normal image signature to `vector3` before connecting it to
  `mtlxnormalmap`.
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
   artifacts only when an external file is actually required. It should support
   an optional macro albedo/roughness branch with `OUT_ROUGHNESS`.
3. `create_materialx_texture_material`: author a MaterialX surface from
   texture paths (including `op:` COP sources) inside a MaterialX builder,
   verify a texture-coordinate primvar, and bind it to an explicit USD prim
   pattern.
4. `ensure_usd_texture_coordinates` (candidate): verify an imported mesh has
   the requested USD texture-coordinate primvar. Optionally insert a named UV
   Texture SOP directly before a specified deformation node, then verify the
   resulting USD `primvars:st`.
5. `capture_cop_output` (candidate): drive a Compositor Viewer to a named COP
   Null output and capture the actual image. Existing pane screenshots use a
   desktop-region grab and can return unrelated pixels even when the viewer is
   correctly bound to the COP node.
6. `create_texture_evaluation_camera` (candidate): create a separately named
   LOP camera from a source camera's framing, select it in Karma Render
   Settings, and render a non-overwriting close material-evaluation artifact.

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
- [UV Texture SOP](https://www.sidefx.com/docs/houdini/nodes/sop/texture.html)
- [MtlX Place2D](https://www.sidefx.com/docs/houdini/nodes/vop/mtlxplace2d.html)
- [MtlX Image](https://www.sidefx.com/docs/houdini/nodes/vop/mtlximage.html)
- [Karma XPU](https://www.sidefx.com/docs/houdini/solaris/karma_xpu.html)
