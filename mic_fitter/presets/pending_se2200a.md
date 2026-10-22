# Not planned: sE Electronics SE2200A

> **Status (2026-09-27): no measured data available; not planned.**  
> Idle confirmed he has no measured data for this mic. This file is a NOT-MEASURED note only —
> there is no preset, and none will be fabricated. The steps below apply only if real data ever appears.

**Dataset:** not in Franco et al. Zenodo dataset (DOI 10.5281/zenodo.4633508).

Requested for MEASURED fit in mic_fitter v3, but **no Raw_IR folder** exists in
`Microphone_Impulse_Responses.zip` for SE2200 / SE2200A / sE2200.

## What is needed

1. Manufacturer published on-/off-axis magnitude curves (20 Hz–16 kHz), **or**
2. User-captured multi-angle impulse responses (same angle grid preferred:
   0, 15, 30, 45, 60, 90, 120, 135, 150, 180 °), quasi-anechoic.

## Do not invent

No synthetic MEASURED preset will be fabricated. Until real curves/IRs arrive,
leave this stub and treat SE2200A as unavailable for honesty=MEASURED.

## Suggested next step

Drop WAVs under `data/zenodo/extracted/` named like
`SE2200A_5m_<angle>Deg_24bit.wav`, add an entry to `PREFERRED_ZENODO_MICS`,
then re-run `python run_fit.py`.
