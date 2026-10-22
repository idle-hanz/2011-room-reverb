# Binaural dataset research (30 Sep 2026)

Tags: **VERIFIED** = read today from the file, the record API or the source page; **ASSUMED** = not checked.

## Surveyed

| Dataset | Head | Licence | Distance | Grid | Rate / taps | Format | Used? |
|---|---|---|---|---|---|---|---|
| **SADIE II v2-2, D1** (York AudioLab), doi:10.5281/zenodo.12092466 | Neumann KU100 | Apache-2.0 (VERIFIED: API, SOFA attr, LICENSE.txt) | 1.2 m (VERIFIED, SourcePosition r) | 8802 directions = 22 elevation rings (−81° … +75°) × 400 azimuths + 2 poles (VERIFIED from SourcePosition); full sphere | 44.1 kHz 16-bit / 48 kHz 24-bit, 256 taps; 96 kHz 512 taps (VERIFIED) | SOFA SimpleFreeFieldHRIR 1.0 | **Yes**, `SADIE2_KU100` (default) |
| **SADIE II v2-2, D2** | KEMAR | same | 1.2 m | same 8802 | same | same | **Yes**, `SADIE2_KEMAR` |
| **TH Köln far-field KU100** (Bernschütz), doi:10.5281/zenodo.3928297 | Neumann KU100 | CC BY-SA 3.0 per SOFA attr + paper; Zenodo says CC BY 3.0 (CONFLICT, VERIFIED) | 3.25 m (VERIFIED) | FULL2DEG: 16020-point Gauss grid, 89 elevations × 180 azimuths (±88.46° el) (VERIFIED); CIRC360: horizontal 1°; also Lebedev 2354 / 2702 (not downloaded) | 48 kHz, 128 taps (VERIFIED) | SOFA SimpleFreeFieldHRIR 1.0 | **Yes**, `THK_KU100_FF` (far-field cross-check; ShareAlike) |
| TH Köln near-field KU100, doi:10.5281/zenodo.4297951 | KU100 | CC BY 4.0 (VERIFIED, Zenodo search API) | several near distances (ASSUMED) | not checked | not checked | SOFA (ASSUMED) | No: room images are mostly > 1 m away |
| MIT KEMAR (Gardner & Martin 1994) | KEMAR | free, no restrictions, cite authors (VERIFIED README) | 1.4 m (VERIFIED page) | 710 positions, el −40…+90 (VERIFIED page) | 44.1 kHz (VERIFIED page) | raw files; SOFA conversions exist (ASSUMED) | No: 44.1 kHz only, no elevations below −40° (floor images reach −65°, VERIFIED engine), SADIE KEMAR is newer |
| CIPIC (UC Davis 2001) | KEMAR subjects 021 (large pinnae) / 165 (small) (VERIFIED read_me) | any purpose incl. commercial, keep copyright notice (VERIFIED read_me on mirror) | 1 m (ASSUMED) | 1250 directions, interaural-polar (ASSUMED) | 44.1 kHz, 200 taps (ASSUMED) | MATLAB (VERIFIED read_me) | No: original host down (mirror only), 1 m, 44.1 kHz only |
| FABIAN (TU Berlin), doi:10.14279/depositonce-5718.5 | FABIAN head-and-torso simulator | CC BY 4.0 since v4 (VERIFIED) | not checked | full sphere, 11 head-above-torso orientations (VERIFIED doc) | not checked | SOFA (VERIFIED doc) | No (KU100 + KEMAR preferred). Best CC BY alternative if ShareAlike is unwanted (DECISION D7) |
| Twoears "KEMAR, different distances" (TU Berlin) | KEMAR | CC BY-NC-SA 3.0 per the Twoears docs page (not checked at source) | multiple | | | SOFA | No: NonCommercial |

## Why these three

- **KU100 + KEMAR** as asked; SADIE II gives both from one lab, one method and one grid, with an **Apache-2.0** licence
  (no ShareAlike, commercial use allowed with notice). It also ships **native 44.1 and 48 kHz** files, which matches the
  locked per-rate colour rule, so no resampling is needed.
- **TH Köln KU100** adds a true far-field (3.25 m) set of the same head, with the densest grid. It cross-checks the
  SADIE KU100 (1.2 m) and gave the best ITD model fit. Its derived files carry ShareAlike (kept separate).
- SADIE and THK both apply processing before release (VERIFIED SOFA `History` for SADIE: "Measurement, Low Frequency
  Extension, Diffuse Field Equalization, Windowing, Diffuse Field Equalization"; THK: LF optimisation is described in
  the DAGA paper, applied to these files ASSUMED). So below ~200 Hz the data are LF-extended, not raw measured.

## What the image-source engine needs (VERIFIED on the p5 tree)

- Each image tap has a 3D position; `compute_taps` gives per-capsule distance, delay and θ = acos(look · û).
  Today's colour is **axisymmetric** (one angle θ). Binaural needs **azimuth and elevation** relative to the head.
- The p5 32-image set (default 6 × 3 × 8 m room, source 2.6 / 1.2 / 4.75, mic 3 / 1.5 / 1.5) has image elevations
  **−63° … +60°** (small room ±65°), so elevation rings to ±60° plus poles cover it. It has n_z ∈ {0, 1, 2} only:
  **no rear-wall images**, so with the head facing +Z all early arrivals are within ±65° azimuth of the front
  (`reports/engine_directions.json`; see brief §3.10 and DECISION D5).
