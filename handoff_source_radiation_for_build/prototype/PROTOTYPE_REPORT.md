# Prototype report: source radiation in a 6 × 3 × 8 m room (box run, 26 Sep 2026)

**Setup:**
- `proto_render.py` uses the live `engine/early_field.py` (read-only copy) for taps, allpass and air.
- The source stage is inserted first per image; the direct path is per capsule and air-free.
- The FDN is a **stand-in** with the same topology: 32 lines, unscaled FWHT, line i ↔ tap i inject, and the diffuse filter on the excitation.
- Source (3, 1.5, 2.5), mic centre (3, 1.5, 5.5), space 0.3 m, capsules facing the source. SR 48 kHz; humidity 0.5.
- Wall peaking stages are skipped (LTI, irrelevant to relative tests).

## Omni null test: PASS (bit-exact)
Omni preset at yaw 37°, compared with no source stage: max |Δ| = **0.0** for early, direct and tail, on L and R (`out/proto_report.json`).

## Facing vs away (energy re omni; broadband = white 0–24 kHz, HF-weighted; see the 250 Hz / 4 kHz columns)
Level reference = on-axis (0 dB on axis).
| preset | yaw rel. | direct dB | early dB | tail α=0 dB | tail α=0.5 dB | early 250 Hz | early 4 kHz | power-match make-up @1k |
|---|---|---|---|---|---|---|---|---|
| talking_head | 0 | -0.0 | -1.3 | -4.37 | -3.25 | -23.8 | -18.1 | +2.3 |
| talking_head | 90 | -7.4 | -6.1 | -4.37 | -4.60 | -25.3 | -23.9 | +2.3 |
| talking_head | 180 | -16.1 | -12.8 | -4.37 | -6.75 | -26.2 | -33.0 | +2.3 |
| trumpet | 0 | -1.2 | -11.7 | -12.90 | -10.88 | -23.9 | -19.5 | +4.4 |
| trumpet | 90 | -16.3 | -14.6 | -12.90 | -13.94 | -26.6 | -37.6 | +4.4 |
| trumpet | 180 | -17.3 | -16.6 | -12.90 | -14.74 | -26.5 | -44.9 | +4.4 |
| combo_1x12 | 0 | -0.3 | -22.2 | -18.95 | -11.88 | -21.2 | -19.5 | +12.6 |
| combo_1x12 | 90 | -33.5 | -25.6 | -18.95 | -23.57 | -40.4 | -54.4 | +12.6 |
| combo_1x12 | 180 | -19.6 | -27.0 | -18.95 | -21.45 | -25.7 | -48.6 | +12.6 |

"early 250 Hz" and "early 4 kHz" are absolute 1/3-octave levels (dB, arbitrary reference) of direct + early, 0–80 ms, at mic L.

Reading the table:
- **Tail (α = 0) is identical for every yaw.** Only the direct and early sound change, which is the intended D/R spectral facing cue (Imbery 2019; Kato 2010).
- α = 0.5 lets the tail follow orientation by a few dB (Advanced only).
- "Power-match make-up" is the broadband gain that would restore the tail's 1 kHz level if `level_ref = power`.

## Plots
- `out/spectra_facing_vs_away.png`: direct + early (0–80 ms), mic L, 1/3-octave, for yaw 0/90/180 relative to facing the mic, compared with omni.
- `out/echogram_before_after.png`: 1 ms energy bins, omni (before) vs preset facing/away (after). The tail is the FDN stand-in ×0.3.

## Mirror parity check
The emission directions for first-order images point at the correct walls (see BUILD brief §8.5).

## Run
`. ../.venv/bin/activate && python proto_render.py` (~17 s on the box).

