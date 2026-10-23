"""Wall thickness map: ray casts inward from every face and draws the result as a colored overlay"""

import time

import bpy
import numpy as np
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import drawing, utils

# Categories, from thinnest to OK. Thresholds are multiples of the nozzle diameter.
RED, ORANGE, YELLOW, GREEN, GREY = range(5)
COLORS = np.array([
    (0.95, 0.10, 0.10),  # < 1 line: may not print at all
    (1.00, 0.50, 0.00),  # < 2 lines: fragile
    (1.00, 0.90, 0.10),  # < 3 lines: printable, not strong
    (0.20, 0.80, 0.30),  # >= 3 lines: OK
    (0.50, 0.50, 0.50),  # no reading (open mesh, flipped normals)
], dtype=np.float32)

# Results per object name
_results = {}
_handle = None


class _Result:
    def __init__(self, coords, tri_poly, thickness, areas, scale):
        self.coords = coords          # (T*3, 3) local triangle vertices
        self.tri_poly = tri_poly      # (T,) polygon index of each triangle
        self.thickness = thickness    # (P,) thickness in mm, inf = no reading
        self.areas = areas            # (P,) polygon areas, for percentages
        self.scale = scale            # object scale at analysis time
        self.stale = False
        self.batch = None
        self.batch_key = None


def categories(thickness, nozzle):
    cat = np.full(len(thickness), GREEN, dtype=np.int8)
    cat[thickness < nozzle * 3] = YELLOW
    cat[thickness < nozzle * 2] = ORANGE
    cat[thickness < nozzle] = RED
    cat[np.isinf(thickness)] = GREY
    return cat


def get_result(obj):
    """Result for obj, or None. A result is stale if the mesh or the scale changed"""
    result = _results.get(obj.name)
    if result is None:
        return None
    if (obj.matrix_world.to_scale() - result.scale).length > 1e-5:
        result.stale = True
    return result


def analyze(obj, depsgraph, scene):
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    if mesh is None:
        return None
    try:
        mesh.calc_loop_triangles()
        nv, np_, nt = len(mesh.vertices), len(mesh.polygons), len(mesh.loop_triangles)
        if nt == 0:
            return None
        co = np.empty(nv * 3, np.float64)
        mesh.vertices.foreach_get("co", co)
        co = co.reshape(nv, 3)
        tri_v = np.empty(nt * 3, np.int32)
        mesh.loop_triangles.foreach_get("vertices", tri_v)
        tri_v = tri_v.reshape(nt, 3)
        tri_poly = np.empty(nt, np.int32)
        mesh.loop_triangles.foreach_get("polygon_index", tri_poly)
        centers = np.empty(np_ * 3, np.float64)
        mesh.polygons.foreach_get("center", centers)
        normals = np.empty(np_ * 3, np.float64)
        mesh.polygons.foreach_get("normal", normals)
        areas = np.empty(np_, np.float32)
        mesh.polygons.foreach_get("area", areas)
    finally:
        obj_eval.to_mesh_clear()

    # Ray cast in world space so the object's scale counts
    m = np.array(obj_eval.matrix_world)
    rot = m[:3, :3]
    world = co @ rot.T + m[:3, 3]
    w_centers = centers.reshape(np_, 3) @ rot.T + m[:3, 3]
    w_normals = normals.reshape(np_, 3) @ np.linalg.inv(rot)
    lengths = np.linalg.norm(w_normals, axis=1)
    lengths[lengths == 0] = 1
    w_normals /= lengths[:, None]

    bvh = BVHTree.FromPolygons(world.tolist(), tri_v.tolist(), all_triangles=True)
    diag = float(np.linalg.norm(world.max(axis=0) - world.min(axis=0)))
    eps = max(diag * 1e-6, 1e-9)
    mm = utils.mm_per_unit(scene)

    thickness = np.full(np_, np.inf, np.float32)
    for i in range(np_):
        direction = Vector(-w_normals[i])
        start = Vector(w_centers[i])
        origin = start + direction * eps
        for _ in range(4):
            loc, normal, index, _dist = bvh.ray_cast(origin, direction)
            if loc is None:
                break
            if tri_poly[index] == i:
                # Hit our own face (precision), step past it
                origin = loc + direction * eps
                continue
            # A valid exit hits the back side of the opposite wall
            if normal.dot(direction) > 0:
                thickness[i] = (loc - start).length * mm
            break

    coords = co[tri_v].reshape(-1, 3).astype(np.float32)
    return _Result(coords, tri_poly, thickness, areas, obj.matrix_world.to_scale())


def _get_batch(result, props, shader):
    key = (props.nozzle, props.thickness_problems_only)
    if result.batch is not None and result.batch_key == key:
        return result.batch

    tri_cat = categories(result.thickness, props.nozzle)[result.tri_poly]
    mask = tri_cat < GREEN if props.thickness_problems_only else np.ones(len(tri_cat), bool)
    if not mask.any():
        result.batch, result.batch_key = None, key
        return None

    coords = result.coords.reshape(-1, 3, 3)[mask].reshape(-1, 3)
    colors = np.repeat(COLORS[tri_cat[mask]], 3, axis=0)
    result.batch = batch_for_shader(shader, 'TRIS', {"pos": coords, "color": colors})
    result.batch_key = key
    return result.batch


def _draw():
    if not _results:
        return
    context = bpy.context
    if not context.space_data.overlay.show_overlays:
        return
    scene = context.scene
    props = scene.print3d_setup
    shader = drawing.overlay_shader()

    items = []
    for name in list(_results):
        obj = scene.objects.get(name)
        if obj is None or not obj.visible_get():
            continue
        result = get_result(obj)
        if result.stale:
            continue
        batch = _get_batch(result, props, shader)
        if batch is not None:
            items.append((obj.matrix_world, batch))
    drawing.draw_overlay(context, items, bias=0.001)


def _on_depsgraph_update(scene, depsgraph):
    if not _results:
        return
    for update in depsgraph.updates:
        if update.is_updated_geometry and isinstance(update.id, bpy.types.Object):
            result = _results.get(update.id.original.name)
            if result is not None:
                result.stale = True


class PRINT3D_OT_thickness_analyze(bpy.types.Operator):
    """Measure wall thickness of the selected objects and show it as a color map"""
    bl_idname = "print3d.thickness_analyze"
    bl_label = "Analyze Thickness"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(utils.printable_objects(context.selected_objects))

    def execute(self, context):
        start = time.perf_counter()
        depsgraph = context.evaluated_depsgraph_get()
        faces = 0
        for obj in utils.printable_objects(context.selected_objects):
            result = analyze(obj, depsgraph, context.scene)
            if result is None:
                _results.pop(obj.name, None)
                continue
            _results[obj.name] = result
            faces += len(result.thickness)
        if context.area:
            context.area.tag_redraw()
        self.report({'INFO'}, f"Analyzed {faces} faces in {time.perf_counter() - start:.1f} s")
        return {'FINISHED'}


class PRINT3D_OT_thickness_clear(bpy.types.Operator):
    """Hide the thickness map"""
    bl_idname = "print3d.thickness_clear"
    bl_label = "Clear"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return bool(_results)

    def execute(self, context):
        _results.clear()
        if context.area:
            context.area.tag_redraw()
        return {'FINISHED'}


classes = (
    PRINT3D_OT_thickness_analyze,
    PRINT3D_OT_thickness_clear,
)


def register():
    global _handle
    _handle = bpy.types.SpaceView3D.draw_handler_add(_draw, (), 'WINDOW', 'POST_VIEW')
    bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)


def unregister():
    global _handle
    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, 'WINDOW')
        _handle = None
    _results.clear()
