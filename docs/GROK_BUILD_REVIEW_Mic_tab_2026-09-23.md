# Grok Build read-only review — Mic tab measured colour
### Archived 2026-09-23 for audit (Idle Hanz)

| Field | Value |
|-------|--------|
| **Date** | 2026-09-23 |
| **Source** | Grok Build — read-only architecture review of brief v1 |
| **Status** | Archived as Idle pasted; recommended sides accepted |
| **Follow-up** | Folded into brief **v2** |
| **Tree check** | Reaktor Reverb Bot verified High claims against Desktop the same day (exact symbols below) |

**Exact Desktop symbols (2026-09-23 audit):** `early_wet` / `direct_wet` / `fdn_wet`; `offaxis_shelf_gain_linear` + `MIC_OFFAXIS_SHELF_DB`; dead `apply_capsule_colour` (0 callers); `direction_angles`; `compute_taps`; `mic_one_pole_coeff`; `LIVE_DIRECT_FOLD`; `render_listen_direct_ir`; `apply_mic=False` on listen paths; `WORKLET_VER = 12`; fitter `angle_weight` / `relative_db` / `dual_shelf_plus_soft_one_pole`; indexes `mic_fitter.preset_index.v3` + assumed `v2`; `POST /api/colour` = IR spectrum.

Decisions Idle locked live in brief v2 **LOCKED** section. Text below is Idle’s shared Build review (clipboard).

---

The two brief copies match. The risky gaps are in the hook point, the angle units, and the preset layout. Phase 1 can look finished and still be inaudible, or it can change the current mix.

## Missed / risky

- **High** — The audible buses are Mix Direct and the FDN. Early is silent at the current default. `early_wet` defaults to 0, `direct_wet` and `fdn_wet` to 1. `render_listen_direct_ir` writes unity spikes at the direct delays, then × 0.55 desk fold. It does not use level_*, pattern, or θ. A hook that only colours early IR / `early_field.py` will not show up on a default Render A/B.

- **High** — “Gate `apply_capsule_colour`” gates a function nothing calls. The colour actually in the signal is `offaxis_shelf_gain_linear` (−6 dB × |θ|/π) baked into every tap level inside `compute_taps`, so it is in FDN inject and in makeup. Early-only gradient HP / beaming LP run on early IR only. Panel high-pass / proximity / Mic response reach `render()` and do not touch samples. Wiring ASSUMED_TOYS as “finally call `apply_capsule_colour`” turns on a whole-buffer stereo filter that is off today. Leaving the −6 dB shelf in place stacks it under measured shelves. Removing it changes inject peaks, and inject RMS makeup will retune FDN loudness. That is the mix lock.

- **High** — Structure 1-pole is off on both listen paths (`apply_mic=False`). Worklet stores `line.micG` and does not use it for filtering. `mic_one_pole_coeff` runs on |theta| in full radians. Structure Dir dumps are ~0.002–0.17 — not radians. MEASURED and STRUCTURE are different insertion points: the pole sits on the FDN line output after the Hadamard, not on the image spike. Reusing `mic_g` / `line.micG` for measured colour is the mute bug.

- **High** — Three render producers plus a second inject builder. Still path uses `combined_ir`. Two-sources calls listen-direct / early / FDN IRs itself. Moving mode calls `combined_ir` per hop. Live coeffs come from `live_fdn_params`. A hook in only one misses a path. Source B has its own early inject while FDN stays on A’s delays and A’s θ.

- **High** — Fitter equation is magnitude in **degrees**, folded; not a biquad. `angle_weight` / `relative_db` take degrees. Audio θ is signed radians, horizontal only. Pass radians straight in and 90° is treated as ~1.6°. Relative soft pole can brighten when `fc_floor > res_hz`. Zero-phase FFT on summed IR is the old whole-IR bug. Live needs causal per-line / per-source state.

- **High** — Polar radius must not stack LF→omni morph under measured colour. Pattern math already exists in several places — do not add a fifth copy. Fig-8 rear is dark under this angle law, not a second on-axis. One preset id must not silently own L/C/R pattern.

- **High** — Preset path: resolve repo root containing `software/` and `mic_fitter/`. Assumed presets live under `presets/assumed/` with index v2. Do not scan `pending_se2200a` or backups. If `early_field` imports `software.mic_colour`, engine-only imports / selfcheck break — keep import graph one-way.

- **Med** — Centre / MS / elevation / makeup traps; HPF orthogonal and null on many mics; Phase 3 SR / WORKLET_VER / `/api/colour` name collision; bound-pinned fits still `success: true`; two brief copies must stay identical.

## Ambiguities (recommended sides — accepted into brief v2 LOCKED)

1. Filter sits on FDN inject, Mix Direct spike, early-tap buffers; Structure stays at post-Hadamard `mic_g`, off unless STRUCTURE mode; MEASURED opt-in; default path unchanged.
2. θ: signed horizontal radians at API; degrees inside model; fold in angle law only.
3. MicColour returns H_db (+ optional HPF dB); no early_field import either way; hooks in render_pipeline + live_fdn_params; early_field only gains skip-shelf flag.
4. Realise H via fitter `relative_db`; causal per tap; not RBJ+mic_one_pole; document live coeff slot in HOOKS.md.
5. Three preset ids L/C/R; map family→engine pattern ASSUMED; morph slider not live under MEASURED.
6. One enum; Bypass=BYPASS; HPF orthogonal; ASSUMED_TOYS = current shelf + early beaming/gradient — not newly wiring dead `apply_capsule_colour`.
7. Repo-root loader; v3 + qualified v2; no pending/backup scans.
8. Makeup from pre-colour inject scalars when MEASURED/BYPASS; do not bake H into scalar.

## What looks solid

Containment goal, exclusive modes, measured id list, model id/params/20 Hz–16 kHz relative dB, HPF-not-from-Zenodo, phase shipping, Polar already server mesh (`POST /api/polar`).