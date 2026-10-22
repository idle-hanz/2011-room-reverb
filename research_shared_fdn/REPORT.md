# Shared Hadamard FDN for Play: research report
Date: 2 Oct 2026, written on the box between 10:55 and 12:45 BST.
Source: `snapshot_2026-10-02_0830/software` (read-only). All work was done on box copies.
Status: complete (the 12:40 checkpoint has been updated with the skip-centre bench and the 4 s stability runs).

Tags: **VERIFIED** means measured or read in code here. **ASSUMED** means inference, literature not checked against the full paper, or an estimate.

## 0. One-paragraph answer
One shared 32-line Hadamard network, with per-mic output taps and early lanes kept per mic, works for the **stereo mic setups** (ORTF / 3-bus).
- **CPU:** the Play block costs **11–24 % less** (VERIFIED).
- **Decay:** T30 per band tracks the decay dial at least as well as today. It is closer to the dial in 4 of 4 stereo scenes (VERIFIED).
- **Coherence:** L/R tail coherence stays within RMS 0.03–0.08 of today across 6 scenes, once a small mirror-safe tap jitter (0.3 ms) is added (VERIFIED). The seed was tuned on 2 of those scenes (ASSUMED risk of over-fit).
- **Mirror symmetry** stays bit-exact (VERIFIED).
- **Binaural: not recommended.** The shared tail fails the existing head-IC test: max |dIC| 0.28 vs the 0.15 limit, where today gives 0.118 (VERIFIED). Binaural should keep its per-ear networks.
- **Binaural CPU instead:** a separate, sound-neutral change, skipping the empty centre bus in binaural, is bit-exact and cuts the binaural Play block by **14–26 %** (VERIFIED).
- **Recommendation:** add it as a **Live-only option, default OFF (per-mic stays the default), `reaktor_parity` untouched**, for stereo mic setups only.
- **Side finding (urgent, not caused by this work):** today's Play engine runs away at DC/infrasonic frequencies at long decays. In the big room at decay 8 s (the UI maximum) the output reaches full scale within about 20 s of an impulse (VERIFIED on the shipped wasm, bit-exact build). See §7.

## 1. What the engine does today (VERIFIED from live_stereo.c, snapshot 0830)
- **Buses:** 3 buses (L, C, R) × 32 lines.
  - Two sources: each bus has bank A and bank B, so 3 networks for one source and 6 for two.
  - Each line's delay = that mic's image delay. The early lane is a tap on the same ring.
  - Loop: `read_peaked` (lg plus peaking) → unscaled FWHT → `g·H·reads + tint(x·inj)` → per-line allpass (dffs). Then the per-line colour FIR per mic.
- **Binaural:**
  - The centre bus is empty (delay 0.042 ms, inject 0, gain 0) but is still computed.
  - `ic_collect` takes the even lines of L and the odd lines of R into the M/S IC FIRs.

## 2. CPU
### 2.1 Where the Play block time goes (VERIFIED)
Setup: shipped 0830 wasm, `wasm_run.js bench 4 8`, ms per block, min/median. Files: `profile/`.

| scene | full | FDN share (full − no_fdn) | colour FIRs (full − no_colour) |
|---|---|---|---|
| default room, 1 source | 1.129 | 0.29 ms = **26 %** | 0.15 ms |
| default room, 2 sources | 1.767 | 0.74 ms = **42 %** | 0.30 ms |
| big room 57×34.2×97 m, 1 source | 1.246 | 0.24 ms = **20 %** | 0.16 ms |
| big room, 2 sources | 1.955 | 0.81 ms = **41 %** | 0.33 ms |
| binaural default, 2 sources | 1.684 | 0.74 ms = **44 %** | 0.16 ms |

Other costs:
- Early-lane reads are about 0 ms.
- Radiation, directional vs omni: about 0.01 ms with 2 sources, but +0.165 ms with 1 source. The kind-0 and kind-1 tints are computed separately in that path.
- `fdn_wet = 0` still runs the colour FIRs, on zeros.

### 2.2 Shared FDN vs today (VERIFIED)
Setup:
- `proto/bench_variants_v3.py`, 6 rounds with the variant order rotated, on a noisy shared box. Reported as min / median ms.
- m0 = today, rebuilt from the box copy and bit-exact to the shipped wasm (IR max diff 0.0 in 5 scenes).
- cand = shared loop, per-mic taps, 0.3 ms jitter.

| scene | today m0 | shared cand | saving (min / median) |
|---|---|---|---|
| default 1 source | 1.114 / 1.191 | 0.906 / 0.943 | **−19 % / −21 %** |
| default 2 sources | 1.792 / 1.868 | 1.361 / 1.448 | **−24 % / −22 %** |
| big 1 source | 1.193 / 1.217 | 1.058 / 1.095 | **−11 % / −10 %** |
| big 2 sources | 1.926 / 2.010 | 1.497 / 1.552 | **−22 % / −23 %** |
| binaural 2 sources (not recommended) | 1.676 / 1.742 | 1.365 / 1.422 | −19 % / −18 % |

- The saving is about 50–60 % of the FDN share, not 67 %. The C network still runs, the per-mic tap reads and colour FIRs remain, and there is per-sample D0 bookkeeping (VERIFIED from the numbers; the cause split is ASSUMED).
- A first jitter build that hashed per sample cost as much as today. Precomputing the jitter at load fixed it, and the output is bit-identical to the per-sample version (VERIFIED).

### 2.3 Binaural: skip the empty centre bus (bit-exact)
- `-DSKIP_EMPTY_C`: when the centre has gain 0 and all inject values are 0, bus C's `bus_sample` and its mix/colour work are skipped. The C ring is zeroed when the centre comes back.
- IR max diff vs today is **0.0** (VERIFIED) on:
  - binaural default with 1 and 2 sources, binaural big, each with colour on and off;
  - default 2 sources and big 1 source (C not empty there, so the path is unchanged).
- CPU (6 alternating rounds, `proto/bench_skipc.json`; VERIFIED):

| scene | today min / median ms | skip-empty-centre | saving |
|---|---|---|---|
| binaural default 2 sources | 1.735 / 1.760 | 1.278 / 1.321 | **−26 % / −25 %** |
| binaural default 1 source | 0.972 / 1.026 | 0.774 / 0.787 | **−20 % / −23 %** |
| binaural big 1 source | 1.036 / 1.062 | 0.861 / 0.913 | **−17 % / −14 %** |

This saves more CPU than the shared tail did in binaural (−18/−19 %), with no sound change.

## 3. Literature (details in `lit/LIT_NOTES.md`; summaries ASSUMED, not checked against the full papers)
- **One FDN with per-channel output vectors is the textbook multichannel design:** Stautner & Puckette 1982; Jot & Chaigne 1991; IRCAM Spat. Per-output networks are the unusual choice.
- **Schlecht, Fagerström & Välimäki 2023** (TASLP 31:3478): output decorrelation comes from the feedforward/output mixing. Common output delays alone do not decorrelate. More lines and dense or velvet matrices help.
  - The velvet/dense-matrix option would break the ±1 Hadamard lock, so it is not proposed.
- **Coherence control outside the loop:**
  - Menzer & Faller 2009 / 2011: our binaural IC stage is this design;
  - Habets & Gannot 2007/2008 and Mirabilii et al. 2021: per-band Cholesky or balanced mixing to a target coherence matrix;
  - Elko 2001: diffuse-field coherence of directional mics, the physical target for ORTF.
  - This is the principled upgrade path if the hashed jitter is not good enough.

## 4. Prototype (proto/live_stereo_shared.c, compile switches)
- `SHARED_MODE=0`: today's engine, bit-exact (VERIFIED).
- `SHARED_MODE=1`, the candidate:
  - **Loop:** only bus C runs the recursive 32-line loop. With two sources, bank A and bank B stay separate networks (one per source); "both sources in one network" was not built.
  - **Inject:** injS_i = sign(Σ_mics inj) · RMS over the real mics of inj_mic,i. That is L/C/R for ORTF and L/R for binaural, where the virtual centre takes the average L/R line parameters and whole-sample delays.
  - **Early lanes:** each mic, C included, keeps its own early lanes and inject.
  - **Taps:** the line outputs y_i go to a history ring (bus L's unused FDN lanes). Each mic b reads line i at the integer offset D0 + 1 + (d_b,i − d_C,i) + jitter_b,i, then scales by g_b = sqrt(Σ inj_b² / Σ injS²).
    - g_b restores each mic's tail level and the L/R balance. Without it the tail was +1.3 to +2.4 dB louder and L/R balance was lost (VERIFIED).
  - **Jitter:** `SHARED_JITTER_US=300`, `SHARED_JSEED=1`. It is a hash of the *partner* bus's line delay (L keyed on R and vice versa), which keeps the mirror test bit-exact.
  - **Colour:** each mic's per-line colour FIR runs on its own taps, unchanged.
- **Locks respected (VERIFIED by construction in code):**
  - unscaled ±1 FWHT and g unchanged;
  - early images excite the FDN (via injS);
  - inject values from the pack (1/r²) are untouched;
  - per-line colour per mic;
  - serial cascade and stage order source → air → surfaces/scatter → mic colour;
  - the two diffusion layers (Hadamard and per-line allpass) stay separate;
  - the FDN return is not filtered (no air): taps read the raw line output.
- **Bugs found and fixed while building:**
  1. The virtual centre glided from 0.04 ms. It now snaps on first fill.
  2. Half-sample average delays put a linear-interpolation lowpass in the loop. The 8 kHz T30 dropped from 1.8 to 1.2 s (VERIFIED, then fixed by rounding to whole samples).
  3. A jitter key offset broke mirror symmetry (fixed).
- **Variants:**
  - `m1` = no jitter;
  - `m2` = all mics read the same taps (far too coherent: 0.84–0.90 at all bands, VERIFIED);
  - `fx` = a fixed per-bus jitter pattern, which is not mirror-exact.

## 5. Sound measurements vs today
Method: tail only (early, direct and dry = 0), ORTF toe 55° and spacing 0.17, decay lock (1.8 s default room, 4 s big room), violin_byu unless stated otherwise. Files: `measure/*.json`.

### 5.1 T30 per octave, left channel (s; VERIFIED, `measure/t30_abs_cand.json`)
| scene (dial) | today 250 / 500 / 1k / 2k / 4k / 8k | shared cand | max deviation from dial: today → cand |
|---|---|---|---|
| default 1 source (1.8) | 1.59 1.74 1.84 1.77 1.79 1.77 | 1.69 1.83 1.78 1.79 1.81 1.78 | 11.9 % → **6.3 %** |
| big 1 source (4.0) | 3.89 3.89 3.85 3.98 4.00 4.10 | 3.93 3.94 4.02 4.03 3.99 4.07 | 3.7 % → **1.8 %** |
| default 2 sources (1.8) | 1.51 1.71 1.80 1.77 1.80 1.77 | 1.68 1.84 1.77 1.81 1.82 1.79 | 16.0 % → **6.4 %** |
| big 2 sources (4.0) | 3.89 3.82 3.73 3.93 4.07 4.10 | 3.93 3.96 4.01 4.08 4.05 4.10 | 6.7 % → **2.4 %** |
| binaural default (1.8) | 1.78 1.82 1.82 1.79 1.80 1.81 | 1.80 1.79 1.80 1.83 1.80 1.80 | 1.2 % → 1.4 % |
| binaural big (4.0) | 4.13 4.02 3.91 3.97 4.02 4.03 | 4.16 4.05 3.90 4.03 3.97 3.98 | 3.4 % → 4.0 % |

- **Change vs today:** up to +11 % at 250 Hz in the default room with 2 sources, i.e. a longer bass tail that is closer to the dial (VERIFIED).
- **EDC:** the largest deviation from today down to −30 dB is 3.4 dB in the default room (250–1k), 2.9 dB in the big room (1k–8k) and ≤ 2.0 dB in binaural (VERIFIED, `cand_metrics.json`).

### 5.2 L/R tail coherence (magnitude coherence, octaves 250 Hz–8 kHz; VERIFIED)
| scene | today | shared cand (0.3 ms jitter) | no jitter (m1) |
|---|---|---|---|
| default room | .83 .63 .53 .52 .46 .47 | .87 .66 .53 .45 .45 .42 | .88 .70 .56 .57 **.80 .71** |
| big room | .85 .77 .61 .50 .45 .38 | .87 .80 .61 .53 .41 .43 | .87 .79 .61 .58 **.67 .60** |

**Across 6 non-symmetric scenes** (`measure/validate_results.json`), RMS / max deviation from today:

| scene | cand | no jitter |
|---|---|---|
| default | 0.042 / 0.069 | 0.18 / 0.35 |
| big | 0.031 / 0.050 | |
| small 6×3×8 m | 0.038 / 0.058 | |
| mid 15×8×22 m off-centre | 0.061 / 0.102 | |
| ORTF wide (30 cm, ±45°) | 0.083 / 0.121 | 0.20 / 0.31 |
| binaural | 0.070 / 0.096 | |

**Seed sensitivity:** at the same 0.3 ms, seeds 0 and 2 reach max deviations of 0.13–0.21. The seed was picked on the default and big rooms. Small, mid_off, ORTF wide and binaural were held out. Treat it as a tuned constant that needs a wider test set before shipping (ASSUMED risk).

**IACC per octave** (max |ρ| over ±1 ms; default room, today → cand):

| band | 250 | 500 | 1k | 2k | 4k | 8k |
|---|---|---|---|---|---|---|
| IACC | .81 → .91 | .58 → .68 | .49 → .49 | .39 → .36 | .41 → .33 | .39 → .18 |

So it is a bit more correlated at low frequencies and less at 8 kHz (VERIFIED).

### 5.3 Tail spectrum and level (third-octave levels of the tail window, cand − today, L channel; VERIFIED)
| scene | 125 | 250 | 500 | 1k | 2k | 4k | 8k | 12.5k |
|---|---|---|---|---|---|---|---|---|
| default room | +2.1 | +1.1 | +2.2 | −0.5 | −1.0 | −1.7 | −2.8 | −1.4 |
| big room | −0.2 | 0.0 | 0.0 | 0.0 | +1.2 | −0.4 | +0.5 | +0.5 |
| binaural default | −1.0 | −0.2 | +1.5 | +3.6 | +0.5 | −1.8 | −1.9 | −2.0 |

- Default room: the shared tail is warmer and darker by 2–3 dB at the extremes. The cause is not established (ASSUMED: interaction of the shared inject with per-mic colour).
- Broadband tail level before any matching: −0.2 dB (default), +0.3 / −0.1 dB L/R (big), −0.6 / −0.8 dB (binaural default). The per-mic tap gain keeps the level within 1 dB (VERIFIED).

### 5.4 Mirror symmetry and symmetric scenes (VERIFIED)
- **Two-source swap null** (B.L vs A.R, omni and violin): −600 dB, bit-exact, for today, m1 and cand. The fx variant fails, as designed (−5.8 / −1.8 / +0.1 dB).
- **Perfectly symmetric scene** (hall 20×10×30, source and mics on the centreline): the tail is exactly L == R in **today's engine** (max |L−R| = 0.0, colour on or off), and also in cand.
  - This follows from mirror-exactness: a symmetric scene must give a symmetric output.
  - The same applies to the 2-source IR tests at balance 0 with B mirrored, because both sources are fed the same impulse.
  - The fx variant decorrelates the symmetric hall (coherence about 0.35–0.65) but gives up the bit-exact mirror. That is a decision for Idle (D4).

### 5.5 Binaural head-IC test (`test_binaural_play_tail_coherence_matches_head` method; limit max |dIC| ≤ 0.15, RMS ≤ 0.06; VERIFIED, `binaural_ic_results.json`)
| variant | today | shared cand | shared no jitter | fx | 0.6 ms jitter, seed 2 |
|---|---|---|---|---|---|
| max / RMS | 0.118 / 0.052 **PASS** | 0.282 / 0.140 FAIL | 0.221 / 0.120 FAIL | 0.181 / 0.101 FAIL | 0.136 / 0.064 FAIL |

- The pytest itself, run with `WASM` pointed at each build, agrees: today 4 passed / 4 xfail; every shared build fails the IC test only. The ILD/ITD and direct-mirror tests pass (VERIFIED).
- **Cause (ASSUMED):** the IC mixer expects its A (even lines of L) and B (odd lines of R) inputs to be near-incoherent. Two subsets of one network are more coherent than two separate networks.

### 5.6 Stability (VERIFIED, `measure/stability*.json`/`.log`)
- Every shared run behaves like today: the same finite or not, the same growth pattern, and the same T30 within a few %.
- The shared mode changes no loop element, so stability is inherited (ASSUMED in general; VERIFIED in the runs listed).
- What is not fine is **today's** behaviour at long decays: see §7.

## 6. A/B WAVs (VERIFIED)
- **Location:** `wav/`; Desktop `2011 Room Reverb\research_shared_fdn\wav\`.
- **Dry file:** `dry_test_48k.wav`, a synthetic 21.4 s piece: clicks, pink bursts, a plucked arpeggio, staccato chords, and a sustained chord with a hard stop.
- **Rendering:** the dry file is convolved with each variant's Play IR (same wasm, same driver; Play is linear below the soft limiter, ASSUMED).
- **Levels:** loudness matched to −20 LUFS by an in-house BS.1770 implementation. Measured −20.0 to −20.3 LUFS, peaks ≤ −5 dBFS.
- **Files:** `<scene>__full|tailonly__<variant>.wav`, where A = today, B = shared candidate, C = shared without jitter, D = shared with the fixed (non-mirror) pattern. See `LISTENING_CHECKLIST.md`.

## 7. Side finding: DC/infrasonic runaway at long decays in TODAY's engine (VERIFIED, not caused by shared mode)
- **Setup:** big room, decay 8 s (UI max `decay_s` max = 8 in `index.html`), 2 sources, default diffusion, 30 s impulse response.
- **What happens:**
  - the level falls to about −89 dB, then rises about 7 dB/s;
  - it reaches full scale with a DC output of 0.999 (soft limiter) within about 20 s;
  - binaural big at 8 s is the same, faster;
  - decay 10 s does the same.
- **Builds affected:** today's m0 (bit-exact to shipped) and cand behave identically.
- **Cause (ASSUMED):** the in-loop peaking biquads (per axis, near DC) have a DC gain marginally above 1/lg when lg ≈ 1 at long decays, so a near-DC mode is unstable. The denormal guard (LS_DC = 1e-18 per sample) or any LF input seeds it.
- **Shorter decays** (30 s IR, VERIFIED, `measure/stability3.log`):
  - **binaural big room at decay 4 s also grows**: −96 dB at 5 s to −44 dB at 30 s (about +2.1 dB/s, DC −0.006 at 30 s);
  - big room with 2 sources at 4 s still falls, but only about 1.2 dB/s after 10 s (a near-marginal mode);
  - default room at 4 s and at 8 s decays cleanly to below −250 dB.
  - m0 and cand are identical in every case.
- **Musical risk:** at long decays, with real input, infrasonic build-up runs into the limiter. **This needs its own Build fix**, e.g. a DC blocker in the loop or clamping the peaking gain so that |H(DC)|·lg < 1.

## 8. Recommendation, risks, decisions
### Recommendation
Build **"Shared tail (Live, CPU saver)"** as a Live-only engine option:
- default **OFF**;
- active only for stereo 3-bus mic setups;
- **binaural always per-ear**;
- `reaktor_parity` untouched;
- Render untouched.

Ship with it the separate, sound-neutral **skip-empty-centre** optimisation for binaural (always on, bit-exact).

### Why not default ON
It changes the sound in small but audible-in-principle ways:
- bass T30 up to +11 % (closer to the dial);
- default-room tail spectrum ±2–3 dB;
- low-band IACC +0.1;
- the first FDN copy of each image moves by about 0.5–1 ms (ASSUMED: from the 0.17 m spacing plus up to 0.3 ms of jitter).
- Idle should listen first.

### Risks
1. The coherence match relies on a tuned hash seed. Other rooms or mic setups could deviate by about 0.1–0.2 (ASSUMED from the seed sweep).
2. The tail is no longer "each mic's own room"; L/R decorrelation now comes only from tap offsets and jitter. Wide spaced pairs (AB) are untested (ASSUMED).
3. The per-mic tail gain g_b is a scalar. Per-line mic directivity in the *first FDN pass* becomes the mic average, but the early lanes keep each mic's directivity (VERIFIED by construction).
4. Toggling the option on param push must clear the history ring and tap state, or there is a click/burst (ASSUMED; not tested in the prototype).
5. Two sources still use 2 networks (A and B). Merging both sources into one network was not tried; it would save more but would mix the two sources' tails (ASSUMED).
6. The bench box is noisy. Savings are min/median over 6 alternating rounds, and real browser numbers may differ (ASSUMED).

### Decisions for Idle (all sound-changing except D1)
- **D1:** ship skip-empty-centre in binaural (bit-exact; no sound change; −14 to −26 % binaural CPU). Recommend YES.
- **D2:** add the shared tail as a Live-only option, default OFF, stereo setups only? Recommend YES after listening.
- **D3:** if D2 is yes, jitter amount and seed. Candidate 0.3 ms / seed 1. Alternative: no jitter, which is cheaper to explain but too coherent above 2 kHz.
- **D4:** symmetric scenes give an exactly mono tail today. Accept it (physically correct for a perfect room), or allow a fixed L/R pattern that is not mirror-exact (it would break the bit-exact mirror test)? It is an issue today as well, independent of D2.
- **D5:** the DC runaway at long decays (§7) needs a fix in the main engine, which changes the sound at near-DC only. Recommend YES, high priority.

## 9. Files
- `profile/`: CPU profile of the shipped wasm.
- `lit/LIT_NOTES.md`: literature notes.
- `proto/`:
  - `live_stereo_shared.c`, with `live_stereo_today.c` as the copy it was built from;
  - builds: `v3/{m0,m1,cand,fx,m0_skipc}.wasm`, `sweep/*.wasm`;
  - benches: `bench_variants_v3.json`, `bench_skipc.json`;
  - `build_cmd.sh`.
- `measure/`:
  - results: `measure_results.json`, `validate_results.json`, `sweep_results.json`, `cand_metrics.json`, `t30_abs_cand.json`, `binaural_ic_results.json`;
  - stability: `stability*.json`/`.log`;
  - scripts.
- `wav/`: the A/B files, `ab_loudness.json`, `make_dry.py`, `make_ab.py`.
- `LISTENING_CHECKLIST.md`, `BUILD_BRIEF.md`.
