# Not planned: Røde NT5 (matched-pair SDC)

> **Status (2026-09-27): no measured data available; not planned.**  
> Idle confirmed he has no measured data for this mic. This file is a NOT-MEASURED note only —
> there is no preset, and none will be fabricated. The steps below apply only if real data ever appears.

**Dataset:** not in Franco et al. Zenodo dataset (DOI 10.5281/zenodo.4633508).

Requested for MEASURED fit (matched-pair small-diaphragm cardioid use), but **no Raw_IR folder**
exists in `Microphone_Impulse_Responses.zip` for NT5 / RodeNT5 / Røde NT5.

## What Idle chose instead

**Røde NT2-A** (1″ large-diaphragm multipattern) **is** in Zenodo and was fitted as MEASURED:

| mic_id | pattern | family |
|--------|---------|--------|
| `RodeNT2ACardioid` | cardioid | `ldc_cardioid` |
| `RodeNT2AOmni` | omni | `omni` |
| `RodeNT2ABidirect` | fig-8 | `fig8` |

## Important honesty note

NT2-A is an **LDC multipattern**, **not** an NT5 stand-in for matched-pair **SDC** use.
Do not treat the NT2-A presets as a substitute when the musical intent is two matched
small-diaphragm cardioids (overhead / AB / ORTF-style pairs).

## What is needed for a real NT5 MEASURED preset

1. Manufacturer published on-/off-axis magnitude curves (20 Hz–16 kHz), **or**
2. User-captured multi-angle impulse responses (same angle grid preferred:
   0, 15, 30, 45, 60, 90, 120, 135, 150, 180 °), quasi-anechoic.

## Do not invent

No synthetic MEASURED NT5 preset will be fabricated. Until real curves/IRs arrive,
leave this stub and treat NT5 as unavailable for honesty=MEASURED.

## Suggested next step

Drop WAVs under `data/zenodo/extracted/` named like
`RodeNT5_5m_<angle>Deg_24bit.wav` (or equivalent), add an entry to
`PREFERRED_ZENODO_MICS` with family `sdc_cardioid`, then re-run
`python run_fit.py --mics RodeNT5`.
