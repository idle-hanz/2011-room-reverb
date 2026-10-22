# source_fitter: parametric source-radiation fits (mirror of the mic fitter)

A compact per-direction model with the same DSP family as the mic model (`dual_shelf_plus_soft_one_pole` → here `radiation_shelf_plus_soft_one_pole`). Schema `source_fitter.preset.v1`.

## Layout
- `source_fitter/data_io.py`: loaders for the TU Berlin SOFA (3rd-octave, 32 mics) and BYU CSV (72×37 grid) data, plus frame/forward handling (`TU_FORWARD_MIC`) and provenance helpers.
- `source_fitter/model.py`: the model, DSP-exact magnitude (`relative_db`), DI (`directivity_index_db`) and RBJ shelf coefficients. It is exact on axis and omni gives a bit-exact null.
- `source_fitter/fit.py`: loss (DI-normalised dB + DI-match term), train/hold-out split, DE + least_squares, and `fit_diffuse_filter` (the FDN-inject filter).
- `source_fitter/plot.py`: polars (horizontal + median, 6 frequencies), 3D balloon, and DI.
- `run_fit.py`: fits the catalog (`--procs 6`, `--only id…`, `--quick`, `--assumed-only`) and writes `presets/*.json`, `presets/index.json` and `plots/`.
- `make_report.py`: writes `FIT_REPORT.md` (the table of all presets).
- `data/`: downloaded datasets (see provenance below). `data/dirpat/` is kept only for the record: REJECTED, do not redistribute.

## Model (per emission direction d in the source frame x = forward, y = left, z = up)
```
theta = angle(d, axis(aim_az, aim_el));  u = (1 - cos theta)/2
A    = max(0, 1 + b_ud*d_up + b_lr*d_left)
k_hi = A * u^p * (1 - q u^8)
k_lo = A * ((1-dip) u^p_lo (1 - q u^8) + dip * 4u(1-u))
H(d,f) = 10^(k_lo*lo_db/20) * RBJshelf(f0, k_hi*hi_db, S=shelf_s) * [(1-lp_mix) + lp_mix * OnePole(lp_hz/k_hi)^lp_order]
```
- Every weight is 0 on axis, which gives the identity. Omni (lo = hi = 0, lp_mix = 0) is an identity everywhere, bit-exact (the DSP stage is skipped).
- **Size:** `a_eq = c/(2π f0)` with c = 340 m/s (the engine's c). A user size a gives `size_scale = a/a_eq`, and both `f0` and `lp_hz` are divided by `size_scale`.
- **Diffuse (FDN inject) filter:** gain + RBJ shelf (S = 0.7) fitted to −DI(f), 50 Hz–16 kHz. Stored in `diffuse_inject`.

## Preset JSON (abridged)
```json
{ "schema": "source_fitter.preset.v1", "id": "trumpet", "label": "...", "category": "brass", "tag": "MEASURED-FIT",
  "model": "radiation_shelf_plus_soft_one_pole", "level_reference": "on-axis (0 dB) — FDN gets diffuse_inject",
  "frame": {"x": "forward", "y": "left", "z": "up", "yaw0": "+z engine"},
  "params": {"lo_db":..,"hi_db":..,"f0":..,"shelf_s":..,"p":..,"q":..,"b_ud":..,"b_lr":..,"aim_az":..,"aim_el":..,
             "lp_hz":..,"lp_mix":..,"p_lo":..,"dip":..,"lp_order":1|2},
  "size": {"a_eq_m":.., "beaming_onset_hz":.., "rule": "..."},
  "di_db": {"125":..,"250":..,...}, "diffuse_inject": {"gain_db":..,"shelf_f0":..,"shelf_gain_db":..,"shelf_s":0.7,"fit_rmse_db":..},
  "fit": {"rmse_train_db":..,"rmse_holdout_db":..,"rmse_per_band_db":{..},"di_data_db":{..},"di_model_db":{..},...},
  "dsp": {...}, "provenance": {"dataset":..,"url":..,"citation":..,"license":..,"measurement":..}, "tags": {...} }
```

## Data provenance
| Set | URL / DOI | Used for | Licence |
|---|---|---|---|
| TU Berlin 41 instruments, 3rd-octave SOFA | doi:10.14279/depositonce-19858 · paper doi:10.17743/jaes.2022.0128 · Shabtai et al. 2017 doi:10.1121/1.4976071 | singer_soprano, acoustic_guitar, trumpet, violin, cello, tu_* | CC BY-NC-SA 4.0 (file attribute) |
| BYU speech | https://scholarsarchive.byu.edu/directivity/1/ · doi:10.1121/10.0003363 | talking_head | open access, cite |
| BYU trumpet / violin | https://scholarsarchive.byu.edu/directivity/13/ , /15/ | trumpet_byu, violin_byu | open access, cite |
| BYU guitar amps (Edelman, Anderson, Bellows, Leishman 2026) | https://scholarsarchive.byu.edu/directivity/19/ | combo_* | open access, cite |
| DirPat (IEM) | https://phaidra.kug.ac.at/detail/o:68229 | **not used**: no licence, non-anechoic, orientation ambiguous | "ask the author" |

**Conventions:**
- BYU grid: θ = 0 is the front and φ = 0 is up. Both are VERIFIED by the median-plane symmetry of speech.
- BYU φ = 90° is taken as the source's left. This is ASSUMED and affects only `b_lr` and `aim_az` signs.
- The front of the guitar amps is inferred from the HF maximum (θ = 0).
- TU forward axes come from the dataset's SourceView notes (`TU_FORWARD_MIC`).

## Re-run
```
. /workspace/source_radiation/.venv/bin/activate
python run_fit.py --procs 6        # ~6 min on the box (8 cores)
python make_report.py
```
