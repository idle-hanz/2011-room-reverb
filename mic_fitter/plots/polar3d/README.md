# 3D polar solids (v3)

Stacked polar fields: **height = frequency (log10)**, radial distance = linear magnitude from
`frequency_dependent_polar_db` (geometric family + dual-shelf colour).

- Low freq at base, high at top (**20 Hz–16 kHz**).
- `*_polar3d.png` — dense surface solid.
- `*_polar3d_rings.png` — wireframe rings at **20**, 63, 125, 250, 1k, 4k, 8k, 16k.
- MEASURED presets only (assumed/proxy skipped) — all **20 MEASURED** mics, incl. Røde NT2-A Cardioid/Omni/Bidirect (added 2026-09-27).
- Pattern families: omni / cardioid / hypercardioid / fig8 (+ ribbon alias).

**Visual caveats:** fig-8 looks like an hourglass stack; cardioids like tapered bulbs;
omnis nearly cylindrical with mild colour. Radius is pressure-linear `10**(pol_db/20)` with peak=1 per frequency layer.
