# GROK BUILD BRIEF: Source radiation (directivity, orientation, size)

**Project:** 2011 Room Reverb (FastAPI `app_server.py` + browser UI + AudioWorklet Play (`live_stereo.c`→WASM) + Python Render).
**Read first:** `findings/source_radiation_research.md` (why), `source_fitter/FIT_REPORT.md` (presets), `prototype/` (reference maths + null test), `findings/source_radiation_c_offload.md` (CPU).
**Tags:** VERIFIED = checked in the live code copy (`live_code/`, read-only snapshot of `software\`) or in a cited source. ASSUMED = design choice.

---
## 1. Goal
Give each source a **radiation pattern** (preset), an **orientation** (yaw, pitch, later roll) and an **apparent size**.
- Per image, the emission direction picks a gain + colour. This makes turning the source audible exactly the way it is in a room:
  - direct and early brightness and level change;
  - the reverberant tail stays put.
- The default preset is **omni**, which is bit-identical to the current sound.

## 2. Locks (do not break)
1. Unscaled ±1 Hadamard FDN stays (`fwht` in live_stereo.c, `unscaled_hadamard_*` in fdn.py). Never replace or normalise it.
2. Early images excite the FDN (line i ↔ tap i inject) as today.
3. 1/r² geometric level (1/r amplitude) is unchanged. Radiation is **relative to on-axis** (0 dB on axis).
4. Serial per-hit cascade per image. The source stage is inserted as the **first** stage: source → allpass/surfaces → air → mic.
5. The two diffusion layers stay separate. The size jitter is a third, independent seed and is never merged into the surfaces diffusion.
6. The direct path is air-free, and there is no air on the FDN return (unchanged).
7. Default = omni = null change (bit-exact test below). Do not touch listened mix voicing by default.
8. Never fabricate measured data: ASSUMED presets keep their tag in the UI (small "assumed" badge).

## 3. Data schema
Presets are `source_fitter/presets/*.json` (schema `source_fitter.preset.v1`, see `source_fitter/README.md`). Ship them as `software/presets/source/*.json` and serve them via a new `GET /api/source_presets`.

Session state additions per source (A, and B when two-source/linked), in the existing `state` object sent to `/api/live_params` and `/api/render`:
```json
"src_rad": {
  "preset": "omni",            // id
  "yaw_deg": 0.0,              // 0 = facing +z (same zero as mic yaw), + toward +x
  "pitch_deg": 0.0,            // + up
  "roll_deg": 0.0,             // phase 3
  "size_m": null,              // null = preset a_eq; else size_scale = size_m / a_eq
  "level_ref": "on_axis",      // "on_axis" (physical) | "power" (keeps tail level; see §5.6)
  "tail_follow": 0.0,          // Advanced, 0..1 (0 = diffuse-only inject, recommended)
  "size_jitter": false,        // phase 2
  "emit_points": 1             // phase 3 (1..4)
}
```

## 4. Algorithm (reference = `prototype/radiation.py`, maths = `source_fitter/model.py`)
- **Facing basis** (`facing_basis(yaw, pitch, roll)`):
  - forward f = (sin ψ cos θ, sin θ, cos ψ cos θ) in engine coords (x = width, y = height, z = length, VERIFIED early_field.py);
  - up = orthonormalised +y;
  - left = up × f.
- **Emission direction per image** (`emission_dir(n, image_pos, rx)`): v = rx − image_pos, with the components on odd-index axes negated (mirror parity: axis k is mirrored iff k odd, VERIFIED `early_field.corner_axis_from_macro`). Normalise, then d_local = basis·v.
- For each image, compute `SrcCoef = coef_for_dir(params, d_local, fs, size_scale)` using the emission direction toward the **mic centre** (shared by the L/C/R buses). This keeps it to 32 filters per source in Play. The capsule-to-capsule direction difference is ≤ 2.0° in the 6×3×8 m test. The **direct** path uses per-capsule directions. The coefficient set is:
  - broadband gain;
  - RBJ high shelf;
  - soft one-pole ×`lp_order` (fc = lp_hz/(k·size_scale), mix `lp_mix`);
  - `bypass` when k = 0 or the preset is omni.
- **Direct path:** the direction is the real source → capsule (n = (0,0,0)), one coefficient set per bus.
- **FDN inject:** use the per-source `diffuse_inject` filter (gain + RBJ shelf; the power average over the sphere = −DI(f)), applied **once to the source signal** before the per-line inject gains. Because the FDN is LTI, this is exactly equivalent to filtering the whole tail by the diffuse power response (VERIFIED in the prototype: tail energy is independent of yaw at α = 0).
- **Optional `tail_follow` α (Advanced, default 0):** per line, inject gain ×= (1−α) + α·|H_img(1 kHz)|/|H_diff(1 kHz)|. This makes the tail slightly orientation-dependent.
- **Size (phase 1):** `size_scale = size_m / a_eq`. Divide `f0` and `lp_hz` by it. That is all: the beaming onset moves.
- **Size jitter (phase 2):**
  - Each image gets a fixed pseudo-random point p_i in a ball of radius a (seed = 2011·1000003 + image index, same in C and Python).
  - Δpath = −p_i·e_i, added to the image delay (metres/c).
  - Delay-only, so no extra filters.
- **Multi-point (phase 3):** M points along the source's left axis, spaced over 2a, each with power 1/M.
  - Recommended cheap variant: extra points add only the direct + 6 first-order images.
  - The full variant multiplies the early taps by M.

## 5. Where it slots (file/function names from the live snapshot)

### 5.1 New module `engine/source_radiation.py`
- A port of `prototype/radiation.py` + `source_fitter/model.py` (the model part only): `facing_basis`, `emission_dir`, `coef_for_dir`, `diffuse_coef`, `src_process_fast`, `size_jitter_m`, `load_preset(id)`.
- This module is the **single source of truth for coefficients**, used by both Render and Play (Play phase 1 ships the coefficients in the blob).

### 5.2 Render (`render_pipeline.py`)
- **`render_early_ir(...)`:** per tap per bus, right after `_apply_ir_at(buf, delay, amp, stages, ap_cache)` (allpass), insert `buf = src_process_fast(buf, coef[tap])`. Use the same per-image (mic-centre direction) coefficients as Play, for parity. Everything after is unchanged: the grad HP / beaming LP toys, peaking, `apply_air_absorption`, `apply_surface_to_buffer`, `_colour_apply`.
  - Because everything is LTI, the order is numerically irrelevant except at float rounding. **First** keeps the conceptual cascade and the null test trivial: bypass means the stage is not called at all.
- **`render_direct_ir` / `render_listen_direct_ir(taps, …, spikes=…)`:** filter each capsule's spike with that capsule's direct coefficients **before** `_colour_apply` and the ×0.55 fold (`DIRECT_FOLD`). The direct path stays air-free.
- **`render_fdn_ir(...)`:** `build_inject_from_taps` (fdn.py) → `_scale_inject_reflect` → FDN. Apply `diffuse_coef` to the **excitation** (or equivalently to the FDN output, since it is LTI) once per source.
  - Do NOT touch `inject` amplitudes (except `tail_follow` α > 0).
  - `combined_ir` / `render` need no other changes.
- **Two-source (`two_source_excitation`, `mirror_source_b`):** source B gets its own `src_rad`. The mirrored B defaults to a mirrored yaw (−yaw) when `mirror_b` is on (ASSUMED convenience).

### 5.3 Play params (`live_fdn_params(p, sr)`)
- **Share one blob version bump with the scattering build** (`live_load_room` currently requires `rf(&r) == 1`, and the scattering brief also bumps `BLOB_LEN` and adds a version field). Append a radiation section **after** the scattering section:
```
rad_on_A, rad_on_B                       (0/1; 0 => skip everything below for that source)
per source (A[,B]):
   diffuse: g, b0,b1,b2,a1,a2                          (6)
   direct per bus b in 0..2: g,b0,b1,b2,a1,a2,pg,pm,order   (3 x 9)
   image per line i in 0..31 (shared by buses): g,b0,b1,b2,a1,a2,pg,pm,order   (32 x 9)
tail_follow per line already folded into inj (Python side)
```
  That is ≈ 330 floats per source. Coordinate `BLOB_LEN`/`MAX_BLOB` with the scattering build.
- **`live_fdn.js`:** bump `WORKLET_VER` (28 → 29) so the WASM and worklet reload together. `ROUTE_LEN` is unchanged unless the routing table grows.

### 5.4 Play DSP (`engine/live_stereo.c`, the same C core as scattering; see `findings/source_radiation_c_offload.md` §7)
- **State:** add `SrcBank srcA, srcB` in `LiveStereo`: 32 image filters each, SoA (coefficients + ramp increments + z1, z2, p1, p2). Add `SrcBiquad dirA[3], dirB[3], diffA, diffB`. Everything lives in the existing arena (`live_bind`), with no alloc in process.
- **Pre-pass at the top of `run_partition`, block-major (SIMD over lines):**
  - `srcBlk[i][t] = src_i(x or xA)` for all 32 images and 128 samples, and the same for B;
  - `xdBlk[t] = diffA(x)`;
  - `dirBlk[b][t] = dirA_b(x)`.

  `bus_sample` then reads these arrays instead of running filters per bus.
- **`bus_sample(st, b, x, xA, xB, two, t)`:**
  - **One-source branch, radiation off:** keep the exact current code, where one shared `tint(line, x*line->inj, 0)` feeds both lanes. This is the null path.
  - **One-source branch, radiation on:**
    - early lane: `tint(line, srcBlk[i][t] * line->inj, 1)` (kind 1 = the existing separate early state);
    - FDN input: `tint(line, xdBlk[t] * line->inj, 0)`.
  - **Two-source branch:** the early lanes use `srcBlkA/B[i][t]` before tint kinds 1/2. The FDN inputs use `xdBlkA/B` before tint kinds 0/3.
  - **Direct:** write `dirBlk[b][t]` (× `dirGain` for two sources) into `st->dir[b]`.
  - **Scattering (Track C) stays on the read side** of the early lane (`ev = bq(spec, ev) + bq(scat, Σ…)`). The cascade order is source (write) → tint → spec/scat (read) → colour FIR. The two changes touch different lines of `bus_sample` and compose.
- **Coefficient ramp:** on a new blob, set the targets. For the next 128 samples, step coefficients linearly (per-sample increments), then snap. Follow the pattern of the existing `delayT`/`SMOOTH` idea but use a linear ramp so it completes in one block.
- **Denormals (a prerequisite; WASM has no FTZ):** use the roadmap §3 guard (alternating ±1e-20 offset per block, or clamp |state| < 1e-15 → 0) on all source filter states. Add the source path to the silence CI test (60 s of silence ≤ 1.5× the playing cost).
- **Watchdog:** use the existing `finite_d`/`scrub()` to reset and bypass a line if its state is non-finite. Under the CPU watchdog, degrade in this order: scattering → source (omni null path) → early.

### 5.5 UI / server
- **`app_server.py`:**
  - `GET /api/source_presets` (index.json + per-preset JSON);
  - `POST /api/source_preview` (polar/balloon data at requested frequencies and DI for the Source desk, computed by `source_radiation.py`);
  - `/api/live_params` and `/api/render` pass `src_rad` through.
- UI: see `GROK_BUILD_BRIEF_Source_UI.md`.

### 5.6 Level reference (important, ASSUMED design)
Presets are referenced to **on-axis = 0 dB** (a close-miked track is roughly the on-axis sound). A directional preset therefore lowers the tail and off-axis early energy. In the prototype (box run, 6×3×8 m):
- talking_head: −4.4 dB broadband tail;
- trumpet: −12.9 dB;
- combo_1x12: −19 dB.

That is physically right but a big mix change. Offer `level_ref`:
- `on_axis`: the default once a non-omni preset is chosen; faithful.
- `power`: multiply everything for that source by the diffuse make-up gain at 1 kHz (e.g. +2.3 dB talking head, +4.4 dB trumpet, +12.6 dB combo_1x12). This keeps the tail loudness roughly as omni, and facing the mic sounds louder and brighter.

Show the make-up in the UI.

## 6. Play/Render parity
- Known pre-existing gap (audit, VERIFIED by the scattering stream): the Play early tap has no per-hit surface cascade (only a broadband √(1−ᾱ) in `inj`), while Render has the full cascade. The source stage does not widen this gap, because it is the same per-image filter in both. Run the parity tests with surfaces set to flat/neutral, or compare the source-stage contribution only (Render with vs without, Play with vs without).
- **Python** `engine/source_radiation.py` computes all coefficients for both paths.
- Render uses double precision with scipy lfilter. Play uses the same coefficients in float/double C.
- **Parity test:** render a 1 s IR through Render and through the C core (ctypes build of live_stereo.c, or the same maths in a small test harness) with a fixed preset and yaw. Early and direct must agree to −60 dB error energy relative to signal (the float Play vs double Render tolerance). The omni null must be bit-exact on both.
- Phase 2 moves `coef_for_dir` into C (`src_radiation.c`, shared by both builds). The parity test then compares Python vs C coefficients on 1000 random directions (|Δ| < 1e-6).

## 7. CPU budget (box measurements; see `findings/source_radiation_c_offload.md`)
- **Play (N = 32, WASM measured on the box with zig -O3 -msimd128):** 96 filters = 19.5 µs (SIMD) to 39 µs (scalar), so 32 shared filters ≈ 7–13 µs per source.
- **Combined with the current core + scattering** (the scattering stream's numbers):

  | Case | Total | % of budget |
  |---|---|---|
  | 1 source, colour on, K=16 | ~1.43–1.46 ms | 54–55 % |
  | 2 sources, colour on, K=8 | ~2.14–2.15 ms | 80–81 % (at the limit) |
  | 2 sources, recommended config: shared source filters + scattering on L/R only + denormal guard | ~2.03–2.08 ms | 76–78 % |

  Omni = 0. More trims (skip rules, FIR non-uniform partitioning) are in the offload doc §7.3.
- Silence without the denormal guard reaches 3.8 ms (>140 %), so fix that first.
- **N = 128 images** (future), 384 lines: 72–133 µs C (SIMD-8 vs scalar), 280 µs Node JS.
- Multi-point ×4 is linear, which is why the cheap variant is recommended.
- Coefficient recompute of all lines: 6–25 µs in C, 31–114 µs in JS (on drag only).

## 8. Acceptance tests
1. **Omni null (bit-exact):** with `preset=omni` at any yaw/pitch/size, the Render early/direct/FDN IRs and the Play output are bit-identical to the pre-change build. Prototype result (box): max |Δ| = 0.0 for early, direct and tail, L and R (`prototype/out/proto_report.json`).
2. **On-axis identity:** for any preset, an image whose emission direction equals the preset axis gets gain 1 and filters bypassed (k = 0).
3. **Tail invariance:** with `tail_follow=0`, the FDN IR energy is identical for yaw 0/90/180 (prototype: identical to 0.01 dB).
4. **Facing contrast** (prototype, box, 6×3×8 m, mic C 3 m away):
   - direct energy drops by ~16 dB (talking_head), ~17 dB (trumpet) and ~20 dB (combo_1x12) when turning 180°;
   - the early 4 kHz band drops by ~15–29 dB, and 250 Hz by ~2–5 dB.
   Values must match Render within 0.5 dB.
5. **Mirror parity:** a source facing +x must brighten the images of the +x wall (odd x-index images lit, even not) and the first-order image of the wall it faces must be ~on-axis. Prototype check (box): for source (3,1.5,2.5) and mic L, the emission directions are: n=(1,0,0) → (0.90, 0, 0.44), n=(−1,0,0) → (−0.89, 0, 0.46), n=(0,1,0) → (−0.04, 0.71, 0.71), n=(0,0,1) → (−0.02, 0, 1.0). These point at the correct walls.
6. **Coefficient smoothness:** a yaw sweep of 360° in 2 s in Play has no clicks. The spectral flux of the output is no higher than for the same sweep rendered offline in 10 ms steps.
7. **Watchdog:** injecting NaN coefficients bypasses the line and does not produce silence or NaN in the output.
8. **CPU:**
   - one source adds ≤ 0.08 ms per block on the CI box (WASM);
   - two sources with scattering stay ≤ 80 % of the budget in the recommended configuration;
   - the silence-tail test passes with the source path active.

## 9. A/B listening checklist (Idle)
- The omni preset is indistinguishable from the old build (null test first; ears second).
- Talking head, facing vs away: consonants dull, the room unchanged, the voice "turns away" rather than "gets quieter".
- Trumpet: the bell toward the mic is bright and forward. Toward a side wall, that wall "lights up" (early brightness on one side).
- Guitar cab, 1x12 closed vs 4x12 closed: the 4x12 beams from a lower frequency. Off-axis it is darker and more "room".
- Size slider on a vocal from 2 cm → 30 cm: HF narrows. It should not sound like an EQ on the tail.
- Level ref `power` vs `on_axis`: pick the default after listening.
- Two linked instances (vox + cab) facing different ways: each keeps its identity, and the tail stays one shared room.

## 10. What NOT to do
- Don't scale or replace the Hadamard. Don't put the per-image filters into the FDN loop (only the inject gets the diffuse filter).
- Don't apply air to the direct path or the FDN return. Don't merge size jitter with surface diffusion jitter.
- Don't use broadband-only directivity (Steam/Resonance style): it sounds like a volume knob.
- Don't make the tail orientation-dependent by default.
- Don't fetch measured data at runtime. Don't label ASSUMED presets as measured. Don't ship `combo_*` as the default guitar presets (low-confidence fit; use `cab_*_closed`).
- Don't redistribute DirPat data. Mind CC BY-NC-SA on TU-derived presets for any commercial build.
- Don't allocate in the worklet `process()`. Don't recompute coefficients per sample.

## 11. Phasing
| Phase | Scope | Est. effort |
|---|---|---|
| 1 | `source_radiation.py`, Render slots, blob v2 with per-line coefficients, C filters + ramp, presets endpoint, Source desk basic (preset, yaw/pitch drag, size), omni null + parity tests | main build |
| 2 | Size jitter; `level_ref` UI; `tail_follow` (Advanced); coefficient maths into shared C core (`src_radiation.c`) for 60 fps drag; SIMD bank | follow-up |
| 3 | Multi-point emission (cheap variant), roll, per-linked-instance sources in Studio One track-FX, CLF/GLL loudspeaker import, v2 model (frequency-limited dipole) for open-back combos, phoneme/voice variants (Pörschmann SOFA) | later |
