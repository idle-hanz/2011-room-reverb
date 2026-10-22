# scattering_fitter — report (Track C)

**Generated:** Sat 26 Sep 2026 ~22:00 BST, on the box. Nothing is MEASURED by us. Tags are defined in `scattering_fitter/__init__.py` and the research memo.

## 1. Fitted s(f) presets (7 bands = surfaces_fitter absorb_hz)
Model: s(f) = s_lo + (s_hi − s_lo)/(1 + exp(−k·log2(f/fc))).
- **GRAS rows** are fitted to 1/3-octave data from 100 Hz to 10 kHz.
- **Where fc = 20000** (the bound), the data only starts rising above 10 kHz. The 7-band values are then near-flat and taken directly from the data.

| id | honesty | s @125,250,500,1k,2k,4k,8k | s_lo | s_hi | fc Hz | k /oct | RMSE | ODEON 707 Hz check |
|---|---|---|---|---|---|---|---|---|
| plaster_smooth | VERIFIED_CITED_EST | 0.02, 0.02, 0.02, 0.02, 0.03, 0.05, 0.07 | 0.015 | 0.228 | 20000 | 0.73 | 0.006 | model 0.021 vs 0.02–0.05: inside |
| gypsum_painted | PROXY | 0.01, 0.01, 0.01, 0.01, 0.01, 0.02, 0.06 | 0.008 | 0.650 | 20000 | 1.87 | 0.003 | model 0.008 vs 0.02–0.05: OUTSIDE |
| brick_unglazed | VERIFIED_CITED_EST | 0.02, 0.02, 0.02, 0.05, 0.23, 0.41, 0.44 | 0.022 | 0.448 | 2020 | 2.50 | 0.006 | model 0.032 vs 0.05–0.1: OUTSIDE |
| concrete_painted | VERIFIED_CITED_EST | 0.01, 0.02, 0.03, 0.06, 0.09, 0.12, 0.13 | 0.006 | 0.132 | 1174 | 1.06 | 0.002 | model 0.046 vs 0.005–0.02: OUTSIDE |
| glass_window | VERIFIED_CITED_EST | 0.01, 0.01, 0.01, 0.01, 0.02, 0.02, 0.04 | 0.007 | 0.113 | 20000 | 0.73 | 0.003 | model 0.011 vs 0.02–0.05: OUTSIDE |
| plywood_panel | VERIFIED_CITED_EST | 0.02, 0.03, 0.03, 0.10, 0.35, 0.48, 0.49 | 0.024 | 0.496 | 1607 | 2.47 | 0.007 | — |
| wood_parquet | VERIFIED_CITED_EST | 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.04 | 0.008 | 0.285 | 20000 | 1.62 | 0.003 | model 0.008 vs 0.02–0.05: OUTSIDE |
| acoustic_ceiling_tile | VERIFIED_CITED_EST | 0.02, 0.02, 0.02, 0.02, 0.02, 0.06, 0.24 | 0.019 | 0.302 | 5975 | 3.19 | 0.009 | — |
| absorber_panel_2in | VERIFIED_CITED_EST | 0.01, 0.01, 0.01, 0.01, 0.03, 0.06, 0.08 | 0.006 | 0.088 | 2976 | 1.37 | 0.001 | — |
| carpet_on_concrete | PROXY | 0.01, 0.01, 0.01, 0.01, 0.02, 0.04, 0.14 | 0.012 | 0.467 | 11320 | 1.93 | 0.004 | model 0.012 vs 0.02–0.05: OUTSIDE |
| carpet_on_foam | PROXY | 0.01, 0.01, 0.01, 0.01, 0.02, 0.04, 0.14 | 0.012 | 0.467 | 11320 | 1.93 | 0.004 | model 0.012 vs 0.02–0.05: OUTSIDE |
| heavy_curtain | ASSUMED | 0.00, 0.01, 0.08, 0.28, 0.41, 0.44, 0.44 | 0.000 | 0.442 | 837 | 2.07 | 0.066 | — |
| diffuser_qrd_n7 | VERIFIED_MEASURED(2 pts)+ASSUMED(shape) | 0.18, 0.32, 0.53, 0.73, 0.85, 0.90, 0.92 | 0.069 | 0.938 | 459 | 1.01 | 0.000 | — |
| diffuser_ceiling_measured | VERIFIED_MEASURED | 0.08, 0.10, 0.16, 0.28, 0.48, 0.71, 0.87 | 0.069 | 1.000 | 2349 | 1.01 | 0.016 | — |
| diffuser_pyramids | VERIFIED_MEASURED | 0.02, 0.03, 0.06, 0.17, 0.48, 0.81, 0.95 | 0.018 | 1.000 | 2105 | 1.57 | 0.046 | — |

**Sources:**
- GRAS (TU Berlin; scattering *estimated* by the authors) for the 11 GRAS-based rows (3 of them PROXY).
- Cox & D'Antonio App. D (ISO 17497-1 measured, via transcription) for pyramids and for the curtain proxy.
- Kamisiński et al. 2010 (measured) for the ceiling diffuser.
- Khrystoslavenko & Grubliauskas 2023 (2 measured points) for the QRD.
- ODEON/Zeng 2006 @707 Hz ranges are used as *checks* only. "OUTSIDE" means GRAS and ODEON guidance disagree; both are estimates.

**Honesty flags:**
- **gypsum_painted:** PROXY (GRAS plaster). No gypsum table was found.
- **carpet_on_concrete / carpet_on_foam:** PROXY (GRAS linoleum = flat floor). No carpet table was found.
- **heavy_curtain:** ASSUMED (Cox battens h = 5 cm as a fold proxy; RMSE 0.066 because the battens data is lumpy).
- **diffuser_qrd_n7:** only 2 measured points; the slope and floor are borrowed from the Kamisiński fit. At 125 Hz, 0.18 is an extrapolation.

## 2. Per-hit prototype (proto/room_proto.py, results in reports/proto_results.json)
**Setup:**
- Room 6×3×8 m, user settings.
- Taps are the *real* live params from the current code (`p_user_colour.json`, bus L: 32 lines, orders 0–4; line 2 = direct).
- Scenes (ASSUMED face assignment):
  - **demo_mixed:** side walls brick, floor parquet, ceiling tile, front plywood, back plaster;
  - **qrd_back_wall:** plaster room, parquet floor, QRD on face B.

| Metric | demo_mixed | qrd_back_wall |
|---|---|---|
| Octave energy after/before (dB) 125…8k | -0.07, -0.11, +0.07, -0.03, -0.24, -0.05, -0.32 | -0.10, -0.23, -0.06, -0.08, -0.21, +0.05, -0.21 |
| Broadband energy (dB) | -0.378 | -0.21 |
| Scattered share of *reflected* energy 125…8k | 0.009, 0.009, 0.007, 0.019, 0.046, 0.086, 0.188 | 0.018, 0.024, 0.024, 0.041, 0.064, 0.081, 0.114 |
| Per-tap filter energy error, max \|dB\| | 0.286 | 0.22 |
| Peak before → after | 0.063 → 0.063 | 0.063 → 0.063 |
| amount = 0 null vs before | 0.0 (bit-identical) | 0.0 |
| amount sweep 0→1 (dB) | 0 … −0.38, monotone within ±0.13 | 0 … −0.21 |
| Cluster widths | 10.1–30 ms (clamped) | 10.1–30 ms |

**Reading the results:**
- Energy is conserved **per tap** by construction, within the shelf-fit error (≤0.3 dB).
- The whole-IR octave deltas (≤0.32 dB) come from random cross-terms between overlapping clusters and neighbouring taps, plus shelf tails.
- It is feed-forward FIR/IIR on the early path only, so it **cannot** affect FDN stability.
- The small scattered share at LF is exactly the intended frequency split.

**Plots:**
- `plots/proto_*_ir_echogram.png`: IR before/after and 1 ms echogram;
- `plots/proto_*_energy.png`: octave energy and amount sweep;
- `plots/proto_lambert_envelope.png`;
- `plots/*_s.png`: per-material fits;
- `plots/gallery_all_s.png`.

## 3. Kernel benchmark (bench/, box measurements)
Block-major layout, ms per 128-sample block (budget 2.667 ms):

| N lines | K | native | WASM (zig -O3 -msimd128) | JS |
|---|---|---|---|---|
| 32 | 16 | 0.039 | 0.060 | 0.180 |
| 64 | 16 | 0.080 | 0.121 | 0.368 |
| 128 | 16 | 0.163 | 0.247 | 0.740 |

Scalar per-sample layout at N=128, K=16 in WASM: 2.83 ms, **so do not ship the scalar layout**. Full tables are in `bench/*.txt`.

## 4. Reproduce
```
pip install numpy scipy matplotlib ziglang
python run_fit.py
python proto/room_proto.py            # PUSER=/path/to/p_user_colour.json
cd bench && gcc -O3 -o bench_native_block bench_native_block.c && ./bench_native_block
python -m ziglang cc -target wasm32-freestanding -O3 -msimd128 -nostdlib -ffreestanding -Wl,--no-entry -Wl,--export-memory -o scatter_kernel_block.wasm scatter_kernel_block.c
node bench_node.js
```
