"""Live overhang map: colors downward-facing faces steeper than the printable overhang angle"""

import bpy
import numpy as np
from gpu_extras.batch import batch_for_shader

from . import drawing, utils

OK, BORDERLINE, SUPPORT = range(3)
BORDERLINE_MARGIN = 10.0  # degrees below the max overhang that count as borderline
COLORS = np.array([
    (0.0, 0.0, 0.0),     # unused (OK faces aren't drawn)
    (1.00, 0.85, 0.10),  # borderline
    (0.85, 0.15, 0.75),  # needs support
], dtype=np.float32)

# Geometry cache per object name, rebuilt when the mesh changes
_cache = {}
_handle = None


class _Geometry:
    def __init__(self, co, coords, tri_poly, normals, centers, areas):
        self.co = co              # (V, 3) local vertices
        self.coords = coords      # (T*3, 3) local triangle vertices
        self.tri_poly = tri_poly  # (T,) polygon index of each triangle
        self.normals = normals    # (P, 3) local polygon normals
        self.centers = centers    # (P, 3) local polygon centers
        self.areas = areas        # (P,)
        self.cat = None
        self.batch = None
        self.batch_key = None
        self.support_share = 0.0  # % of surface that needs support
        self.borderline_share = 0.0


def _extract(obj, depsgraph):
    mesh = obj.evaluated_get(depsgraph).data
    if not isinstance(mesh, bpy.types.Mesh) or len(mesh.loop_triangles) == 0:
        return None
    nv, np_, nt = len(mesh.vertices), len(mesh.polygons), len(mesh.loop_triangles)
    co = np.empty(nv * 3, np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(nv, 3)
    tri_v = np.empty(nt * 3, np.int32)
    mesh.loop_triangles.foreach_get("vertices", tri_v)
    tri_poly = np.empty(nt, np.int32)
    mesh.loop_triangles.foreach_get("polygon_index", tri_poly)
    normals = np.empty(np_ * 3, np.float64)
    mesh.polygons.foreach_get("normal", normals)
    centers = np.empty(np_ * 3, np.float64)
    mesh.polygons.foreach_get("center", centers)
    areas = np.empty(np_, np.float64)
    mesh.polygons.foreach_get("area", areas)
    coords = co[tri_v.reshape(nt, 3)].reshape(-1, 3).astype(np.float32)
    return _Geometry(co, coords, tri_poly, normals.reshape(np_, 3), centers.reshape(np_, 3), areas)


def classify(geo, matrix_world, max_overhang, bed_tolerance):
    """Category per polygon for the object's current orientation"""
    m = np.array(matrix_world)
    rot = m[:3, :3]
    normals = geo.normals @ np.linalg.inv(rot)  # inverse-transpose for normals
    lengths = np.linalg.norm(normals, axis=1)
    lengths[lengths == 0] = 1
    nz = normals[:, 2] / lengths

    # Angle from vertical: 0 = vertical wall, 90 = flat ceiling
    angle = np.degrees(np.arcsin(np.clip(-nz, -1.0, 1.0)))
    cat = np.full(len(nz), OK, dtype=np.int8)
    cat[angle > max_overhang - BORDERLINE_MARGIN] = BORDERLINE
    cat[angle > max_overhang] = SUPPORT

    # Faces lying on the bed (the object's lowest level) don't need support
    z = geo.co @ rot[2] + m[2, 3]
    center_z = geo.centers @ rot[2] + m[2, 3]
    cat[(center_z - z.min() < bed_tolerance) & (nz < -0.99)] = OK
    return cat


def update(obj, context):
    """Classify obj for its current orientation if anything changed. Returns its geometry or None"""
    geo = _cache.get(obj.name)
    if geo is None:
        geo = _extract(obj, context.view_layer.depsgraph)
        if geo is None:
            return None
        _cache[obj.name] = geo

    props = context.scene.print3d_setup
    tolerance = props.layer_height / 2 / utils.mm_per_unit(context.scene)
    key = (tuple(map(tuple, obj.matrix_world)), props.max_overhang, tolerance)
    if geo.batch_key != key:
        geo.cat = classify(geo, obj.matrix_world, props.max_overhang, tolerance)
        total = geo.areas.sum() or 1.0
        geo.support_share = geo.areas[geo.cat == SUPPORT].sum() / total * 100
        geo.borderline_share = geo.areas[geo.cat == BORDERLINE].sum() / total * 100
        geo.batch = None
        geo.batch_key = key
    return geo


def _get_batch(geo, shader):
    if geo.batch is not None:
        return geo.batch
    tri_cat = geo.cat[geo.tri_poly]
    mask = tri_cat != OK
    if not mask.any():
        return None
    coords = geo.coords.reshape(-1, 3, 3)[mask].reshape(-1, 3)
    colors = np.repeat(COLORS[tri_cat[mask]], 3, axis=0)
    geo.batch = batch_for_shader(shader, 'TRIS', {"pos": coords, "color": colors})
    return geo.batch


def _draw():
    context = bpy.context
    scene = context.scene
    props = getattr(scene, "print3d_setup", None)
    if props is None or not props.show_overhangs:
        return
    if not context.space_data.overlay.show_overlays:
        return

    shader = drawing.overlay_shader()
    items = []
    for obj in context.view_layer.objects:
        if obj.type != 'MESH' or not obj.select_get() or not obj.visible_get():
            continue
        geo = update(obj, context)
        batch = _get_batch(geo, shader) if geo else None
        if batch is not None:
            items.append((obj.matrix_world, batch))
    drawing.draw_overlay(context, items, bias=0.002)


def _on_depsgraph_update(scene, depsgraph):
    if not _cache:
        return
    for update in depsgraph.updates:
        if update.is_updated_geometry and isinstance(update.id, bpy.types.Object):
            _cache.pop(update.id.original.name, None)


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
    _cache.clear()
