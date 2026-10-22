# Live-32 image set (420, 434, 435, 462) — 2026-09-20

Distances debug lists, 32 poly voices. Room at this snapshot: **W=57**, **H≈34.241**, **L=97**, source **(24.925, 1.88, 72.083)**, mic centre **(28.5, 1.88, 24.25)**. Dis (462) matches CDist of these images to **0.001 m**. No new screenshot.

## Macros present **VERIFIED**

| Axis | Values | Macros | Missing |
|------|--------|--------|---------|
| SX (420) | 24.925 / 89.075 / −24.925 | `X`, `2W−X`, `−X` | `2W+X`, `−2W+X` |
| SY (434) | 70.3624 / 66.6024 / 1.88 / −1.88 / −66.6024 | all five Y | — |
| SZ (435) | 72.0831 / 121.917 / 266.083 | `Z`, `2L−Z`, `2L+Z` | `−Z`, `4L−Z`, `−2L+Z` |

Old agreed table (3×3×3 + five |n|=2 faces, omit `(0,0,−2)`) is **not** this set. That table had `±2W` and a full `nz=−1` slab.

## Ordered voices 1–32 **VERIFIED** (poly index)

Three duplicate images (same n on two voices): `(0,1,1)` v7=v8, `(0,0,1)` v9=v10, `(−1,−2,0)` v24=v25. **29 unique**. Direct is **voice 3**.

Voice 32 `nz=+2` is **`2L+Z`**, not `4L−Z`. Engine default `z_face_4l=False`.

No `nz<0` → the 2011 **32 FDN voices** have no `−Z` image. That is the ensemble’s voice table, **not** “rear wall is an absorber.” Surface **D / Behind** still exists on the Surfaces cards. Do not hardcode rear out of the product. Other grids (64like) still have `nz=−1`.

Do **not** treat `voice_table_32.py` sink ids or To V 17–52 as this poly order.

To V 17–52 is a **wider** image-index bus: X repeating-5 includes `2W+X` / `−2W+X`; Z first column has `4L−Z` at 33. LIVE_32 has neither ±2W nor `4L−Z`. Voice 1 is `(0,2,0)` = `X, 2H+Y, Z`; X-code `X` lands on To V 17, 22, 27… not poly 1. **No 1:1 map.** Data only.

Engine: `LIVE_32` in `early_field.py`. FDN line i = voice i+1.
