import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from . import utils

BED_COLOR = (0.15, 0.5, 1.0)

_handle = None


def _bed_geometry(scene):
    props = scene.print3d_setup
    k = 1.0 / utils.mm_per_unit(scene)
    x = props.bed_x * k / 2
    y = props.bed_y * k / 2
    z = props.bed_z * k

    floor = [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0)]
    top = [(px, py, z) for px, py, _ in floor]

    outline = [floor[i] for e in ((0, 1), (1, 2), (2, 3), (3, 0)) for i in e]
    volume = ([top[i] for e in ((0, 1), (1, 2), (2, 3), (3, 0)) for i in e] +
              [p for i in range(4) for p in (floor[i], top[i])])
    cross = [(-x, 0, 0), (x, 0, 0), (0, -y, 0), (0, y, 0)]
    fill = [floor[0], floor[1], floor[2], floor[0], floor[2], floor[3]]
    return outline, volume, cross, fill


def _draw_lines(coords, width, alpha, region):
    shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": coords})
    shader.uniform_float("viewportSize", (region.width, region.height))
    shader.uniform_float("lineWidth", width)
    shader.uniform_float("color", (*BED_COLOR, alpha))
    batch.draw(shader)


def _draw_bed():
    context = bpy.context
    scene = context.scene
    props = getattr(scene, "print3d_setup", None)
    if props is None or not props.show_bed:
        return
    if not context.space_data.overlay.show_overlays:
        return

    outline, volume, cross, fill = _bed_geometry(scene)
    region = context.region

    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.depth_mask_set(False)

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {"pos": fill})
    shader.uniform_float("color", (*BED_COLOR, 0.06))
    batch.draw(shader)

    _draw_lines(volume, 1.0, 0.3, region)
    _draw_lines(cross, 1.0, 0.5, region)
    _draw_lines(outline, 2.5, 1.0, region)

    gpu.state.depth_mask_set(True)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


_overlay_shader = None


def overlay_shader():
    """Shader for per-vertex colored triangles drawn on top of an object's surface"""
    global _overlay_shader
    if _overlay_shader is not None:
        return _overlay_shader

    iface = gpu.types.GPUStageInterfaceInfo("print3d_overlay_iface")
    iface.flat('VEC3', "v_color")

    info = gpu.types.GPUShaderCreateInfo()
    info.push_constant('MAT4', "modelview")
    info.push_constant('MAT4', "proj")
    info.push_constant('FLOAT', "is_persp")
    info.push_constant('FLOAT', "bias")
    info.push_constant('FLOAT', "view_distance")
    info.vertex_in(0, 'VEC3', "pos")
    info.vertex_in(1, 'VEC3', "color")
    info.vertex_out(iface)
    info.fragment_out(0, 'VEC4', "frag_color")
    # Pull the overlay slightly toward the viewer so it wins the depth test against the object itself
    info.vertex_source(
        "void main() {"
        "  v_color = color;"
        "  vec4 v = modelview * vec4(pos, 1.0);"
        "  if (is_persp > 0.5) { v.xyz *= 1.0 - bias; } else { v.z += bias * 2.0 * view_distance; }"
        "  gl_Position = proj * v;"
        "}"
    )
    # Extra depth offset proportional to the surface slope, for faces seen at grazing angles
    info.depth_write('ANY')
    info.fragment_source(
        "void main() {"
        "  frag_color = vec4(v_color, 0.9);"
        "  gl_FragDepth = gl_FragCoord.z - 2.0 * fwidth(gl_FragCoord.z);"
        "}"
    )
    _overlay_shader = gpu.shader.create_from_info(info)
    return _overlay_shader


def draw_overlay(context, items, bias):
    """Draw (matrix_world, batch) pairs made with overlay_shader(). Higher bias draws on top"""
    if not items:
        return
    rv3d = context.region_data
    shader = overlay_shader()

    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.depth_mask_set(False)
    gpu.state.face_culling_set('BACK')

    shader.bind()
    proj = rv3d.window_matrix
    shader.uniform_float("proj", proj)
    shader.uniform_float("is_persp", 1.0 if proj[3][3] == 0.0 else 0.0)
    shader.uniform_float("bias", bias)
    shader.uniform_float("view_distance", rv3d.view_distance)
    for matrix_world, batch in items:
        shader.uniform_float("modelview", rv3d.view_matrix @ matrix_world)
        batch.draw(shader)

    gpu.state.face_culling_set('NONE')
    gpu.state.depth_mask_set(True)
    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def tag_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def register():
    global _handle
    _handle = bpy.types.SpaceView3D.draw_handler_add(_draw_bed, (), 'WINDOW', 'POST_VIEW')


def unregister():
    global _handle, _overlay_shader
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, 'WINDOW')
        _handle = None
    _overlay_shader = None
