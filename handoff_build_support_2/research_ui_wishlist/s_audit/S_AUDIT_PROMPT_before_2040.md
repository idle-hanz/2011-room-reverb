# S-AUDIT: fixes from AUDIT_1852 plus the six locked sound decisions (PASTE-READY: new Build window, high effort, run only after S-MIX has landed)

Written 3 Oct 2026, 19:55–20:10 BST, on the box. Sources: `research_ui_wishlist\AUDIT_1852.md` (the audit) and `research_ui_wishlist\s_audit\` (the box measurements behind every number here).

Tags: **VERIFIED** = measured on the box, on the 0c7fd78490ea / WORKLET_VER 47 tree. **ASSUMED** = arithmetic or reasoning only. Build re-measures everything on the post-S-MIX tree.

**Decisions locked by Idle (3 Oct 2026, 19:29 BST, "all six"):**

| ID | Decision |
|---|---|
| D-AUD-1 | Mono centre = C mic only; the L/R faders are disabled in that setup |
| D-AUD-2 | Render length follows Decay, with a short fade at the end |
| D-AUD-3 | Play and Render treat hot mixes the same way, with a visible message |
| D-AUD-4 | Short gain smoothing on faders, phase and mute (Play) |
| D-AUD-5 | Render writes 24-bit WAV |
| D-AUD-6 | The engine uses per-mic heights (not a locked height drag) |

---

## Paste this into a new Build window (high effort)

> Hi Build. New session **S-AUDIT**, high effort. Prompt: `handoff_build_support_2\research_ui_wishlist\S_AUDIT_PROMPT.md` (everything below the line "Full prompt"). It runs **after S-MIX has landed**. Check the baseline in §0 first, and stop and report if S-MIX is not in the tree or the baseline tests fail. Do the Part A items, then the Part B items in the order given, with every gate. Then stop per §5.

---

## Full prompt

### §0 Baseline (print it first; stop if anything is off)
1. **S-MIX must be in the tree.** Print WORKLET_VER (S-MIX bumps 47 → **48**; ASSUMED until S-MIX reports), the wasm sha1, the `engine/live_stereo.c` sha1, the golden SHA1s and GOLDEN_META, and the harness, pytest and selfcheck counts.
   - Compare them with S-MIX's own final report.
   - If WORKLET_VER is still 47 or the S-MIX desk (Route chips, pair modes) is missing, **stop**: S-AUDIT is based on post-S-MIX code.
2. Line numbers below come from the 3 Oct 18:29 tree (wasm 0c7fd78490ea). S-MIX touches `render_pipeline.py`, `engine/fdn.py`, `engine/early_field.py`, `live_stereo.c`, `app.js`, `mic_desk.js` and the worklet. **Re-find every line.**
3. Run the full harness, pytest and selfcheck once before any edit and keep the log as the S-AUDIT baseline. The counts must never drop below it.
4. **Don't redo S-MIX items:** the palette, the badge, the stack top, the figure-8 ±, the pytest fixtures, the Each-mic measured graphs, the desk and the pan law.

### §1 Rules for the whole session
- **Part A is UI or code only.** The goldens must stay byte-identical after every Part A item (print the SHA1s). Play output max-abs 0 against the §0 baseline wasm on the harness scenes.
- **Part B items change the sound by design.**
  - Each one has an expected change. Measure it on the tree just before that item. If the measured change is outside the stated tolerance, **stop at that item**, keep the last passing state and report.
  - **Never loosen an existing gate.**
- **Goldens:** regenerate them **once, at the end** (§4), and only if a Part B item changed them. Expected (ASSUMED): every golden stays byte-identical, because the goldens use ORTF, flat heights, 3 s IRs, no automation and float files. If any golden changes, the item that changed it must be named and its numbers given.
- Every new test goes into pytest or the harness, with no skips and no xfails added.
- **CPU (D-S5c-2 paired method):** 12 alternating rounds on the PC, the §0 baseline wasm against the S-AUDIT wasm, t19 scene, per-block medians.
  - **Shared off:** median ≤ **2.40 ms**, and the paired median rise ≤ **+1.0 %**.
  - **Shared on:** median ≤ **2.133 ms**.
  - Report every round.

---

### §2 Part A: safe fixes (no sound change, goldens byte-identical)

**A1. Place presets set a complete state** (AUDIT A1). VERIFIED bug: Hall → Studio gives decay_lock false, fdn_g 1 and **decay 0.104 s** (Studio clicked fresh: 1.80 s). Hall's air_lp 0.25, diffusion_master −0.5, direct fader 0.5, car_omni 0.764 and surfaces also leak in.
- **Fix:** `applyPlace()` (`app.js` about line 2533) resets to the server defaults (`/api/defaults` plus the default surfaces) and then applies the preset.
  - Give Studio and Club explicit `decay_lock: true` and `decay_s`. Studio is 1.8, as clicked fresh today. Club is whatever it is fresh today: print it and don't change it.
  - Hall keeps `applyReaktorSnapshot()`.
- **Gate:**
  - For all 9 orders X → Y (X, Y in Studio, Club, Hall), the posted `params_json` equals that of Y clicked fresh (ignore `_` keys). Use a Playwright test with a stubbed `/api/render`. The method is `s_audit\decision_measure\place_leak.py`.
  - Studio fresh decay_s = 1.80.

**A2. Phone width (390 px) layout** (AUDIT A3; shots `shots_audit_1852\audit_390_mic_sidebar_over_tabs.png`, `tour_390_meas_space.png`, `tour_390_meas_mix.png`).
- **Fix:** below 700 px, stack the sidebar under the stage with no overlap. Set canvases to `max-width:100%`. Wrap or shorten the header tagline. The Mix desk may scroll inside its own box.
- **Gate:** Playwright at 390×844, every Colour mode, every tab:
  - `elementFromPoint` at the centre of each of the 7 tab buttons returns that button;
  - `document.documentElement.scrollWidth ≤ 391`;
  - the sidebar and stage rectangles don't intersect;
  - 1600 px screenshots are pixel-identical to before, outside the changed CSS (or show the diff).

**A3. The server stays responsive while rendering** (AUDIT A4). VERIFIED: with a Render running, `GET /api/defaults` took **19.1 s** (idle: 0.003 s).
- **Fix:** turn the CPU-bound `async def` endpoints (`app_server.py` about lines 605–1036: geometry, live_params, images, source_preview, render, colour, polar) into plain `def` (FastAPI threadpool), or wrap the heavy part in `run_in_executor`.
  - Only one Render at a time, behind a lock. A second Render returns `{"ok": false, "error": "render busy"}` and the UI shows it.
- **Gate:** a test that starts a Render and meanwhile times `/api/defaults` (< 0.5 s) and `/api/live_params` (< 1.0 s). Render output max-abs 0.

**A4. Binaural sidebar shows only controls that do something** (AUDIT A6). VERIFIED: in Binaural, Measured vs Bypass and side preset SM57 vs U87 give an identical live-params hash.
- **Fix:** in Binaural, hide Colour mode, Horizontally aligned, Link angles, the Side/Centre preset pickers and the C capsule. The source-plane meta reads the head preset (e.g. "SADIE2 KU100 head"), not "Shure SM57".
- **Gate:** the hidden-state audit is 0 leaks, and a Playwright check confirms those rows are hidden in Binaural and visible in the other setups. live_params JSON is unchanged.

**A5. Play stops costing CPU after Stop** (AUDIT A9). VERIFIED (code): `LiveFDN.stop()` only stops the source, so the worklet keeps running at full cost.
- **Fix:** after Stop, wait for 1.5 × the current decay (or until the output RMS stays below −100 dBFS for 0.5 s), then `ctx.suspend()`. Resume on Play.
  - A Play pressed during the wait cancels the suspend.
  - The tail is never cut while it is above −100 dBFS.
- **Gate:**
  - A Playwright test confirms `ctx.state === "suspended"` after the wait and a clean restart.
  - Play goldens byte-identical.

**A6. No allocations or big copies on the audio thread** (AUDIT A10). VERIFIED (code): `fdn_worklet.js` builds the blob with repeated `Array.concat` (about lines 139, 169, 173), copies the IR blob on the audio thread at every param push (every 45 ms while dragging), and `_viewF()` (about line 232) creates new `Float32Array` views inside `process()` (about lines 313–315).
- **Fix:**
  - Pack the blob into one `Float32Array` on the main thread and post it as a transferable.
  - Cache the heap views and rebuild them only when `memory.buffer` changes.
  - Delete `static/js/fdn_worklet.js.orig` if it is present (a stale 1 Oct copy; it exists in the box copy, on the PC ASSUMED).
- **Gate:**
  - Play goldens byte-identical, harness Play scenes max-abs 0.
  - A grep shows no `concat` and no `new Float32Array` inside `process()` or `_apply`.
  - Report the time per param push (main-thread pack plus the worklet apply) before and after while dragging.

**A7. API input validation** (AUDIT A12). VERIFIED today:
- W=0 and W=−5 are accepted;
- `decay_s=1e6` is accepted, giving loop gain ≈1 and an endless tail;
- a mic outside the room is accepted (makeup 8.4);
- W=NaN returns HTTP 500;
- W="abc" is silently ignored.

**Fix:** one `clamp_body()` using the ranges in `parameters.csv`. Out-of-range numbers are clamped and listed in a `warnings` field. Non-finite or non-numeric values return HTTP 400 with the key name.

**Gate:**
- pytest cases for each input above;
- default body hash unchanged, goldens byte-identical.

**A8. Render file hygiene** (AUDIT A13; the bit depth is D-AUD-5).
- Delete the per-render temp preview (`tweak_app.py` about line 129, `NamedTemporaryFile(delete=False)`) when the next render replaces it, and at shutdown.
- Write `renders/out_YYYYMMDD_HHMMSS.wav`, keep the last 10, and keep `out.wav` as a copy of the newest.
- In `/api/preview`, use `Path.resolve()` plus an `is_relative_to(tempdir)` check.
- **Gate:**
  - A pytest confirms that after 12 renders there are ≤ 10 files plus out.wav and ≤ 1 temp preview.
  - A `../` path returns 403.
  - Audio bytes are unchanged.

**A9. The combined-pattern 3D view isn't covered by room labels** (AUDIT A14, shot `shots_audit_1852\audit_1600_combined_mic_label.png`).
- **Fix:** in focus-mic mode, hide the room-scale label sprites (`room_3d.js` makeLabel, about line 426) or scale them by camera distance, and fit the camera to the lobes' bounding sphere.
- **Gate:** a screenshot showing all capsules and lobes unclipped and no label over any capsule.

**A10. A status line on every tab** (AUDIT A15). The Preview status is hidden on Mic, Space and Polar, so errors there are invisible.
- **Fix:** a one-line status in the header, visible on all 7 tabs, fed by the same `statusEl` messages.
- **Gate:** a Playwright test that forces a live_params error on each tab and checks the text is visible.

**A11. Small items** (AUDIT A16):
- (a) Source floor view: the "Left" label overlaps "Length Z" (shot `shots_audit_1852\tour_1600_meas_source.png`).
- (b) Omni source: the radiation polar draws nothing, so draw a circle; hide "Beaming onset" for omni.
- (c) Add sequence guards to `fetchImages` and `source_preview`, as polar has, so a late reply can't overwrite a newer one.
- (d) The worklet `_fail` reports each distinct error, rate-limited, not just the first.
- (e) At startup, refuse to start with a clear message when the sibling `mic_fitter/` is missing. Today every API call returns 500 and the page looks alive (VERIFIED on the box).
- (f) Add a favicon.
- **Gate:** a screenshot for (a) and (b), a unit or Playwright test for (c)–(e), and goldens byte-identical.

**A12. Turn the audit scripts into tests:**
- **Control map** (`audit_1852` `controls.py` method): every visible control changes a posted param, or is on an explicit UI-only allow-list (view chips, polar toggles, colourRefMode).
- Place A→B (A1).
- 390 px tab clickability (A2).
- Server responsiveness (A3).
- API validation (A7).

---

### §3 Part B: the six locked sound decisions (run them in this order)

All before/after numbers are measured on the tree just before the item. The stated tolerances are stop lines.

#### B1 = D-AUD-5: Render writes 24-bit WAV
- **Do:**
  - `write_wav_stereo` (`render_pipeline.py` about line 234) writes 24-bit PCM (format 1, 3 bytes per sample, block align 6), round to nearest, no dither. 24-bit quantisation is about −144 dBFS (ASSUMED).
  - The same applies to the preview file, and to the Gradio path if it still writes WAVs.
- **Expected change:** only quantisation.
  - Today's 16-bit error is about −101 dBFS RMS (ASSUMED, LSB/√12).
  - Tails below −96 dBFS now survive instead of being truncated.
  - f32 goldens are unaffected (they come from the float render).
- **Gates:**
  - Header fields correct.
  - The decoded WAV nulls against the float render at ≤ **−135 dB**.
  - Chrome's `<audio>` loads and plays it: a Playwright check that duration > 0 and there is no media error.
  - The file is 1.5× the old size.
- **Stop if** the browser preview fails to play 24-bit.

#### B2 = D-AUD-2: Render length follows Decay, with a short end fade
- **Today** (VERIFIED): the Render FDN runs for `fdn_ms = max(early_ms, ir_length_ms)` (`render_pipeline.py` about line 1217) and is truncated at `keep = n_dry + fdn_ms` (about line 1429). ir_length_ms defaults to 1500 and the UI maximum is 2000. Decay goes up to 8 s. Play has no cut.
- **Do:**
  - `fdn_ms = max(early_ms, ir_length_ms, early_ms + 1500 × T60_s)`, capped at **12 500 ms**.
    - T60_s is the effective decay: `decay_s` when decay_lock is on, else the 2011-law decay readout (`live_params` `decay_s`).
    - 1.5 × T60 puts the end about 90 dB below the tail start (ASSUMED).
  - End with a **50 ms raised-cosine fade** on the FDN tail (and on the whole output if the dry is shorter).
  - The UI "IR length" becomes "Minimum IR length". Keep its range and default.
  - `makeup` doesn't depend on ir_length_ms (VERIFIED: the argument is deleted in `ir_rms_makeup_from_inject`), so levels don't move.
- **Expected change** (box, harness `render_ir.py`, standard measure body, `s_audit\decision_measure\len_mono.json`, VERIFIED):

| Case | Old / new length | First 1.5 s | Old cut level re peak | Added energy (of total) | T30 old → new |
|---|---|---|---|---|---|
| Decay 1.8 s (default) | 1500 / 2800 ms | max-abs **0** | −93.0 dB | −58.1 dB | 1.755 → 1.756 s |
| Decay 4 s | 1500 / 6100 ms | max-abs **0** | −68.3 dB | −29.8 dB | 3.398 → 3.983 s (set 4.0) |
| Decay 8 s | 1500 / 12 100 ms | — | — | — | about 3.5 → about 7.9 s (ASSUMED; the audit measured 3.47 at 1.5 s IR) |

- **Correction to AUDIT A2:** the default decay is effectively **not** affected (the cut was at −93 dB). The audible cases are Decay ≳ 3 s.
- **Render time** grows linearly (VERIFIED box: 23 → 46 s for 2.8 s, 24 → 96 s for 6.1 s; Decay 8 s about 190 s, ASSUMED). Show progress text, and make sure A3 keeps the app responsive.
- **Gates:**
  1. For decays 1.0, 1.8, 4 and 8 s, Render T30 (EDC −5…−35 dB) is within **±5 %** of Play's T30 on the same scene (Play via the harness wasm, offline).
  2. The last 50 ms of the file are ≤ −90 dB re peak.
  3. No click at the end: the sample-to-sample step in the last 100 ms is ≤ 1e-5.
  4. The first 1500 ms are max-abs 0 against the pre-item tree for decays 1.8 and 4 s.
  5. Harness goldens: the harness passes ir_length 3000, so 1.8 s renders are unchanged (ASSUMED). Any golden that changes is listed with its null.
- **Stop if** gate 1 fails by more than ±5 % or any render goes over 12.5 s.

#### B3 = D-AUD-3: one rule for hot mixes, plus a visible message
- **Today** (VERIFIED):
  - Render `clip_guard` (`render_pipeline.py` about line 264) scales the **whole file** to a peak of 0.9. The hot-fader burst was scaled **×0.46 (−6.75 dB)** and the impulse ×0.83, with no message.
  - Play applies `soft_limit()` per sample (`live_stereo.c` about line 431: identity up to 0.95, smooth knee to 1.0).
- **Do:**
  - Render applies **the same `soft_limit()`** per sample at the output. Port it to Python bit-for-bit in float64.
  - Remove the whole-file scaling. A hard ±1.0 clip remains only inside the int conversion.
  - **Message in both engines:** "Limiter: peak reduced by x.x dB (n samples)".
    - **Render:** from counters returned in the render JSON (`limiter_db`, `limiter_samples`), shown in the status line.
    - **Play:** the worklet reports the max gain reduction per 100 ms through a preallocated message (no allocation), shown as a limiter badge or LED next to Play live that holds for 2 s.
- **Expected change:**
  - Below a 0.95 peak nothing changes. Default peaks are 0.067 for the impulse and 0.32 for the burst (VERIFIED), so the defaults and goldens are byte-identical (ASSUMED; the harness `render_ir.py` already undoes clip_guard).
  - Files with peaks between 0.9 and 0.95 are no longer scaled: up to +0.46 dB louder (ASSUMED, 20·log10(0.95/0.9)).
  - Hot mixes (fader sum over the limit) come out about **+6.7 dB louder RMS** than today's Render, with peaks limited instead of the whole file turned down (ASSUMED from the VERIFIED ×0.46). Render and Play then match.
- **Gates:**
  1. The Python `soft_limit` matches wasm `live_soft` on 10 000 points in [−4, 4] within 1e-7.
  2. Hot-fader scene (all bus faders +12 dB, burst input): the Play and Render outputs' RMS agree within **0.5 dB** and peaks are ≤ 1.0. Both messages appear (Playwright for Play, JSON plus status for Render).
  3. Default scenes: no message, goldens byte-identical.
- **Stop if** gate 2 differs by more than 0.5 dB.

#### B4 = D-AUD-4: short gain smoothing in Play
- **Today** (VERIFIED, code): fdn_wet, direct_wet, early_wet, makeup, mic gains, pan, phase and mute jump at the 128-sample block boundary, and unmuting the FDN clears its tail. After S-MIX the pan and route weights live in the `w` matrix.
- **Do:**
  - **10 ms linear per-sample ramps** (480 samples at 48 kHz, scaled by the sample rate) on every gain the desk applies: bus wet and faders, makeup, per-mic gains, the `w` matrix entries (pan, route, Width), phase, and mute/solo.
  - Phase flips ramp through 0. Mute ramps to 0. A new target restarts the ramp from the current value.
  - **At init the gains start at their targets (no ramp)**, so offline renders and goldens are untouched.
  - The FDN keeps running while muted: the mute is an output ramp, no state clear. Report its CPU.
  - Render is static and unchanged.
- **Expected change:**
  - Steady state: **max-abs 0** (VERIFIED by design target, ASSUMED until measured).
  - During moves: no more steps.
- **Gates:**
  1. Play goldens byte-identical, harness Play scenes max-abs 0.
  2. Step test in the harness wasm: a 1 kHz sine with a phase flip on C, and separately a 0 → +6 dB fader jump. The largest sample-to-sample jump is ≤ 1.5× that of the sine itself. The energy above 5 kHz in the 50 ms around the event is ≤ **−60 dB** re the sine (today: a step, ASSUMED well above that; report it).
  3. FDN unmute after 2 s keeps the tail: the RMS right after unmute is within 1 dB of the never-muted run.
  4. t19 paired, shared off: ≤ +1.0 % rise.
- **Stop if** gate 1 or gate 4 fails.

#### B5 = D-AUD-1: Mono centre = C only, L/R faders disabled
- **Overlap with S-MIX item 3** (three independent mics, desk presets). **First re-check:**
  - Load Mono centre on the post-S-MIX tree.
  - Render it, then render it again with the L and R strips muted.
  - If they null at ≤ −100 dB, S-MIX already made Mono centre C only. Record "fixed by S-MIX", then do only the UI part and the tests below.
- **Today** (pre-S-MIX, VERIFIED): the server has no notion of mono_c. The L and R capsules (coincident, 0 dB faders) are mixed in, and the L/R faders change the sound even though the Mic tab says "not used".
- **Do:**
  - The Mono centre setup's desk preset is C only. The L and R strips are off in the engine and **disabled in the UI** (greyed, not hidden, with a "Mono centre uses only C" tooltip).
  - C keeps its normal route (Centre, 2011 linear law: ½ to each side, the same as the C strip in ORTF). **No hidden level compensation.** Idle can raise C's fader, and S-OUT's auto level handles loudness later.
  - Leaving Mono centre restores the L/R strips as they were.
- **Expected change** (box, standard measure body in mono_c geometry, L/R gains 0 vs 1, `len_mono.json`, VERIFIED):
  - total **−10.66 dB**, early −10.74 dB, tail −9.54 dB in every band, peak −10.76 dB;
  - early ⅓-octave −10.5 … −11.1 dB (−12.3 dB at 125 Hz);
  - L/R stay identical (correlation 1.0).
  - If S-MIX's Mono centre preset differs (e.g. C routed Both at 0 dB), print its level against this table and report it. Don't add compensation.
- **Gates:**
  1. Mono centre with L/R faders moved to any value is max-abs 0 against the faders at default (they're inert).
  2. The level change against the pre-item tree is within ±0.3 dB of the table, or 0 if S-MIX already fixed it.
  3. Every other setup at defaults is byte-identical.
  4. A Playwright check that the L/R strips are disabled in Mono centre and enabled elsewhere.

#### B6 = D-AUD-6: the engine uses per-mic heights
**Research** (box, 3 Oct 19:30–19:55, `s_audit\heights_research\`, README and LISTENING_CHECKLIST there):

- **Overlap with S-MIX item 4.** It says per-mic positions, height included, go through `MicStand`, early taps and FDN inject. **First re-check** what S-MIX did:
  - Does the Mic Side-view drag of L, R and C (state `my_l` / `my_r` / `my_c`; `mic_desk.js` `applySideDrag` about lines 957–985) now reach the engine?
  - Does `align_horizontal` still pair L/R?
  - Which height do the FDN line lengths use?
  - Today none of the drags reach the engine except C's (it also writes `my`). That was VERIFIED: `my_l=0.3` and `my_c=2.5` give a byte-identical live_params hash.
- **Design (recommended: H-1):**
  - Each capsule's Y is its own absolute height (`my_l`, `my_r`, `my_c`, defaulting to `my`, clamped to [0.02, H − 0.02] m). `my` stays the stand and C height.
  - The heights enter `mic_positions()` and the C centre in `compute_taps` (`engine/early_field.py` about lines 1218–1232 and 1643–1648). From there they flow, with no new code paths, into:
    - each image tap's 3D distance → delay;
    - 1/r²;
    - the arrival angle **including elevation** (so cardioid off-axis gain and the off-axis shelf apply);
    - the **direct path** (the n = (0,0,0) tap per capsule);
    - the per-bus inject levels.
  - **The FDN line lengths, line diffusers and line air keep the stand reference height `my`** (`engine/fdn.py` `_tap_distance` callers, about lines 188, 756 and 1087). Then a capsule drag doesn't swing the tail ±4 dB in single bands, and Play's delay lines don't change length while dragging.
  - **Coincident M/S (`ms_decode` or an S-MIX M/S pair with S coincident) and binaural ignore per-capsule heights.**
  - `align_horizontal` on keeps L = R height.
- **Box results** (all VERIFIED):
  - **Back-compat:** with no per-capsule heights, the Play params JSON is identical (0 fields differ) and the Render IR is max-abs 0.
  - **Structure:** image taps already carry per-capsule distance, delay and level, and Play already has one delay set per bus. Heights add **no taps, lines or blob fields**.
  - **CPU:** box Node-wasm t19, 6 alternating rounds, tilt vs flat. Shared off: paired median **−1.15 %** (1.8938 vs 1.9175 ms). Shared on: −0.62 %. Both are noise. PC expected 0 (ASSUMED).
  - **Sound** (Render, guitar, level-matched, standard body):

| Case (L / C / R m) | Early ⅓-oct worst Δ | Early broadband L / R | Tail ⅓-oct worst Δ, H-1 | Tail worst Δ, full model | Level trim to match |
|---|---|---|---|---|---|
| pair up 0.5 (2.0 / 1.5 / 2.0) | 9.2 dB (H-1), 8.4 dB (full) | −1.17 / −0.58 dB (H-1) | **0.42 dB** | 3.88 dB | +0.36 dB (H-1) / −0.31 dB (full) |
| tilt 0.6 (1.2 / 1.5 / 1.8) | 9.7 dB (H-1), 9.9 dB (full) | −0.69 / −0.46 dB (H-1) | **0.24 dB** | 3.93 dB | −0.44 dB (full) |
| pair up 1.0 (2.5 / 1.5 / 2.5) | 8.7 dB (full) | −0.61 / +0.11 dB (full) | not run | 4.56 dB | +2.33 dB (full) |
| reference: today, whole stand +0.5 m | — | — | — | 3.89 dB | — |

  - Direct timing in tilt: L 2 samples earlier, R 6 samples later. Early L/R correlation 0.435 → 0.394.

**Do:**
- Implement H-1 on top of S-MIX's per-mic `MicStand` positions: the per-capsule Y as above, and FDN line distances from the stand reference.
- Wire the Side-view drags so they move what you hear, in Play and Render.
- Add a `height` readout per capsule.

**Gates:**
1. Flat heights: goldens byte-identical, Play params JSON identical, Render IR max-abs 0.
2. Image-tap delays match the 3D geometry for each capsule to 1 sample (pytest on 4 heights).
3. Tilt 1.2 / 1.5 / 1.8 against flat on the standard body, Render:
   - tail ⅓-octave |Δ| ≤ **0.5 dB** in every band;
   - early broadband within ±0.3 dB of the table above (L −0.69, R −0.46 dB).
4. Play against Render with the same heights: tail ⅓-octave |Δ| ≤ 0.1 dB, and the S5 early-parity gates as locked in D-S5c-4.
5. M/S coincident and binaural with heights set are byte-identical to without.
6. t19 paired, shared off: ≤ +1.0 %.

**Stop rule for B6:** if S-MIX already made the FDN lines follow per-capsule positions, **don't change that**. Report it with tail numbers for the tilt case and stop B6 at that point: changing it is a design choice for Idle. If gate 3 fails, stop and report.

---

### §4 Goldens and HANDOVER
- Regenerate goldens only if a Part B item changed one. Print the SHA1s before and after, plus the max-abs and null for every file.
- Store this exact reason, **keeping only the IDs that changed a golden**:
  > `D-AUD-1..6 (S-AUDIT, Idle 3 Oct 2026 19:29): D-AUD-1 Mono centre = C only (L/R strips off); D-AUD-2 Render length = max(min IR, early + 1.5*T60) capped 12.5 s + 50 ms fade; D-AUD-3 shared soft_limit in Render + limiter message (clip_guard scaling removed); D-AUD-4 10 ms gain ramps in Play (init at target); D-AUD-5 Render 24-bit PCM; D-AUD-6 per-mic heights (H-1: early + direct + inject, FDN lines at stand height)`
- GOLDEN_META names the shipped C file and wasm SHA1s. HANDOVER gets one section per item, with the measured numbers.

### §5 Report, then stop
**Report:**
- §0 baseline;
- every Part A gate;
- for each Part B item, the expected vs measured table;
- golden SHA1s;
- t19 paired rounds (shared off and on);
- harness, pytest and selfcheck counts;
- screenshots (A2 at 390 px for all tabs, A4, A9, A11 a/b, the B3 limiter message in both engines, the B5 disabled strips, the B6 Side view with readouts).

**Stop rule:**
- Do §2 and §3 only. No S-OUT, scatter, smear or save/load scenes (AUDIT B1, a later session).
- Don't change `g`, the per-line loss, the shared-tail logic, the SURF cascade or the S-MIX desk law.
- If a gate fails, stop at that item, keep the tree at the last passing state and report. Don't loosen a gate.
- A bare "continue" starts nothing new.
