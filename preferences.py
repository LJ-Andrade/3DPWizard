import bpy

from . import icons

KOFI_URL = "https://ko-fi.com/moubix"
REPO_URL = "https://github.com/LJ-Andrade/3DPWizard"


class PRINT3D_AP_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Enjoying 3DPWizard? You can support its development:", icon_value=icons.icon_id("logo"))

        row = layout.row(align=True)
        row.operator("wm.url_open", text="Support on Ko-fi", icon='FUND').url = KOFI_URL
        row.operator("wm.url_open", text="Report a bug / Source", icon='URL').url = REPO_URL


classes = (
    PRINT3D_AP_preferences,
)
