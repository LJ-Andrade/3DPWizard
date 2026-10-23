import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty

from . import drawing

# Build volume in mm (X, Y, Z)
PRINTERS = {
    'ENDER3': ("Creality Ender 3", (220, 220, 250)),
    'K1': ("Creality K1", (220, 220, 250)),
    'PRUSA_MK4': ("Prusa MK4", (250, 210, 220)),
    'PRUSA_MINI': ("Prusa Mini", (180, 180, 180)),
    'BAMBU_A1': ("Bambu Lab A1", (256, 256, 256)),
    'BAMBU_A1_MINI': ("Bambu Lab A1 mini", (180, 180, 180)),
    'BAMBU_P1': ("Bambu Lab P1S / X1C", (256, 256, 256)),
    'SNAPMAKER_U1': ("Snapmaker U1", (270, 270, 270)),
}

# Density in g/cm³
MATERIALS = {
    'PLA': ("PLA", 1.24),
    'PETG': ("PETG", 1.27),
    'ABS': ("ABS", 1.04),
    'ASA': ("ASA", 1.07),
    'TPU': ("TPU", 1.21),
}

# Guard so that applying a preset doesn't flip it back to "Custom"
_applying_preset = False


def _printer_items(self, context):
    items = [(key, label, f"{x} × {y} × {z} mm") for key, (label, (x, y, z)) in PRINTERS.items()]
    return items + [('CUSTOM', "Custom", "Custom build volume")]


def _material_items(self, context):
    items = [(key, label, f"{d} g/cm³") for key, (label, d) in MATERIALS.items()]
    return items + [('CUSTOM', "Custom", "Custom density")]


def _on_printer(self, context):
    global _applying_preset
    if self.printer not in PRINTERS:
        return
    _applying_preset = True
    try:
        self.bed_x, self.bed_y, self.bed_z = PRINTERS[self.printer][1]
    finally:
        _applying_preset = False


def _on_bed_size(self, context):
    if not _applying_preset and self.printer != 'CUSTOM':
        self.printer = 'CUSTOM'
    drawing.tag_redraw()


def _redraw(self, context):
    drawing.tag_redraw()


def _on_material(self, context):
    global _applying_preset
    if self.material not in MATERIALS:
        return
    _applying_preset = True
    try:
        self.density = MATERIALS[self.material][1]
    finally:
        _applying_preset = False


def _on_density(self, context):
    if not _applying_preset and self.material != 'CUSTOM':
        self.material = 'CUSTOM'


class PRINT3D_PG_settings(bpy.types.PropertyGroup):
    printer: EnumProperty(name="Printer", items=_printer_items, update=_on_printer)
    bed_x: FloatProperty(name="X", default=220.0, min=1.0, unit='NONE', update=_on_bed_size)
    bed_y: FloatProperty(name="Y", default=220.0, min=1.0, unit='NONE', update=_on_bed_size)
    bed_z: FloatProperty(name="Z", default=250.0, min=1.0, unit='NONE', update=_on_bed_size)
    show_bed: BoolProperty(name="Show Bed", description="Draw the printer build volume in the viewport",
                           default=False, update=_redraw)

    # Print references (mm / degrees)
    nozzle: FloatProperty(name="Nozzle", description="Nozzle diameter in mm",
                          default=0.4, min=0.1, max=2.0, step=5, precision=2)
    layer_height: FloatProperty(name="Layer Height", description="Layer height in mm",
                                default=0.2, min=0.02, max=1.5, step=2, precision=2)
    clearance: FloatProperty(name="Fit Clearance",
                             description="Gap per side between parts that fit together, in mm",
                             default=0.2, min=0.0, max=2.0, step=5, precision=2)
    max_overhang: FloatProperty(name="Max Overhang",
                                description="Steepest overhang (from vertical) printable without supports, in degrees",
                                default=45.0, min=0.0, max=89.0, step=100, precision=0,
                                update=_redraw)

    show_overhangs: BoolProperty(name="Show Overhangs",
                                 description="Color the faces of the selected objects that need support, live",
                                 default=False, update=_redraw)
    thickness_problems_only: BoolProperty(name="Problems Only",
                                          description="Hide the parts of the thickness map that are OK",
                                          default=False, update=_redraw)

    material: EnumProperty(name="Material", items=_material_items, update=_on_material)
    density: FloatProperty(name="Density", description="g/cm³", default=1.24, min=0.01,
                           precision=2, update=_on_density)
    price_per_kg: FloatProperty(name="Price / kg", default=20.0, min=0.0, precision=2)

    # Last estimate result
    volume_mm3: FloatProperty(default=0.0)
    has_estimate: BoolProperty(default=False)


classes = (
    PRINT3D_PG_settings,
)


def register():
    bpy.types.Scene.print3d_setup = bpy.props.PointerProperty(type=PRINT3D_PG_settings)


def unregister():
    del bpy.types.Scene.print3d_setup
