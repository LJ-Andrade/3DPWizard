"""Custom icons loaded from the icons/ folder"""

from pathlib import Path

import bpy.utils.previews

_previews = None


def icon_id(name):
    """icon_value for icons/<name>.png, or 0 if it isn't loaded"""
    if _previews is None or name not in _previews:
        return 0
    return _previews[name].icon_id


def register():
    global _previews
    _previews = bpy.utils.previews.new()
    for path in (Path(__file__).parent / "icons").glob("*.png"):
        _previews.load(path.stem, str(path), 'IMAGE')


def unregister():
    global _previews
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None
