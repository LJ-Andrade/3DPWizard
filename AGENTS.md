# Agent Instructions

## Role
Act as the project orchestrator for this repository, with the mindset of a senior Blender add-on developer (Python, `bpy`, `gpu`) who also knows FDM 3D printing.
Work directly by default. Delegate only when parallel exploration or review materially reduces implementation time or risk. Do not create sub-agents for straightforward tasks.
Keep discovery, context usage, documentation, and validation proportional to task scope and risk.

## Communication
- User-facing messages must be in Spanish.
- Keep user-facing messages short, direct, and functional.
- Code, code comments, documentation, branch names, and commit messages must be in English.
- Ask questions only when missing information blocks a safe implementation.

## Project Context
3DPWizard is a Blender extension (add-on) that helps prepare models for 3D printing: millimeter units, printer build volume overlay, print references, wall thickness map, live overhang map, bed placement tools and weight/cost estimate.

- Extension id: `wizard_3dp` (do not change it: it would break existing installs). Minimum Blender 4.2, developed on 5.1.
- Internal identifiers (`print3d.*` operators, `PRINT3D_*` classes, `Scene.print3d_setup`) are kept on purpose so saved `.blend` settings keep working.
- The parent folder is registered in Blender as a local extension repository, so the module is `bl_ext.dPrintSetup.wizard_3dp`.
- Published at https://github.com/LJ-Andrade/3DPWizard; releases are zips attached to GitHub Releases.

Preserve existing systems and architecture. Do not scaffold replacement systems or add features the task does not require.

## Layout
- `__init__.py` — registration and submodule reload on "Reload Scripts".
- `properties.py` — scene settings (`PropertyGroup`), printer and material presets.
- `operators.py` — units, bed placement, apply transforms, weight estimate.
- `panels.py` — sidebar UI (tab "3DPWizard").
- `preferences.py` — add-on preferences (support and repo links).
- `drawing.py` — build volume overlay and the shared overlay shader.
- `thickness.py`, `overhangs.py` — analysis maps drawn as viewport overlays.
- `icons.py`, `icons/` — custom icons. `utils.py` — geometry helpers.
- `docs/` — logo and screenshots for the README (excluded from the package).

## Workflow
- Work directly by default.
- Search before reading broadly; read only the relevant files and sections.
- Do not repeatedly read files whose relevant contents are already known during the current task.
- Prefer existing project patterns over new abstractions.
- Apply the smallest safe change that satisfies the request.
- Do not perform speculative cleanup, refactoring, or architecture work.
- For new features, agree on scope with the owner before building: present options with a recommendation; the owner decides.

## Validation
Keep validation proportional to risk. Blender is at `D:\Programs\Blender\blender.exe` (not on PATH).

- Logic: run headless, e.g. `blender -b --python-expr "..."` or `blender -b --python script.py`, enabling `bl_ext.dPrintSetup.wizard_3dp`. Unrelated tracebacks from other add-ons (HardOps, BoxCutter) in background mode are expected.
- Visuals (overlays, panels): launch Blender with a script that sets up the scene and calls `bpy.ops.screen.screenshot` from a timer, then quits.
- Package: `blender --command extension validate` and `blender --command extension build` from the repo folder.
- After adding files or properties, the owner must restart Blender; otherwise F3 › Reload Scripts is enough.
- Report checks that could not be run and what needs manual testing in Blender.

## Releases
1. Bump `version` in `blender_manifest.toml`.
2. Build the zip and test-install it with `BLENDER_USER_RESOURCES` pointed at a temporary folder (the dev copy has the same id).
3. Tag `vX.Y.Z`, push the tag, and publish with `gh release create`, attaching the zip.

## Galpón
Registro mis proyectos en Galpón.
- Al empezar: corré `galpon project`. Si el repo no tiene .galpon.json,
  corré `galpon init` y seguí sus instrucciones.
- Al terminar una tarea significativa: `galpon report`.
- Antes del primer uso en la sesión: `galpon guide`.
