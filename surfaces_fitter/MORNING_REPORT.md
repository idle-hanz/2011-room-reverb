# surfaces_fitter — MORNING_REPORT / FIT_REPORT

**Generated:** 2026-09-24 13:02 BST (Europe/London)
**Elapsed:** 13.8 s
**Honesty:** ASSUMED_TEXTBOOK (Sengpiel-style octave α — not Structure VERIFIED)
**Materials:** 12

## Locks (do not violate)

- Do **not** edit live `software/` / engine / static that Build may be editing for mic/air.
- Do **not** change listened mix defaults in the live app.
- Depth is **absolute per bounce**, not per metre.
- Tag ASSUMED vs anything VERIFIED from Structure — these tables are ASSUMED.
- Floor/Ceiling cards E/F stay; only illegal material kits on those faces are purged.

## Physics

Energy absorb α(f) at octave centres; log-frequency interpolate.
Amplitude reflection:

```
R_db(f) = 20 * log10(√(max(1 − α(f), 1e-6)))
```

Fit grid: log-spaced 20–16000 Hz. Export absorb[7] at [125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0] Hz (Desktop Surfaces cards).

Candidates: **A** `dual_high_shelf` · **B** `low_shelf_high_shelf` (LF for plywood/glass/curtain).
Loss: RMSE of model R_db vs target R_db; also absorb-band L1.

## RMSE table

| Material | Roles | Model | RMSE R_db | Absorb L1 | A | B |
|----------|-------|-------|-----------|-----------|---|---|
| `brick_unglazed` | wall | `dual_high_shelf` | **0.0015** | 0.0006 | 0.0015 | 0.0040 |
| `concrete_painted` | floor,wall,ceiling | `dual_high_shelf` | **0.0019** | 0.0008 | 0.0019 | 0.0060 |
| `plaster_smooth` | wall,ceiling | `dual_high_shelf` | **0.0030** | 0.0009 | 0.0030 | 0.0021 |
| `gypsum_painted` | wall,ceiling | `low_shelf_high_shelf` | **0.0042** | 0.0014 | 0.1000 | 0.0042 |
| `wood_parquet` | floor | `dual_high_shelf` | **0.0103** | 0.0032 | 0.0103 | 0.0215 |
| `plywood_panel` | wall | `low_shelf_high_shelf` | **0.0262** | 0.0075 | 0.4102 | 0.0262 |
| `carpet_on_concrete` | floor | `dual_high_shelf` | **0.0450** | 0.0084 | 0.0450 | 0.0470 |
| `carpet_on_foam` | floor | `dual_high_shelf` | **0.0471** | 0.0101 | 0.0471 | 0.1617 |
| `glass_window` | wall | `low_shelf_high_shelf` | **0.0550** | 0.0108 | 0.6981 | 0.0550 |
| `acoustic_ceiling_tile` | ceiling | `low_shelf_high_shelf` | **0.1661** | 0.0131 | 0.2278 | 0.1661 |
| `heavy_curtain` | wall | `low_shelf_high_shelf` | **0.2060** | 0.0268 | 0.2309 | 0.2060 |
| `absorber_panel_2in` | wall | `dual_high_shelf` | **0.2713** | 0.0244 | 0.2713 | 0.4523 |

- **Best RMSE:** `brick_unglazed` = 0.0015 dB
- **Worst RMSE:** `absorber_panel_2in` = 0.2713 dB

## Role matrix

| Role | Allowed material ids |
|------|----------------------|
| **floor** | `concrete_painted`, `wood_parquet`, `carpet_on_concrete`, `carpet_on_foam` |
| **wall** | `plaster_smooth`, `gypsum_painted`, `brick_unglazed`, `concrete_painted`, `plywood_panel`, `glass_window`, `absorber_panel_2in`, `heavy_curtain` |
| **ceiling** | `plaster_smooth`, `gypsum_painted`, `concrete_painted`, `acoustic_ceiling_tile` |

### Banned faces (from roles)

| Material | banned_on |
|----------|-----------|
| `plaster_smooth` | floor |
| `gypsum_painted` | floor |
| `brick_unglazed` | floor, ceiling |
| `concrete_painted` | _(none)_ |
| `wood_parquet` | wall, ceiling |
| `plywood_panel` | floor, ceiling |
| `carpet_on_concrete` | wall, ceiling |
| `carpet_on_foam` | wall, ceiling |
| `glass_window` | floor, ceiling |
| `acoustic_ceiling_tile` | floor, wall |
| `absorber_panel_2in` | floor, ceiling |
| `heavy_curtain` | floor, ceiling |

## Crazy-kit purge (Idle pick #11)

See `PURGE_LIST.md` and Desktop `findings/surfaces-crazy-kit-purge.md`.

- Curtain/Carpet must **not** be unrestricted paint-all chips.
- Ban: curtains on floor (E) or ceiling (F); carpet on walls/ceiling unless Idle unlocks.
- Shift-paint-all must skip illegal role combos.
- Do **not** delete Floor/Ceiling cards E/F themselves.

## Absolute paths (box)

- Pack root: `/workspace/surfaces_fitter`
- Presets: `/workspace/surfaces_fitter/presets`
- Plots: `/workspace/surfaces_fitter/plots`
- Reports: `/workspace/surfaces_fitter/reports`

## Desktop sync target

`C:\Users\IdleHanz\Desktop\2011 Room Reverb\surfaces_fitter\`
`C:\Users\IdleHanz\Desktop\2011 Room Reverb\findings\surfaces-crazy-kit-purge.md`

## Per-material params

### `plaster_smooth`

- Plaster (smooth) · roles=['wall', 'ceiling'] · candidate A / `dual_high_shelf`
- RMSE R_db=0.00305 · absorb L1=0.00093
- absorb=[0.02, 0.02, 0.03, 0.04, 0.05, 0.05, 0.05]
- source: Sengpiel / typical smooth plaster on solid backing
- params:
```json
{
  "r0_db": -0.08631690424417518,
  "f0": 714.0560259220359,
  "depth_db": -0.13826348891990398,
  "shelf_slope": 5.599635884583102,
  "f0_hi": 13870.040538140334,
  "depth_hi_db": -6.441181098471628e-13,
  "shelf_slope_hi": 11.842721413448551
}
```

### `gypsum_painted`

- Gypsum board (painted) · roles=['wall', 'ceiling'] · candidate B / `low_shelf_high_shelf`
- RMSE R_db=0.00416 · absorb L1=0.00142
- absorb=[0.1, 0.08, 0.05, 0.04, 0.05, 0.06, 0.06999999999999999]
- source: Typical painted gypsum / drywall on studs (panel LF dip)
- params:
```json
{
  "r0_db": -0.15488159395835563,
  "f_lo": 320.3539235619464,
  "depth_lo_db": -0.30582918149161087,
  "shelf_slope_lo": 6.693785650563932,
  "f0": 2652.6685513092348,
  "depth_db": -0.17066642102165058,
  "shelf_slope": 4.405145262180095
}
```

### `brick_unglazed`

- Brick (unglazed) · roles=['wall'] · candidate A / `dual_high_shelf`
- RMSE R_db=0.00150 · absorb L1=0.00057
- absorb=[0.03, 0.03, 0.03, 0.04, 0.05, 0.07, 0.08]
- source: Sengpiel / unglazed brick wall typical table
- params:
```json
{
  "r0_db": -0.13191496787748666,
  "f0": 788.4860314278202,
  "depth_db": -0.05056183914507467,
  "shelf_slope": 11.999999999999998,
  "f0_hi": 2959.677870500915,
  "depth_hi_db": -0.18325001959640264,
  "shelf_slope_hi": 6.7813252375336805
}
```

### `concrete_painted`

- Concrete (painted) · roles=['floor', 'wall', 'ceiling'] · candidate A / `dual_high_shelf`
- RMSE R_db=0.00192 · absorb L1=0.00081
- absorb=[0.01, 0.01, 0.02, 0.02, 0.02, 0.03, 0.03]
- source: Painted concrete / sealed concrete typical
- params:
```json
{
  "r0_db": -0.043026055802491976,
  "f0": 351.4789320900464,
  "depth_db": -0.04473161987762263,
  "shelf_slope": 11.999999999999998,
  "f0_hi": 2866.8201140295564,
  "depth_hi_db": -0.04570385694056147,
  "shelf_slope_hi": 11.999999999999998
}
```

### `wood_parquet`

- Wood parquet · roles=['floor'] · candidate A / `dual_high_shelf`
- RMSE R_db=0.01033 · absorb L1=0.00318
- absorb=[0.04, 0.04, 0.07, 0.06, 0.06, 0.07, 0.08]
- source: Wood parquet / hardwood on concrete (typical)
- params:
```json
{
  "r0_db": -0.1750553216613735,
  "f0": 316.07450310365675,
  "depth_db": -0.10806010312204987,
  "shelf_slope": 11.999999999999998,
  "f0_hi": 4519.526522721336,
  "depth_hi_db": -0.07958803549812614,
  "shelf_slope_hi": 11.275583687298312
}
```

### `plywood_panel`

- Plywood panel · roles=['wall'] · candidate B / `low_shelf_high_shelf`
- RMSE R_db=0.02616 · absorb L1=0.00750
- absorb=[0.28, 0.22, 0.17, 0.09, 0.1, 0.11, 0.12]
- source: Plywood paneling ~10 mm on battens (LF panel absorb)
- params:
```json
{
  "r0_db": -0.21475999345191502,
  "f_lo": 432.96927706622307,
  "depth_lo_db": -1.238675288234043,
  "shelf_slope_lo": 4.3926622559253525,
  "f0": 2056.9242532963813,
  "depth_db": -0.3389478699671708,
  "shelf_slope": 5.737965378937574
}
```

### `carpet_on_concrete`

- Carpet on concrete · roles=['floor'] · candidate A / `dual_high_shelf`
- RMSE R_db=0.04497 · absorb L1=0.00839
- absorb=[0.02, 0.06, 0.14, 0.37, 0.6, 0.65, 0.68]
- source: Heavy carpet on concrete (no pad) — Sengpiel-style
- params:
```json
{
  "r0_db": -0.09460972493425533,
  "f0": 1177.8627654989587,
  "depth_db": -4.772941703086262,
  "shelf_slope": 5.160598717766025,
  "f0_hi": 6538.053217177187,
  "depth_hi_db": -0.1226697417760207,
  "shelf_slope_hi": 11.999999999999998
}
```

### `carpet_on_foam`

- Carpet on foam · roles=['floor'] · candidate A / `dual_high_shelf`
- RMSE R_db=0.04712 · absorb L1=0.01007
- absorb=[0.08, 0.24, 0.57, 0.69, 0.71, 0.73, 0.76]
- source: Carpet on foam underlay / pad — typical published
- params:
```json
{
  "r0_db": -0.33071835211074346,
  "f0": 416.66733175327096,
  "depth_db": -5.013739833157151,
  "shelf_slope": 6.643352935485745,
  "f0_hi": 4468.208217738681,
  "depth_hi_db": -0.9122447485757454,
  "shelf_slope_hi": 6.989562049587113
}
```

### `glass_window`

- Glass window · roles=['wall'] · candidate B / `low_shelf_high_shelf`
- RMSE R_db=0.05502 · absorb L1=0.01080
- absorb=[0.35, 0.25, 0.18, 0.12, 0.07, 0.04, 0.04]
- source: Large ordinary window glass (panel LF resonance)
- params:
```json
{
  "r0_db": -6.805433166879811e-34,
  "f_lo": 387.3655498335804,
  "depth_lo_db": -1.9066540976774806,
  "shelf_slope_lo": 3.423072387976545,
  "f0": 408.26172039492246,
  "depth_db": -0.2205796467467608,
  "shelf_slope": 0.9267629649474936
}
```

### `acoustic_ceiling_tile`

- Acoustic ceiling tile · roles=['ceiling'] · candidate B / `low_shelf_high_shelf`
- RMSE R_db=0.16608 · absorb L1=0.01311
- absorb=[0.45, 0.55, 0.7, 0.8, 0.8, 0.75, 0.78]
- source: Mineral-fiber / ACT NRC~0.70 class typical table
- params:
```json
{
  "r0_db": -1.0128629767685533e-30,
  "f_lo": 799.999999996667,
  "depth_lo_db": -2.61274550329899,
  "shelf_slope_lo": 3.7886049860814537,
  "f0": 461.9383811270204,
  "depth_db": -6.392318737214798,
  "shelf_slope": 5.871328283647663
}
```

### `absorber_panel_2in`

- Absorber panel (2 in fiberglass) · roles=['wall'] · candidate A / `dual_high_shelf`
- RMSE R_db=0.27129 · absorb L1=0.02441
- absorb=[0.28, 0.7, 0.88, 0.92, 0.94, 0.92, 0.9500000000000001]
- source: ~50 mm fiberglass / rigid mineral wool panel typical
- params:
```json
{
  "r0_db": -1.2525801037758997,
  "f0": 328.7805061085933,
  "depth_db": -10.313100082085118,
  "shelf_slope": 5.966252587335083,
  "f0_hi": 6912.017413172723,
  "depth_hi_db": -1.601788963810436,
  "shelf_slope_hi": 11.999999999999998
}
```

### `heavy_curtain`

- Heavy curtain · roles=['wall'] · candidate B / `low_shelf_high_shelf`
- RMSE R_db=0.20599 · absorb L1=0.02683
- absorb=[0.14, 0.35, 0.55, 0.72, 0.7, 0.65, 0.68]
- source: Heavy velour / drape on wall (spaced) — Sengpiel-style
- params:
```json
{
  "r0_db": -1.4066303551531108e-46,
  "f_lo": 799.9999932746065,
  "depth_lo_db": -0.7049827022009573,
  "shelf_slope_lo": 3.334855938074777,
  "f0": 400.00000008352333,
  "depth_db": -4.940230145082744,
  "shelf_slope": 6.520567213070784
}
```
