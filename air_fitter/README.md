# air_fitter (v0.1.0)

**Standalone tool** for Idle Hanz — fits a *tiny* distance-scalable air-absorption colour model  
to **ISO 9613-1:1993** α(f), parallel to `mic_fitter`.

> **Does not modify** the listened Room Reverb mix, AudioWorklet, or default engine path.  
> This folder is separate from `software/`. Do **not** import presets into live `software/` here.

## Locks

| Lock | Meaning |
|------|---------|
| **Geometric 1/r²** | Stays. This fit does not touch loudness versus distance. |
| **Structure 1-pole Wet/Dis** | Idle retired it (2026-09-23). It is a darker stand-in, not ISO air. Remove it in **Phase 6** of `docs/GROK_BUILD_BRIEF_Mic_tab_measured_colour.md`, in the same session as this shelf, and only after Play matches the mic filter. Do not remove it during mic phases. |
| **This shelf** | Replaces the ASSUMED −0.15 dB/m shelf. Default preset `studio_20C_50RH`. |
| **Placement** | Once on early + FDN inject; **not** Direct; **not** feedback return. |
| **Honesty** | `FITTED_TO_ISO_9613_1` — physics standard, not measured IRs. |

## Physics

ISO 9613-1:1993 atmospheric absorption (same equations as python-acoustics):

1. Saturation vapour pressure `p_sat(T)`
2. Molar water vapour `h = RH · p_sat / p` (RH as fraction)
3. Relaxation frequencies `frO`, `frN`
4. Attenuation coefficient `α(f)` in **dB/m**

Path attenuation (model ≤ 0 dB):

```
A_db(f, d) = −α(f) · d = d · H1(f)
```

Apply as magnitude `10^(A_db/20)` once per path. **Do not** replace geometric spreading.

## Filter candidates (pick best by joint RMSE)

Fit over distances `d ∈ {5, 10, 20, 40} m` and log-spaced freqs **20 Hz – 16 kHz**  
(optional HF weight ×1.5 on 4–16 kHz):

| Candidate | Model | Params |
|-----------|-------|--------|
| **A** | high shelf only | `f0`, `depth_db_per_m` (≤0), `shelf_slope` |
| **B** | high shelf + soft one-pole | + `res_hz`, `lp_mix` |
| **C** | dual high shelf | + `f0_hi`, `depth_hi_db_per_m`, `shelf_slope_hi` |

Soft one-pole = `20·log10(1/√(1+(f/fc)²))` (0 dB at DC). High shelf = same log-sigmoid as mic_fitter.

## Climate presets

1. `studio_20C_50RH` — **PRIMARY** default (20 °C, 50 % RH, 101.325 kPa)
2. `dry_20C_20RH`
3. `humid_20C_80RH`
4. `warm_22C_40RH`

Optional report note: `hall_long_path` — studio coeffs at 40–80 m (no extra fit).

## ASSUMED engine comparison (not fitted)

Current colour in `software/engine/early_field.py`:

```
gain_db = -0.15 * distance * humidity
corner ≈ 0.35 * Nyquist   # ~7718 Hz @ 44.1 kHz
```

Plots show humidity **0.5** and **1.0** vs ISO. The ASSUMED curve is a coarse flat HF shelf; ISO rises strongly with frequency.

## One-command run

```bat
cd "C:\Users\IdleHanz\Desktop\2011 Room Reverb\air_fitter"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_fit.py
```

On the agent box:

```bash
cd /workspace/air_fitter
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_fit.py
```

(Or reuse `/workspace/mic_fitter/.venv` if present.)

## Outputs

```
air_fitter/
  README.md
  requirements.txt
  run_fit.py
  MORNING_REPORT.md
  air_fitter/          # Python package
    iso9613.py
    model.py
    fit.py
    plot.py
    export.py
  presets/*.json       # climate presets (schema air_fitter.preset.v1)
  plots/fit/*.png      # ISO vs model at 5/10/20/40 m
  plots/shape/*.png    # α dB/m ISO vs H1
  reports/*.json
  logs/
```

## Room Reverb pointer

Room software: `../software/` (Desktop) / `/workspace/2011-Room-Reverb/software/` (box).  
**Untouched.** Future integration: optional read of `air_fitter/presets/*.json` as colour tables.
