import bmesh
import numpy as np
from mathutils import Vector

GEOMETRY_TYPES = {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}


def mm_per_unit(scene):
    """Millimeters in one Blender unit (1.0 after Setup Units)"""
    return scene.unit_settings.scale_length * 1000.0


def printable_objects(objects):
    return [o for o in objects if o.type in GEOMETRY_TYPES]


def top_level(objects):
    """Drop objects whose parent (or ancestor) is also in the list, so they don't move twice"""
    selected = set(objects)
    result = []
    for obj in objects:
        parent = obj.parent
        while parent is not None and parent not in selected:
            parent = parent.parent
        if parent is None:
            result.append(obj)
    return result


def bbox_world(objects):
    """Fast world-space bounds from bounding boxes. Returns (min, max) or None"""
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        return None
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def evaluated_bounds_world(obj, depsgraph):
    """Exact world-space bounds of the evaluated geometry (with modifiers). Returns (min, max) or None"""
    obj_eval = obj.evaluated_get(depsgraph)
    try:
        mesh = obj_eval.to_mesh()
    except RuntimeError:
        mesh = None
    try:
        if mesh is None or len(mesh.vertices) == 0:
            return bbox_world([obj])
        n = len(mesh.vertices)
        co = np.empty(n * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", co)
        co = co.reshape(n, 3)
        m = np.array(obj_eval.matrix_world)
        world = co @ m[:3, :3].T + m[:3, 3]
        return Vector(world.min(axis=0)), Vector(world.max(axis=0))
    finally:
        if mesh is not None:
            obj_eval.to_mesh_clear()


def evaluated_volume_world(obj, depsgraph):
    """Volume in Blender units cubed. Only meaningful for closed (manifold) meshes"""
    obj_eval = obj.evaluated_get(depsgraph)
    try:
        mesh = obj_eval.to_mesh()
    except RuntimeError:
        return 0.0
    if mesh is None:
        return 0.0
    try:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.transform(obj_eval.matrix_world)
        volume = abs(bm.calc_volume(signed=True))
        bm.free()
        return volume
    finally:
        obj_eval.to_mesh_clear()


def translate_world(obj, delta):
    mw = obj.matrix_world.copy()
    mw.translation += delta
    obj.matrix_world = mw
