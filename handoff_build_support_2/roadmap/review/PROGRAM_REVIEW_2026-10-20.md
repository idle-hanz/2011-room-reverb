# Program review (read-only), 2026-10-20

> Change note 2026-10-20: first version. The scope was widened during the review from `render_pipeline.py` alone to the whole of `software\`. This file replaces the planned `RENDER_PIPELINE_REVIEW_2026-10-20.md`.

**Rules kept:** I edited no code, goldens or binaries, and I ran no pytest or renders. I read the files from a copy of the tree. Line numbers refer to the tree as it stood on 2026-10-20 at about 20:30 BST (PERROOMK pin, BLOOM not in the tree).

**Locked items, not flagged:** MOVEMENT_FORCED_OFF (`render_pipeline.py:812`), per-room k, the 1/r law, makeup frozen at the boot-source offset (`makeup_at_stand`, 1397–1450), BLOOM absent, and the shared tail being Live-only. Known items are cited, not re-reported: F10, F11, F13 (B bank uses A's physics sections), F14 (closed), the pytest stamp rotation (`publish_out_copy`, 3381), and backlog 3.10 (binaural gaps).

## Coverage (honest)

| Area | Depth |
|---|---|
| `render_pipeline.py` (3434 lines) | Read in full, line by line |
| `static/js/pack_room.js` | Read in full and compared with `pack_blob_v2` |
| `static/js/live_fdn.js` | `pushParams`, `start`, `decodeFile` and `attachSource` read |
| `static/js/fdn_worklet.js` | `_apply` read |
| `engine/live_stereo.c` | Blob loader (`load_core_body`, `live_load_room`), `sub_apply`, `fdn_excite`, `apply_harm` and `live_load_harm` read. The audio loop was only grepped. |
| `app_server.py` | `params_from_body`, `_render_impl`, `api_preview` and `api_render` read |
| `engine/fdn.py`, `early_field.py`, `surface_colour.py` | The functions that Render and Play call were read (delays, makeup, T60 gain, harmonic pack, fit_line_cascade). Not read in full. |
| The other engine `.py` files, `app.js` (3724 lines), the other JS, `index.html`, `.inc` files and tests | Grep-level only, for the wiring questions below. **Not reviewed in depth.** A full pass would need its own session. |

## Counts

- **Bug: 4** (B1–B4)
- **Risk: 6** (R1–R6)
- **Improvement: 6** (I1–I6)

## Bugs

### B1. The moving-path render is about 3.5 dB too quiet (OLA gain constant). Bug.
- **Lines:** `render_pipeline.py` 2307–2309 and 2401.
- **Evidence:** hop is 100 ms and frame is 200 ms, so the windows overlap by 50 %. The window is a symmetric Hann (`hann_window`, 328–331). Each block is the dry signal times the window (2386–2388), so the overlapped windows sum to about 1.0, not 1.5. `ola_comp = 2/3` (2401) then scales the whole wet signal by 0.667, which is −3.52 dB compared with the still path. The value is tagged ASSUMED in the code. I verified this by the maths, not by measuring a render.
- **Sound / goldens:** it changes the sound of moving-path renders only (`path_on` with a preset other than still). The still and two-source paths are not affected. I did not check whether any golden uses a moving path.
- **Fix:** compute `ola_comp = 1 / mean(sum of shifted windows)` from `win` and `hop`, or simply use 1.0 for 50 % Hann. Confirm with a dry-only A/B at a fixed source.

### B2. The moving path ignores `capsule_mm`. Bug.
- **Lines:** 2340–2384. The `combined_ir` call in the moving loop has no `capsule_mm=` argument, so it uses the default of 17.0 (1474). The still path (2138) and the two-source path (1946) both pass it.
- **Evidence:** read directly. `capsule_mm` drives the gradient high-pass and the beaming low-pass in `render_early_ir` (612, 617, 704–705).
- **Sound / goldens:** this only matters when the path is moving and the capsule is not 17 mm. It is unlikely to touch any golden.
- **Fix:** add `capsule_mm=capsule_mm` to that call. A shared helper (see I3) would stop this kind of drift.

### B3. Render does not do binaural; Play does. Bug, or a known gap (probably part of backlog 3.10).
- **Lines:** `render_pipeline.py` `_render_core` has no `mic_setup` parameter. `mic_setup` appears only in `live_fdn_params` (2812). The docstring of `render_binaural_fdn_ir` (1261) says "render() never calls this function". `app_server._render_impl` (1057–1165) does not pass `mic_setup`, `head_yaw_deg` or `binaural_preset`.
- **Evidence:** in Play, binaural uses `MicStand.binaural`, the binaural colour bank and the IC tail FIRs (2813–2818, 2834–2841, 3065–3070). In Render, the same scene goes through the ordinary L/C/R stand. The server sets centre gain to 0 for binaural (`app_server.py:544`), so Render produces a plain two-capsule stereo file with no HRTF. `app.js` disables some mic rows for binaural, but I found no guard on the Render button.
- **Sound / goldens:** a binaural Render does not sound like binaural Play. The goldens are probably not binaural (I did not verify).
- **Fix:** either route binaural through a Render path (stand, `BinauralColour`, `render_binaural_fdn_ir`), or block or label Render when `mic_setup` is binaural. Check against 3.10 first. If it is already listed there, this is a citation, not a new item.

### B4. `render()` designs the sub high-pass at 48 kHz when `sr` is passed by keyword. Latent bug.
- **Lines:** 2550–2554: `sr_hp = args[1] if len(args) > 1 else 48000`.
- **Evidence:** a call such as `render(dry, sr=44100, sub_hp=True, ...)` designs the 15 Hz Butterworth for 48 kHz. `app_server` passes `sr` by position, so the app is fine. Tests or harness scripts that use the keyword would get the wrong filter.
- **Sound / goldens:** no change through the app. At 44.1 kHz the high-pass would sit at about 13.8 Hz instead of 15 Hz.
- **Fix:** `sr_hp = args[1] if len(args) > 1 else kw.get("sr", 48000)`, or bind with the signature.

## Risks

### R1. No denormal flush in the sub-HP and ROOMTONE filter states (C/wasm). Risk.
- **Lines:** `live_stereo.c` `sub_apply` 2505–2513 and `apply_harm` 2288–2303. Compare `ls_flush` in the surf and air filters (563–576, 1409–1412, 2202–2203).
- **Evidence:** `fdn_excite` adds `LS_DC` *after* the high-pass (2519–2520), so the guard keeps the tank out of denormal range but not `subZ`. With silent input, the DF1 states decay towards the subnormal range. Wasm keeps subnormals, and on x86 they can be slow. `harmZ` filters the delayed line, which carries the DC guard, so it is probably safe. Treat that part as uncertain.
- **Sound / goldens:** no change to the sound. A possible CPU rise during long silences with `sub_hp` on, which is the server default. Not measured.
- **Fix:** wrap `*z1` and `*z2` with `ls_flush` in `sub_apply` (and in `apply_harm` for symmetry), then re-run the CPU gate and the `test_quick_pins` MD5s. The output should stay bit-exact unless values are subnormal.

### R2. `subZ` is not cleared when the sub high-pass is switched back on. Risk.
- **Lines:** `live_stereo.c` 1714 and 1803–1814. I found no `ls_zero(st->subZ…)`. `harmZ` is zeroed on toggle (1069, 1103).
- **Evidence:** when section 9 is absent, `subHpOn` is 0 and the states freeze at their last values. Turning it on again resumes from those stale states, which may give a small click. I did not see this in the audio.
- **Fix:** zero `subZ` when `subHpOn` goes from 0 to 1, the same way `harmZ` is handled.

### R3. The decay-lock gain uses different delays in Render and Play. Risk, size unmeasured.
- **Lines:** Render single-source 2104 and 2108, and two-source 1883 and 1888, use `fdn_delays_from_taps(..., channel="mean")` (the default, `fdn.py:814`). Play uses `channel="c"` (2914–2915).
- **Evidence:** `g` feeds the makeup (`ir_rms_makeup_from_inject` uses the √(1−(g√N)²) term, `fdn.py:535–541`) and Play's `g_decay`. When the centre capsule distance differs from the L/R mean, the makeup differs slightly between Play and Render. The unlocked T60 readout also differs: Render uses the mean channel, Play averages L, C and R (2869–2912). That is display only.
- **Sound / goldens:** possibly a small level offset between Play and Render, which may already be inside the parity tolerances. Changing either side moves goldens or MD5s.
- **Fix:** measure first (makeup Play against Render on boot, hall and a pose with the C mic forward). If it is not zero, pick one channel in both.

### R4. The Python and JS blob packers disagree on the `snap` default. Risk.
- **Lines:** `render_pipeline.py:3299` `d.get("snap", True)` against `pack_room.js:50` `data.snap ? 1 : 0`.
- **Evidence:** `live_fdn_params` never sets `snap`, so `pack_blob_v2(live_fdn_params(p))` packs snap=1. JS packs whatever `live_fdn.js:418` sets. The real page always sets it. Harness or MD5 tools that pack a live dict without `snap` get a different CORE float from JS with snap missing. Everything else in CORE, AIR, SURF, SRC and sections 6–9 matched line for line.
- **Fix:** make both default the same (and say which in the docstring), or always set `snap` in the live dict.

### R5. Play fades the loaded file in and out by 20 ms; Render does not. Risk for parity checks.
- **Lines:** `live_fdn.js` `decodeFile` → `fadeLoopSeam(…, 0.02)` (332–357).
- **Evidence:** this is deliberate for a click-free loop, but Play's input differs from Render's in the first and last 20 ms. A transient-onset Play/Render comparison at file start would show it.
- **Fix:** note it in the parity docs, or have parity harnesses skip the first 20 ms.

### R6. A direct spike beyond the IR length is clamped onto the last sample. Low risk.
- **Lines:** `render_listen_direct_ir` `_at` (1348–1350).
- **Evidence:** a delay past `n_samp` is moved to `n_samp−1` instead of being dropped. With `fdn_ms ≥ ir_length_ms` this probably cannot happen in normal use (uncertain for very short `ir_length_ms` in a large room).
- **Fix:** drop the spike when it is out of range, as `_apply_ir_at` does.

## Improvements

- **I1. Dead parameters and branches.** `mic_hp_on`, `mic_hp_hz` and `mic_proximity` are accepted by `_render_core` (1682–1685) and sent by `app_server` (1076–1079), but they are never used. `mirror_x` in `render_early_ir` (594) is unused on purpose (comment 626–627). `delays` in `render_fdn_ir` is deleted (1145). The `kmax > SURF_K_MAX` clamp (1020) is dead because `fit_line_cascade` never goes above 6 (`surface_colour.py:875`). Suggest removing them or marking them as legacy, so readers don't think they work. No sound change.
- **I2. Performance.** `_df1_columns` (1101–1114) is a per-sample Python loop over up to 12.5 s × 48 kHz for each of three buses whenever `sub_hp` is on (the default). This is likely a measurable share of Render time, though I did not time it. A C helper through the existing ziglang DLL, or a block-recursive form, would cut it. `apply_soft_limit` loops per hot sample in Python (451–461), which is fine unless a render limits heavily.
- **I3. Copied code.** `combined_ir` is called three times with about 45 identical arguments (2118–2163, 2167–2213, 2340–2384), and the two-source bus build in `live_fdn_params` (3009–3045) copies the A-bus build (2871–2911). B2 is exactly this kind of drift. Suggest one helper that builds the kwargs and one bus-builder function. Should be bit-exact.
- **I4. Render status estimate.** `app.js` `doRender` (3497–3503) estimates the FDN length from `decay_s` even when the lock is off. That's cosmetic only.
- **I5. Float WAV input.** `_pcm_bytes_to_float` (206–230) supports PCM only. A 32-bit float WAV (common from DAWs) fails with "Could not load WAV". Consider adding IEEE-float support.
- **I6. Tests.** I gave the tests a grep-level look only. F11's five stale or failing acceptance tests are still the main known weakness. The `*_draft.py` names (`test_t2`, `t3`, `t3b`, `t4b`, `t7`) suggest tests that were never promoted, and `test_s_audit_ui.py` still uses fixed `wait_for_timeout` waits (F10). I found no test for B1 (moving-path loudness against still), B2 or B3. Adding a moving-against-still level test would have caught B1.

## Top 10 (plain)

1. B1: moving-path renders come out about 3.5 dB quieter than still renders, because of a wrong overlap-add constant.
2. B3: Render ignores the binaural setting, so a binaural scene renders as plain stereo while Play is binaural.
3. R1: the new sub high-pass filter in Play has no denormal flush, which could raise CPU in silence.
4. R3: Render and Play work out the decay-lock gain from slightly different delays, which could give a small level difference.
5. B2: the moving path forgets the capsule size and always uses 17 mm.
6. B4: calling `render()` with `sr=` as a keyword designs the sub high-pass at 48 kHz.
7. R4: the Python and JS blob packers default `snap` differently. Everything else in the blob matches.
8. R2: switching the sub high-pass back on in Play resumes from stale filter states.
9. I2: the Python sub high-pass loop is probably a big share of Render time.
10. I3: three copy-pasted `combined_ir` calls are where bugs like B2 come from.
