import bpy
from mathutils import Vector

from . import utils


class PRINT3D_OT_setup_units(bpy.types.Operator):
    """Set scene units to millimeters and adjust the viewports to match"""
    bl_idname = "print3d.setup_units"
    bl_label = "Setup Units"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Scene units: 1 Blender unit = 1 mm
        units = context.scene.unit_settings
        units.system = 'METRIC'
        units.scale_length = 0.001
        units.length_unit = 'MILLIMETERS'

        # Grid and clipping in every open 3D viewport
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type != 'VIEW_3D':
                    continue
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.grid_scale = 0.001
                        space.clip_start = 0.1      # 0.1 mm
                        space.clip_end = 10000.0    # 10 m

        self.report({'INFO'}, "Units set to millimeters")
        return {'FINISHED'}


class _SelectionOperator:
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(utils.printable_objects(context.selected_objects))


class PRINT3D_OT_drop_to_bed(_SelectionOperator, bpy.types.Operator):
    """Move each selected object down so its lowest point touches Z = 0"""
    bl_idname = "print3d.drop_to_bed"
    bl_label = "Drop to Bed"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        depsgraph = context.evaluated_depsgraph_get()
        objects = utils.top_level(utils.printable_objects(context.selected_objects))
        for obj in objects:
            bounds = utils.evaluated_bounds_world(obj, depsgraph)
            if bounds:
                utils.translate_world(obj, Vector((0, 0, -bounds[0].z)))
        return {'FINISHED'}


class PRINT3D_OT_center_on_bed(_SelectionOperator, bpy.types.Operator):
    """Center the selection on the bed in X and Y, keeping objects' relative positions"""
    bl_idname = "print3d.center_on_bed"
    bl_label = "Center on Bed"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        depsgraph = context.evaluated_depsgraph_get()
        objects = utils.top_level(utils.printable_objects(context.selected_objects))
        all_bounds = [b for b in (utils.evaluated_bounds_world(o, depsgraph) for o in objects) if b]
        if not all_bounds:
            return {'CANCELLED'}
        lo_x = min(b[0].x for b in all_bounds)
        lo_y = min(b[0].y for b in all_bounds)
        hi_x = max(b[1].x for b in all_bounds)
        hi_y = max(b[1].y for b in all_bounds)
        delta = Vector((-(lo_x + hi_x) / 2, -(lo_y + hi_y) / 2, 0))
        for obj in objects:
            utils.translate_world(obj, delta)
        return {'FINISHED'}


class PRINT3D_OT_apply_transforms(_SelectionOperator, bpy.types.Operator):
    """Apply rotation and scale to the selected objects"""
    bl_idname = "print3d.apply_transforms"
    bl_label = "Apply Transforms"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        except RuntimeError as ex:
            self.report({'ERROR'}, str(ex).strip())
            return {'CANCELLED'}
        return {'FINISHED'}


class PRINT3D_OT_estimate(_SelectionOperator, bpy.types.Operator):
    """Calculate the volume of the selected objects to estimate weight and cost"""
    bl_idname = "print3d.estimate"
    bl_label = "Calculate"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        depsgraph = context.evaluated_depsgraph_get()
        volume = sum(utils.evaluated_volume_world(o, depsgraph)
                     for o in utils.printable_objects(context.selected_objects))
        props = scene.print3d_setup
        props.volume_mm3 = volume * utils.mm_per_unit(scene) ** 3
        props.has_estimate = True
        return {'FINISHED'}


classes = (
    PRINT3D_OT_setup_units,
    PRINT3D_OT_drop_to_bed,
    PRINT3D_OT_center_on_bed,
    PRINT3D_OT_apply_transforms,
    PRINT3D_OT_estimate,
)
