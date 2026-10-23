# Al hacer "Reload Scripts", recargar también los submódulos
if "panels" in locals():
    import importlib
    importlib.reload(utils)
    importlib.reload(drawing)
    importlib.reload(thickness)
    importlib.reload(overhangs)
    importlib.reload(properties)
    importlib.reload(operators)
    importlib.reload(panels)
else:
    from . import utils, drawing, thickness, overhangs, properties, operators, panels

import bpy

modules = (properties, operators, thickness, panels)


def register():
    for module in modules:
        for cls in module.classes:
            bpy.utils.register_class(cls)
    properties.register()
    drawing.register()
    thickness.register()
    overhangs.register()


def unregister():
    overhangs.unregister()
    thickness.unregister()
    drawing.unregister()
    properties.unregister()
    for module in reversed(modules):
        for cls in reversed(module.classes):
            bpy.utils.unregister_class(cls)
