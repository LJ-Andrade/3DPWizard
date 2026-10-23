import tomllib
from pathlib import Path

import bpy
import numpy as np

from . import icons, overhangs, thickness, utils

EPSILON = 1e-4

with open(Path(__file__).with_name("blender_manifest.toml"), "rb") as f:
    _MANIFEST = tomllib.load(f)


class _PrintSetupPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "3DPWizard"


class PRINT3D_PT_title(_PrintSetupPanel, bpy.types.Panel):
    bl_label = ""
    bl_idname = "PRINT3D_PT_title"
    bl_options = {'HIDE_HEADER'}

    def draw(self, context):
        row = self.layout.row()
        row.scale_y = 1.5
        logo = icons.icon_id("logo")
        if logo:
            row.label(text=_MANIFEST["name"], icon_value=logo)
        else:
            row.label(text=_MANIFEST["name"], icon='MOD_REMESH')
        sub = row.row()
        sub.alignment = 'RIGHT'
        sub.enabled = False
        sub.label(text=f"v{_MANIFEST['version']}")


class PRINT3D_PT_units(_PrintSetupPanel, bpy.types.Panel):
    bl_label = "Units"
    bl_idname = "PRINT3D_PT_units"

    def draw(self, context):
        self.layout.operator("print3d.setup_units", icon='DRIVER_DISTANCE')


class PRINT3D_PT_printer(_PrintSetupPanel, bpy.types.Panel):
    bl_label = "Printer"
    bl_idname = "PRINT3D_PT_printer"

    def draw(self, context):
        layout = self.layout
        props = context.scene.print3d_setup

        layout.prop(props, "printer", text="")
        col = layout.column(align=True)
        col.prop(props, "bed_x", text="X (mm)")
        col.prop(props, "bed_y", text="Y (mm)")
        col.prop(props, "bed_z", text="Z (mm)")

        layout.prop(props, "show_bed", toggle=True, icon='MESH_GRID')


def _ref_row(layout, label, value_mm):
    split = layout.split(factor=0.65)
    split.label(text=label)
    split.label(text=f"{value_mm:.2f} mm")


class PRINT3D_PT_references(_PrintSetupPanel, bpy.types.Panel):
    bl_label = "References"
    bl_idname = "PRINT3D_PT_references"

    def draw(self, context):
        layout = self.layout
        props = context.scene.print3d_setup
        nozzle = props.nozzle
        layer = props.layer_height

        col = layout.column(align=True)
        col.prop(props, "nozzle", text="Nozzle (mm)")
        col.prop(props, "layer_height", text="Layer (mm)")
        col = layout.column(align=True)
        col.prop(props, "clearance", text="Clearance (mm)")
        col.prop(props, "max_overhang", text="Max Overhang (°)")

        if layer > nozzle * 0.8:
            row = layout.row()
            row.alert = True
            row.label(text=f"Layer too thick (max ~{nozzle * 0.8:.2f})", icon='ERROR')

        box = layout.box()
        box.label(text="Walls", icon='MOD_SOLIDIFY')
        col = box.column(align=True)
        _ref_row(col, "1 line (fragile)", nozzle)
        _ref_row(col, "Minimum (2 lines)", nozzle * 2)
        _ref_row(col, "Recommended (3 lines)", nozzle * 3)

        box = layout.box()
        box.label(text="Details", icon='FONT_DATA')
        col = box.column(align=True)
        _ref_row(col, "Min XY detail", nozzle)
        _ref_row(col, "Min Z step (1 layer)", layer)
        _ref_row(col, "Emboss / engrave (3 layers)", layer * 3)

        box = layout.box()
        box.label(text="Fit", icon='SNAP_FACE')
        col = box.column(align=True)
        _ref_row(col, "Hole/gap: add per side", props.clearance)
        _ref_row(col, "Min gap between parts", max(props.clearance * 2, nozzle))


class PRINT3D_PT_thickness(_PrintSetupPanel, bpy.types.Panel):
    bl_label = "Thickness"
    bl_idname = "PRINT3D_PT_thickness"

    def draw(self, context):
        layout = self.layout
        props = context.scene.print3d_setup
        n = props.nozzle

        row = layout.row(align=True)
        row.operator("print3d.thickness_analyze", icon='MOD_SOLIDIFY')
        row.operator("print3d.thickness_clear", text="", icon='X')
        layout.prop(props, "thickness_problems_only")

        col = layout.column(align=True)
        col.label(text=f"< {n:.2f} mm   may not print", icon='COLORSET_01_VEC')
        col.label(text=f"< {n * 2:.2f} mm   fragile", icon='COLORSET_02_VEC')
        col.label(text=f"< {n * 3:.2f} mm   thin", icon='COLORSET_09_VEC')
        col.label(text=f"≥ {n * 3:.2f} mm   OK", icon='COLORSET_03_VEC')

        obj = context.active_object
        result = thickness.get_result(obj) if obj else None
        if result is None:
            return

        box = layout.box()
        box.label(text=obj.name, icon='OBJECT_DATA')
        if result.stale:
            row = box.row()
            row.alert = True
            row.label(text="Model changed, analyze again", icon='ERROR')
            return

        measured = result.thickness[np.isfinite(result.thickness)]
        if len(measured):
            box.label(text=f"Thinnest: {measured.min():.2f} mm")

        cat = thickness.categories(result.thickness, n)
        total = result.areas.sum() or 1.0
        col = box.column(align=True)
        names = ("May not print", "Fragile", "Thin", "OK", "No reading")
        icons = ('COLORSET_01_VEC', 'COLORSET_02_VEC', 'COLORSET_09_VEC', 'COLORSET_03_VEC', 'COLORSET_13_VEC')
        for c, (name, icon) in enumerate(zip(names, icons)):
            share = result.areas[cat == c].sum() / total * 100
            if share > 0 or c < thickness.GREY:
                split = col.split(factor=0.65)
                split.label(text=name, icon=icon)
                split.label(text=f"{share:.1f} %")


class PRINT3D_PT_overhangs(_PrintSetupPanel, bpy.types.Panel):
    bl_label = "Overhangs"
    bl_idname = "PRINT3D_PT_overhangs"

    def draw(self, context):
        layout = self.layout
        props = context.scene.print3d_setup
        a = props.max_overhang

        layout.prop(props, "show_overhangs", toggle=True, icon='MOD_SHRINKWRAP')
        layout.prop(props, "max_overhang", text="Max Overhang (°)")

        col = layout.column(align=True)
        col.label(text=f"> {a:.0f}°   needs support", icon='COLORSET_05_VEC')
        col.label(text=f"> {a - overhangs.BORDERLINE_MARGIN:.0f}°   borderline", icon='COLORSET_09_VEC')

        obj = context.active_object
        if not props.show_overhangs or obj is None or obj.type != 'MESH':
            return
        geo = overhangs.update(obj, context)
        if geo is None:
            return
        box = layout.box()
        box.label(text=obj.name, icon='OBJECT_DATA')
        col = box.column(align=True)
        split = col.split(factor=0.65)
        split.label(text="Needs support")
        split.label(text=f"{geo.support_share:.1f} %")
        split = col.split(factor=0.65)
        split.label(text="Borderline")
        split.label(text=f"{geo.borderline_share:.1f} %")


class PRINT3D_PT_object(_PrintSetupPanel, bpy.types.Panel):
    bl_label = "Object"
    bl_idname = "PRINT3D_PT_object"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.print3d_setup

        col = layout.column(align=True)
        col.operator("print3d.drop_to_bed", icon='TRIA_DOWN_BAR')
        col.operator("print3d.center_on_bed", icon='PIVOT_BOUNDBOX')
        col.operator("print3d.apply_transforms", icon='CHECKMARK')

        objects = utils.printable_objects(context.selected_objects)
        bounds = utils.bbox_world(objects)
        if bounds is None:
            layout.label(text="No object selected", icon='INFO')
            return

        lo, hi = bounds
        k = utils.mm_per_unit(scene)
        size = (hi - lo) * k

        box = layout.box()
        col = box.column(align=True)
        col.label(text=f"X: {size.x:.2f} mm")
        col.label(text=f"Y: {size.y:.2f} mm")
        col.label(text=f"Z: {size.z:.2f} mm")

        bed = (props.bed_x, props.bed_y, props.bed_z)
        too_big = any(s > b + EPSILON for s, b in zip(size, bed))
        lo_mm, hi_mm = lo * k, hi * k
        outside = (lo_mm.x < -bed[0] / 2 - EPSILON or hi_mm.x > bed[0] / 2 + EPSILON or
                   lo_mm.y < -bed[1] / 2 - EPSILON or hi_mm.y > bed[1] / 2 + EPSILON or
                   lo_mm.z < -EPSILON or hi_mm.z > bed[2] + EPSILON)

        row = box.row()
        if too_big:
            row.alert = True
            row.label(text="Too big for the bed", icon='ERROR')
        elif outside:
            row.alert = True
            row.label(text="Outside the bed area", icon='ERROR')
        else:
            row.label(text="Fits on the bed", icon='CHECKMARK')


class PRINT3D_PT_estimate(_PrintSetupPanel, bpy.types.Panel):
    bl_label = "Weight & Cost"
    bl_idname = "PRINT3D_PT_estimate"

    def draw(self, context):
        layout = self.layout
        props = context.scene.print3d_setup

        layout.prop(props, "material", text="")
        col = layout.column(align=True)
        col.prop(props, "density", text="Density (g/cm³)")
        col.prop(props, "price_per_kg")

        layout.operator("print3d.estimate", icon='FILE_REFRESH')

        if props.has_estimate:
            volume_cm3 = props.volume_mm3 / 1000.0
            weight_g = volume_cm3 * props.density
            cost = weight_g / 1000.0 * props.price_per_kg

            box = layout.box()
            col = box.column(align=True)
            col.label(text=f"Volume: {volume_cm3:.2f} cm³")
            col.label(text=f"Weight: {weight_g:.1f} g")
            col.label(text=f"Cost: $ {cost:.2f}")
            sub = box.column(align=True)
            sub.scale_y = 0.8
            sub.label(text="Solid model (100% infill)")
            sub.label(text="Real print uses less")


classes = (
    PRINT3D_PT_title,
    PRINT3D_PT_units,
    PRINT3D_PT_printer,
    PRINT3D_PT_references,
    PRINT3D_PT_thickness,
    PRINT3D_PT_overhangs,
    PRINT3D_PT_object,
    PRINT3D_PT_estimate,
)
