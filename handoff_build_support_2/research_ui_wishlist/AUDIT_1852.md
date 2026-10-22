# AUDIT_1852: whole-app bug hunt (2011 Room Reverb tweak app)

Written 3 Oct 2026, 19:25 BST, by an audit worker on the box. **Read-only audit: nothing in software\ was changed, and the app on the PC was not touched.**

Baseline audited: the copy of the PC's software\ tree in /workspace/audit_1852/software. All MD5s matched the PC at copy time: wasm sha1 0c7fd78490ea…, WORKLET_VER 47, goldens 18:29. The app ran on the box at 127.0.0.1:7860. Headless Chrome (playwright) toured all 7 tabs (Room, Source, Mic, Mix, Space, Surfaces, Polar) in every Colour mode (Measured, User defined, Bypass) and in the 5 mic setups, at 1600 px and 390 px.

Tags: **VERIFIED** = reproduced on the box, with numbers or a shot. **ASSUMED** = read from the code but not reproduced.
**SOUND?** = whether the fix changes what you hear. Anything marked "DECISION" is for Idle to choose. Nothing here was applied.

This audit leaves out items already queued in REPORT.md §7 S-MIX: three independent mics, the routing desk with M/S, Width and S→+L/−R, the 2011 linear pan law, the source-plane badge stuck on MEASURED, the violet patches and cyan seam on the 3D stack, the MS figure-8 +/− marking, the two pytest fixture errors, and Measured per-mic graphs showing measured data.


## LOCKED decisions (Idle, 3 Oct 2026 19:29 BST, "all six")
All six sound decisions below are **LOCKED** and are queued as Part B of `S_AUDIT_PROMPT.md` (run after S-MIX). The safe fixes are Part A of the same prompt.

| ID | Audit item | Locked choice |
|---|---|---|
| D-AUD-1 | A7 | **LOCKED:** Mono centre = C mic only, L/R faders disabled (box: −10.66 dB total vs today, VERIFIED; no hidden compensation) |
| D-AUD-2 | A2 | **LOCKED:** Render length follows Decay (early + 1.5 × T60, cap 12.5 s) + 50 ms end fade |
| D-AUD-3 | A8 | **LOCKED:** one soft limiter in Play and Render + visible message |
| D-AUD-4 | A11 | **LOCKED:** 10 ms gain ramps on faders, phase and mute (Play) |
| D-AUD-5 | A13 (bit depth) | **LOCKED:** Render writes 24-bit WAV |
| D-AUD-6 | A5 | **LOCKED: H-1** (Idle 3 Oct 20:38): the engine uses per-mic heights (option b) for the direct sound, early reflections and tail inject levels; the tail's delay lines stay at the stand height (tail ≤ 0.42 dB, VERIFIED). The full version (tail up to 4.6 dB) is rejected. Research in `s_audit/heights_research/` |

**Correction to A2 (re-measured 19:50 with the harness `render_ir.py`, VERIFIED):** at the default Decay 1.8 s the old 1.5 s cut sits at −93 dB re peak. T30 is 1.755 s with the cut and 1.756 s without, so the default is effectively unaffected. The audible cases are Decay ≳ 3 s (Decay 4 s: cut at −68 dB, T30 3.40 → 3.98 s). The 1.66 s in the A2 table came from the cruder sanity-script estimate.

---

## A. Bugs (ranked)

### A1. Clicking Hall, then Studio (or Club), gives a nearly dry room with a 0.10 s decay. HIGH. VERIFIED. Fixing it restores the intended preset (a safe fix).
- Evidence: data/place_full.json, scripts/place_leak.py, scripts/place_live.py.
  - Studio clicked fresh: decay_lock true, decay_s **1.80 s**.
  - Hall, then Studio: decay_lock **false**, fdn_g 1, decay_s **0.104 s**. The Decay slider reads "0.10". /api/live_params confirms 0.104 s.
  - Other leaks from Hall into Studio: air_lp 0.25 (vs 0), diffusion_master −0.5 (vs −0.25), direct_wet 1 / fader_direct 0.5 (vs 0 / 0), car_omni 0.764, and the Hall surfaces (absorption, diffusion).
- Cause: `applyPlace()` (app.js about line 2533) only overwrites room size, positions, space and humidity. The Hall snapshot (app.js about lines 200–230) turns on the 2011 law (decay_lock=false, fdn_g=1). In a 5.6×2.8×7.2 m room that law gives a 0.1 s decay.
- Fix: each Place preset should set a **complete** state. Reset to the server defaults first, then apply the preset (decay_lock, decay_s, air, diffusion, faders, surfaces). "Studio" then always sounds the same whatever was clicked before. Studio clicked fresh is unchanged.
- Test gap: add a test that checks Place A→B equals B.

### A2. [D-AUD-2 LOCKED] Render cuts the reverb tail off at "IR length" whatever the Decay. HIGH. VERIFIED. Sound DECISION.
- Evidence: data/eng1.log, scripts/engine_sanity.py.
  - The FDN in Render runs for `fdn_ms = max(early_ms, ir_length_ms)` (render_pipeline.py line 1217) and is truncated at `keep = n_dry + fdn_ms` (line 1429). ir_length_ms defaults to 1500, and the UI maximum is 2000. Decay goes up to 8 s.
  - At Decay 8 s the impulse is hard-cut at 1.50 s while the tail is still at about −40 dB re peak, so every note's reverb is gated. Play has no cut and rings out, so **Play and Render disagree on long decays**.
  - Measured T30 is skewed low by the cut:

| Decay set | IR length | T30 measured | T20 |
|---|---|---|---|
| 1.8 s (default) | 1500 | 1.66 | 1.70 |
| 8 s | 1500 | 3.47 | 3.75 |
| 8 s | 2000 | 4.47 | 4.90 |
| Hall snapshot (readout 1.30) | 1500 | 1.13 | 1.89 (bent decay) |

- Recommendation: make Render's FDN length follow Decay, e.g. `max(ir_length_ms, 1.2 × T60)` capped at about 12 s, with a short (about 50 ms) raised-cosine fade at the end. Or turn IR length into "minimum length". This changes Render's sound on any Decay above about 1.2 s. The default case changes only below about −55 dB. Goldens for render_std would need a reason string.

### A3. At 390 px (phone) the Mic tab traps you: the Listen sidebar sits on top of the tab bar. HIGH. VERIFIED. Safe UI fix.
- Shot: **shots_audit_1852/audit_390_mic_sidebar_over_tabs.png**. elementFromPoint over all 7 tab buttons returns `panelListen`, so you can't tap your way off the Mic tab.
- Also at 390 px: the Space and Polar canvases are 565 and 517 px wide, so the page scrolls sideways (tour_390_meas_space.png). The header title and tagline wrap under the buttons. The Mix desk is 837 px wide inside a sideways scroller (tour_390_meas_mix.png). No `[hidden]` leaks at either width.
- Fix: below about 700 px, stack the sidebar under the stage (position static, no overlap), set canvases to `max-width:100%`, and shorten or hide the tagline.

### A4. The server freezes during a Render, for about 20 s. MEDIUM-HIGH. VERIFIED. Safe fix.
- Evidence: scripts/block_probe.py. With a Render running, `GET /api/defaults` took **19.1 s**; idle, it takes 0.003 s. The tour's page loads timed out twice while renders ran.
- While Render runs, Play parameter pushes (/api/live_params), polar plots, images and source preview all stall, so riding a slider during a Render does nothing until it finishes.
- Cause: the `async def` endpoints (app_server.py lines 605–1036) do CPU-heavy numpy work directly on the event loop.
- Fix: make them plain `def` (FastAPI runs those in a thread pool) or wrap the work in `run_in_executor`. One Render at a time, behind a lock. No sound change.

### A5. [D-AUD-6 LOCKED: H-1] Per-capsule heights are drawn but not heard. MEDIUM. VERIFIED. The safe fix is UI only; passing them through is a sound DECISION.
- With "Horizontally aligned" off, the Mic Side view lets you drag L, R and C to different heights (state my_l / my_r / my_c).
- `params_from_body` never reads them. /api/live_params gives a **byte-identical** result for my_l=0.3 and my_c=2.5 (hash cf263beba6, the same as the base; data/api_probe.log).
- Options: (a) safe: lock L/R/C height dragging to the shared `my` and show "heights are shared". (b) DECISION: pass the per-capsule heights through to the engine, which changes the image taps.
- Recommend (a) now and (b) only if Idle wants vertical arrays.

### A6. Binaural: Colour mode and the Side/Centre mic presets are shown but do nothing. MEDIUM. VERIFIED. Safe UI fix.
- Binaural with Measured vs Bypass, and with the side preset SM57 vs U87: all three give the identical live-params hash (6d046430f0).
- The sidebar still shows Colour mode, Horizontally aligned, Link angles, the Side/Centre SM57 presets and a C capsule with cardioid lobes. The source-plane meta reads "Shure SM57 — dynamic cardioid".
- Shot: **shots_audit_1852/audit_1600_binaural_sidebar_clutter.png**. Fix: hide those rows in Binaural (Idle's rule: each tab shows only relevant controls). Show "Head (KEMAR/HRTF)" in the meta instead.

### A7. [D-AUD-1 LOCKED] "Mono centre" still mixes the L and R capsules. MEDIUM. VERIFIED. Sound DECISION. Check that S-MIX covers it.
- The server has no notion of mono_c. Muting L changes the live params (9fa3b511ac to 973a5dfeae).
- Rendered output: L/R correlation 1.000, peak 0.143 vs ORTF 0.067 (about +6.6 dB), because three coincident capsules are summed at 0 dB.
- The Mic tab says L and R are "not used", but the Mix L/R faders still change the sound.
- Recommend: mono_c sends only C to both outputs, with L/R muted in the engine. S-MIX's three independent mics plus routing desk may make this fall out naturally; make sure its item 1 states it. This changes the sound: about −6.6 dB and a different colour in Mono centre.

### A8. [D-AUD-3 LOCKED] Render quietly turns hot mixes down by up to 6.7 dB. MEDIUM. VERIFIED. Sound DECISION. Showing a warning is safe.
- `clip_guard` (render_pipeline.py line 264) scales the whole file so its peak is 0.9. In the hot-fader case the burst render was scaled **×0.46 (−6.7 dB)** and the impulse ×0.83, with no message.
- Play instead soft-limits above 0.95, so hot settings sound louder and more squashed in Play than in Render.
- Recommend: safe now, show "Render normalised by −6.7 dB" in the status line. DECISION: pick one rule for both (e.g. the same soft limiter in Render, or no limiter in Play plus a clip LED).

### A9. Play keeps burning CPU after Stop. MEDIUM. VERIFIED by code. Safe fix.
- `LiveFDN.stop()` (live_fdn.js line 379) only stops the file source. The AudioContext, worklet and live_stereo keep running at full cost: about 2.2 ms per 2.667 ms block on Idle's PC, i.e. about 85 % of one core, forever.
- Fix: after Stop, wait for the tail to fall below about −90 dBFS (or 1.5 × Decay), then `ctx.suspend()`, and resume on Play. Or skip process() when the input and the state are silent. No audible change; this is only after the tail has died.

### A10. The audio thread allocates and copies big arrays while you drag. MEDIUM. VERIFIED by code. Safe fix (no sound change).
- In fdn_worklet.js the param blob is built with repeated `Array.concat` (lines 139, 169, 173), which is O(n²). Up to about 1.5 M IR floats are copied **on the audio thread** at every param push (every 45 ms while dragging).
- `_viewF()` (line 232) creates a new Float32Array view every call inside process() (lines 313–315).
- Risk: GC pauses and dropouts on slower machines.
- Fix: pack the blob in a Float32Array on the main thread and transfer it (zero-copy postMessage). Cache the heap views and recreate them only when memory.buffer changes.
- Gate: goldens must stay max-abs 0.

### A11. [D-AUD-4 LOCKED] No gain smoothing in Play (zipper noise or clicks when riding faders or toggling phase/mute). LOW-MEDIUM. VERIFIED code; audibility ASSUMED. Changes the sound only during moves.
- fdn_wet, direct_wet, makeup, the mic gains, pan and phase jump at the 128-sample block boundary. Unmuting the FDN also clears its tail.
- Fix: a 10–20 ms linear ramp per block on each gain. Steady state is unchanged, so goldens should stay max-abs 0 (verify).
- It's a small DECISION only because moves sound smoother.

### A12. The API accepts nonsense values. LOW. VERIFIED. Safe fix.
- data/api_probe.log results:
  - W=0 and W=−5 are accepted and produce params.
  - decay 1e6 is accepted, giving loop gain ≈1 (an endless tail).
  - A mic outside the room is accepted (makeup 8.4).
  - W=NaN returns a 500 ("cannot convert float NaN to integer").
  - W="abc" is silently ignored.
- The UI clamps most of these, but a bad preset file or a future scene-load could feed them in.
- Fix: one `clamp_body()` with the parameters.csv ranges and a 400 response with a readable message.

### A13. [D-AUD-5 LOCKED, bit depth] Render output file details. LOW. VERIFIED by code.
- `write_wav_stereo` (line 234) writes **16-bit with no dither**, so quiet tails truncate. Recommend 24-bit or float32 WAV. That's a tiny sound DECISION (it only affects the bottom bits).
- Each /api/render leaves a NamedTemporaryFile(delete=False) preview in /tmp that is never cleaned up (tweak_app.py line 129, app_server.py). Safe to fix.
- Every Render overwrites renders/out.wav, so there's no A/B history. Suggest out_HHMMSS.wav, keeping the last 10.
- /api/preview checks the path with `startswith(tempdir)` and no `resolve()`. Low risk (localhost only), but tighten it.

### A14. The combined-pattern 3D view is covered by the big room labels. LOW. VERIFIED. Safe UI fix.
- Shot: **shots_audit_1852/audit_1600_combined_mic_label.png**. The room-scale "Mic"/"R" sprites (room_3d.js makeLabel about line 426) cover the 17 cm capsules, and the lobes clip at the panel edge.
- Fix: hide the labels or scale them by distance in focus-mic mode, and fit the camera to the lobes' bounding sphere.

### A15. Status and errors are invisible on Mic, Space and Polar. LOW. VERIFIED. Safe UI fix.
- The Preview panel (status line and player) is hidden on those tabs. A Render or Play failure started there shows no message, and Play errors (e.g. live_params failed) vanish.
- Fix: a one-line status bar in the header on every tab.

### A16. Smaller items. LOW.
- Source floor view: the "Left" label overlaps "Length Z". VERIFIED in shot (tour_1600_meas_source.png).
- Omni source: the radiation polar draws nothing, and the "Beaming onset" text still shows. VERIFIED.
- Stale-response races: fetchImages and source_preview have no sequence guard, so a slow old reply can overwrite a newer one. polar already has a guard. ASSUMED.
- The worklet's `_fail` reports only the first error. VERIFIED by code.
- `static/js/fdn_worklet.js.orig` is a stale 1 Oct copy (dead file). VERIFIED in the box copy; on the PC ASSUMED.
- If mic_fitter/ is missing, the server still starts but every API call returns 500 ("repo root with software/ and mic_fitter/ not found") and the page looks alive but silent. Add a startup check that refuses to start, with a clear message. VERIFIED on the box before mic_fitter was added.
- favicon.ico 404. three.min.js deprecation warning (r150+). Neither is harmful. These were the only two console messages in the entire tour. VERIFIED.
- Manual `?v=` cache-bust numbers on scripts are easy to forget. Suggest using the file's mtime or hash server-side.
- Play's loop seam fades the first and last 20 ms of the file (fadeLoopSeam), so it's a Play-only transient difference from Render. That's known and by design, but worth a line in HANDOVER.

---

## B. Improvements (not bugs)

1. **Save/load scenes, undo and autosave.** VERIFIED absent (no localStorage, no undo, no preset UI). A reload loses everything. Suggest: Ctrl-Z/Ctrl-Shift-Z over state snapshots, autosave to localStorage, and "Save scene"/"Load scene" JSON going through the A12 clamp. No sound change.
2. **Master meter and clip LED on the Mix desk**, plus numeric pan readouts. No sound change.
3. **Advanced / Structure locks shows on every tab.** Move it to Space (or a gear menu) to match the "only relevant controls" rule. Hadamard already obeys it (Space only). VERIFIED.
4. **Turn the audit scripts into tests:** controls.py ("every visible control changes a posted param or is on the UI-only allow-list"), the 390 px tab-clickability check, and place A→B == B.
5. **Polar banner wording is jargon.** Plain words would help (e.g. "Each mic's pick-up shape, coloured by frequency").
6. **Question for Idle:** ORTF includes the C mic at 0 dB by default (the 2011 "477 fold"). That's probably intended. Confirm, or default C to −∞ for ORTF in S-MIX.

---

## C. Checked and fine
- **Frequency colours:** one shared freq_palette.js, red (low) to violet (high), is used by mic_desk, polar_field, room_3d, source_desk and colour_surfaces. No violations in code or shots. VERIFIED.
- **Engine sanity** (offline Render, box; data/eng1.log): default, decay 8 s, 8 s/IR 2000, Hall, Mono centre, Binaural and hot faders all have no NaN, no clipped samples, and impulse DC about 1e-5.
  - L/R balance is +1.2 dB on default, as expected from the off-centre source.
  - Binaural correlation is 0.08, as expected.
  - The C engine has a NaN/inf scrub and a denormal flush. VERIFIED.
- **Controls:** 211 visible controls were exercised. Every real parameter control changes the posted params. The "no change" ones are UI-only by design (view chips, polar toggles, colourRefMode) or test artefacts. A keyboard re-test confirmed pan and trim work. Surface sliders weren't exercised (the DOM is rebuilt on each change). VERIFIED.
- **Play vs Render parity** for the default and S5 cases is already gated by the S5 fix-up (tail ≤ 0.08 dB, t18 −71.8 dB). Not repeated here, apart from A2 (long decays) where they differ by design today.

## D. Test-suite gaps
None of these is covered today:
1. Render tail length vs Decay (A2)
2. Place A→B (A1)
3. Per-capsule heights (A5)
4. Binaural dead controls (A6)
5. Mono-C L/R (A7)
6. clip_guard reporting (A8)
7. The 390 px layout and tab clickability (A3)
8. Server responsiveness during a Render (A4)
9. API validation (A12)
10. Worklet allocations and post-Stop CPU (A9, A10)
11. The UI-control → param map (controls.py)

## E. Safe fixes vs decisions
- **Safe (UI or code only, no sound change):** A1 (restores the intended preset), A3, A4, A6, A9, A10, A12, A13 temp cleanup and filenames, A14, A15, A16, B1–B5. A5 option (a). The A8 warning.
- **Sound DECISIONS for Idle:**
  - A2 (Render tail length; recommend: follow Decay)
  - A7 (Mono centre = C only; recommend yes, via S-MIX)
  - A8 (one limiter rule)
  - A5 option (b)
  - A11 (ramps; recommend yes)
  - A13 bit depth (recommend 24-bit)

## Files
- Scripts and raw data: /workspace/audit_1852/scripts/, /workspace/audit_1852/data/ (tour.json, tour390.json, controls.json, eng1.log, api_probe.log, place_full.json, place_leak.json)
- Shots: shots_audit_1852/ next to this file (full set in /workspace/audit_1852/shots/)
