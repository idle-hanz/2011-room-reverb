# DECISIONS LOCKED: binaural mode, 30 Sep 2026 (Idle Hanz)

Read this first. It overrides the "DECISIONS FOR IDLE" options in earlier drafts. The build spec is
`BINAURAL_MODE_BRIEF.md` (section numbers below). The pack-side proofs are in `tests/test_binaural_locked.py`
(pass now); the Build acceptance tests are in `tests/test_binaural_mode_acceptance.py` (xfail until built).
Tags: LOCKED = Idle's decision; VERIFIED = checked by a script or test here; ASSUMED = design judgement.

| # | Decision | Locked value | Spec | Proof (pass now) |
|---|---|---|---|---|
| 1 | FDN tail | **Diffuse.** L/R FDN outputs mixed to the chosen head's MEASURED diffuse-field interaural coherence | §3.9 | `test_ic_mixer_design`, `test_ic_mixer_on_independent_noise`, `test_engine_tail_coherence_matches_head` |
| 2 | Default head | **SADIE2_KU100** (Apache-2.0). THK_KU100_FF stays available, licence flagged. SADIE2_KEMAR available | §2.1, §6 | `test_locked_default_head_and_thk_flagged` |
| 3 | Colour tables | **K = 6 biquads per ear; one mirror-symmetric table (60 entries) for both ears** | §3.6 | `test_locked_k6_single_mirror_table_60` |
| 4 | Level | **1/r² from the head centre** (`level_l == level_r`; ILD from the HRTF only) | §3.4 | `test_locked_level_from_head_centre` |
| 5 | Rear images | **Added in binaural mode**: image set `binaural_rear32` | §3.10 | `test_rear32_*`, `test_rear_images_*`, `test_rear_front_back_coloured` |
| — | EQ (not asked) | diffuse-field, as shipped | §4, §9 | — |
| — | THK licence (not asked) | stays flagged: CC BY-SA 3.0 applied (Zenodo metadata says CC BY 3.0) | `DATA_LICENCES.md` | same as 2 |

## 1. Diffuse tail: method

- **Target:** Re{IC(f)} of the chosen head over the measured sphere, area-weighted (MEASURED, from the SOFA HRIRs):
  `presets/binaural/tail_ic/<id>.json`. SADIE2_KU100: 0.94 at 100 Hz, zero at about 500 Hz, −0.145 at 700 Hz, ≈ 0 above 1 kHz.
- **Signals:** lines uncoloured. `A = √2·Σ even lines (L loop)`, `B = √2·Σ odd lines (R loop)`. These are nearly
  uncorrelated (VERIFIED |IC| ≤ 0.17 per band, within estimator noise). Loops, delays, Hadamard and inject are unchanged.
- **Mixer:** `L = Hc·A + Hs·B`, `R = Hs·A + Hc·B`, with `Hc = cos φ`, `Hs = sin φ` and `sin 2φ(f) = IC_target(f)`.
  It is realised as two linear-phase FIRs of 513 taps on M = A + B and S = A − B, shipped for 44.1 and 48 kHz.
  Latency is 5.3 ms at 48 kHz, on the tail only (ASSUMED inaudible; fallback 257 taps).
- **VERIFIED on the p5 FDN** (4 s tail, 1/3-octave bands 125 Hz–8 kHz):

  | Scene | Max \|ΔIC\| | RMS ΔIC |
  |---|---|---|
  | Default | 0.065 | 0.028 |
  | Small room | 0.098 | 0.044 |

  The estimator noise floor at that length is 0.09 median and 0.13 p95. Today's raw L/R loops miss the target by up to
  0.76–0.88. The tail level changes by +0.17 dB.
- **Test tolerance (Build):** max |ΔIC| ≤ 0.15 and RMS ≤ 0.06 against the head's target.

## 5. Rear images: what changes

- Play has N = 32 lines, one image per line (VERIFIED), so "add" means a binaural 32-image set.
  `binaural_rear32` takes `LIVE_32`, removes the 3 duplicate voices and the 4 order-4 corners, and adds:
  - the partners (0,−1,1) and (−1,−1,0), which make the set X-symmetric;
  - 5 rear images (0,0,−1), (±1,0,−1), (0,±1,−1).
  Direct stays at index 2. The selection rule is ASSUMED; everything else is VERIFIED by tests.
- **Entry count vs 64 (VERIFIED):** records (mirror-shared) / filters per ear.

  | Head yaw | Default | Two sources | Small room | Hall |
  |---|---|---|---|---|
  | 0° | 24 / 21 | 24 / 24 | 28 / 25 | 19 / 19 |
  | 90° | — | 36 | 38 (max) | — |

  Head yaw 90° spans 32–38 records across scenes; 180° is the same as 0°. The fixed bank of 60 stays ≤ 64.
- **CPU (VERIFIED, box native C):**
  - K6 filters: 3.3–3.9 % of one core at 48 kHz (2.7 ns/biquad this run; 3.75–4.5 % at the earlier 3.1 ns).
  - Tail mixer: +1.3 % (direct-form upper bound).
  - Total 4.6–5.8 %, against ORTF today at 4.0 % (which cannot run two-source colour).
- **Checks (VERIFIED):**
  - All 5 rear images arrive from |az| > 90°.
  - Rear-left has the left ear first by 461–480 µs and louder by 6.8–8.0 dB (1–8 kHz mean); rear-right is the mirror.
  - Front/back: each horizontal rear node's colour differs from its front mirror, which has the same ITD, by ≥ 1.2 dB RMS
    (median 4.1–5.1 dB, 2–12 kHz).

Plots: `plots/binaural/tail_ic_SADIE2_KU100.png`, `plots/binaural/rear_images_top.png`.
