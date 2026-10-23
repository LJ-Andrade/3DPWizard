<p align="center">
  <img src="docs/logo3dpw.png" alt="3DPWizard logo" width="220">
</p>

# 3DPWizard

A Blender add-on to prepare models for 3D printing: set up millimeter units, preview your printer's build volume, and spot walls that are too thin or overhangs that need support — right in the viewport.

Requires Blender 4.2 or newer (tested on 5.1).

<a href="https://ko-fi.com/moubix"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support me on Ko-fi"></a>

## Features

All tools live in the **3DPWizard** tab of the 3D Viewport sidebar (`N`).

### Units
- **Setup Units** — metric, unit scale 0.001, length in millimeters, grid scale and view clipping adjusted for mm work.

### Printer
- Build volume presets (Creality, Prusa, Bambu Lab, Snapmaker U1…) or custom size.
- **Show Bed** — draws the build volume as a blue overlay centered at the origin. It's not an object: it won't show in the Outliner or end up in your exports.

### References
- Enter your nozzle, layer height, fit clearance and max overhang angle.
- Get derived guidelines: minimum and recommended wall thickness, smallest XY/Z detail, emboss/engrave depth, hole clearance.
- Warns when the layer height is too thick for the nozzle.

### Thickness
- **Analyze Thickness** — measures wall thickness by casting rays inward from every face and paints the model:
  - red: thinner than 1 line (may not print)
  - orange: thinner than 2 lines (fragile)
  - yellow: thinner than 3 lines (thin)
  - green: OK
- Shows the thinnest wall and the share of the surface in each range.
- Works with modifiers and unapplied scale. Hides itself when the mesh changes so you never see stale data.

### Overhangs
- **Show Overhangs** — live map of the faces that need support (magenta) or are borderline (yellow). Updates as you rotate the object, so you can look for the best print orientation.
- Shows the share of the surface that needs support.

### Object
- **Drop to Bed**, **Center on Bed**, **Apply Transforms**.
- Live dimensions in mm and a fit check against the build volume.

### Weight & Cost
- Material presets (PLA, PETG, ABS, ASA, TPU) or custom density, price per kg.
- Estimates volume, weight and cost of the selection (solid, 100% infill — an upper bound).

## Installation

1. Download the latest `.zip` from [Releases](https://github.com/LJ-Andrade/3DPWizard/releases).
2. Drag and drop it into Blender, or go to **Edit › Preferences › Get Extensions › Install from Disk**.

## Development

Clone the repo into a folder and register that folder's parent as a local extension repository (**Preferences › Get Extensions › Repositories › + › Add Local Repository**). Enable the add-on, then use **F3 › Reload Scripts** after editing.

Build an installable package from the repo folder:

```
blender --command extension build
```

## Support

3DPWizard is free. If it saves you a failed print or two, you can buy me a coffee on [Ko-fi](https://ko-fi.com/moubix) — it helps keep the project going. Bug reports and ideas are welcome in [Issues](https://github.com/LJ-Andrade/3DPWizard/issues).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
