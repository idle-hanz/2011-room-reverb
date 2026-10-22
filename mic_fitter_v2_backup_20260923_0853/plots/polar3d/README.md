# 3D polar solids

Stacked polar fields: **height = frequency (log10)**, radial distance = linear magnitude from `frequency_dependent_polar_db` (geometric family + dual-shelf colour).

- Low freq at base, high at top (~40 Hz–16 kHz).
- `*_polar3d.png` — dense surface solid.
- `*_polar3d_rings.png` — wireframe rings at 63, 125, 250, 1k, 4k, 8k, 16k.
- MEASURED presets only (assumed/proxy skipped).

**Visual caveats:** fig-8 (e.g. Royer R-121) looks like an hourglass stack; cardioids look like tapered bulbs. Radius is pressure-linear `10**(pol_db/20)` with peak=1 per frequency layer.
