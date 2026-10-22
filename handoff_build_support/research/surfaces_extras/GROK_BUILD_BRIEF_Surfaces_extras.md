# GROK BUILD BRIEF: Surfaces extras (wall-tone in decay lock + porous gap presets)

Written 27 Sep 2026 (BST). Background: `research/surfaces_extras/FINDINGS.md`. Implement when Idle says go. Do not start before roadmap P0 (F1–F3, F2 per-line loss) has landed.

## A. FDN wall-tone (decay lock only)

**Goal:** with decay lock on, the tail's per-octave T60 follows the Surfaces materials (Eyring shape), and the dial still sets the 1 kHz T60. With decay lock off (2011 / GainF mode), nothing changes, bit for bit.

1. **Target (Python, shared by Render and the Play packer):** add `wall_tone_t60(W, H, L, surfaces, decay_s, formula='eyring') -> t60[7]` for bands 125…8k.
   - Face areas: A/C = side walls (H·L each), B/D = ahead/behind (W·H), E/F = floor/ceiling (W·L). ᾱ(f) = Σ S_k α_k(f) / S.
   - Eyring: T(f) = 0.161 V / (−S ln(1 − ᾱ)). Shape = T(f)/T(1k). Final value = `decay_s × shape`, clamped to [0.1, 30] s.
   - **No air term** (lock).
   - `formula='sabine' | 'fitzroy'` are options, off by default.
   - Material α comes from the card's `absorb` bands (the same data `tap_reflect_gain` uses today). With all cards flat or absorb = 0, shape = 1 at every band. This reduces exactly to today's decay lock.
2. **Per-line loss filter:** generalise F2's per-line broadband gain g_i = 10^(−3 d_i/(fs·T)) to one **low shelf + high shelf** per line (RBJ, fixed corners 250 Hz / 4 kHz ASSUMED, gains fitted by least squares to the 7 target gains 20·log10(10^(−3 d_i/(fs T60(f)))) ), plus the broadband gain at 1 kHz.
   - Place it where F2's gain sits, per line, outside the ±1 Hadamard.
   - Do not touch the in-loop Dffs allpass or the in-loop peaking. Account for the peaking's per-band gain in the fit, so the net loop gain hits the target.
3. **Play:** SoA biquads, 2 per line (32 lines). Coefficients go in the v2 blob (roadmap P1) under the decay-lock section and are recomputed on scene or card change only.
4. **Render:** the same filter in `fdn.py`'s decay-lock branch (same coefficients from the same Python function).

**Acceptance tests (add to `engine/tests/run_all.py`):**
- AT-WT1: decay lock on, three rooms (FINDINGS §3 table: plaster, plaster + tile ceiling, studio), `decay_s` = 1.0 and 2.5 s. The octave T30 (125 Hz–8 kHz) of the Play and Render tails must be within **±10%** of `wall_tone_t60` (target 5%), both paths.
- AT-WT2: all cards flat → identical to the pre-change decay-lock IR (null ≤ −100 dB, or bit-exact).
- AT-WT3: decay lock off → bit-exact vs pre-change, Play and Render.
- AT-WT4: CPU. Play 1 source adds ≤ +0.10 ms/block (bench_colour-style run, 3 runs, median).
- AT-WT5: no narrow-band peak > 6 dB at 9/11 kHz in a 1 s late window (the P0.2 residue check stays green).

## B. Porous-absorber gap variants (presets, no runtime code)

1. Add `absorber_panel_2in_gap2in` (and optionally 1 in / 4 in thickness) to `surfaces_fitter/presets`. Roles: `wall`, `ceiling`. Banned: `floor` (lock).
2. **Data:** prefer a measured manufacturer table for "50 mm mineral wool, 50 mm air gap". If none is available, generate α from `research/surfaces_extras/proto/angle_absorption.py` (Miki + Paris, extended reaction) and set `honesty: "MODELLED (Miki 1990 + Paris; sigma=15 kPa s/m2 ASSUMED)"`. Never label it MEASURED.
3. Fit with the existing `run_fit.py` (dual shelf). Accept if rmse_r_db < 0.5.

**Acceptance:** the preset loads in the materials picker. The 125/250 Hz α is above the on-rigid variant. The honesty tag is shown in the UI tooltip.

## Not in scope (LATER)

Angle-dependent absorption (per-hit α(θ)) and membrane-resonance (PK) material stages. See FINDINGS §1 and §2b for why.
