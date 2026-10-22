# AMBIENCE + RUMBLE + CLEAN LISTENS (2026-10-18)

Read START_HERE / HANDOVER Current pin (2026-10-17, SMALLDECAY) first. That pin is the baseline: WORKLET_VER 57, app.js?v=60, wasm d2dddc2f..., five TLAW goldens, GOLDEN_META 883cc7329582c21532fb44dbd040145e0ce7bc6e, empty MD5 af2b154a1e8f806d98a87e5e2e846022, stored-centre MD5 f30665f446a3c5163cafb8331909e1db, decay-8 cube ceiling 2.40 ms shared-off.

Read `roadmap\smalldecay\DISTORTION_DIAG_2026-10-18.md` before anything. Its findings drive this run.

## Why (Idle, 2026-10-18)
- Idle heard distortion and artifacts in the SMALLDECAY listens. The diagnosis: (1) the test guitar has a DC offset (-0.0046) plus drift under 5 Hz, which the tank boosts with nothing removing it. That causes all the 3x4 clipping and lost headroom everywhere. (2) The test guitar has splice clicks at exact 0.5 s marks. Both are pre-existing. `_on` exposes them more.
- Idle likes `phys_ceiling` on as "nice and natural", but it "loses a lot of the reverb". He wants to still be able to add a lot of ambience when he chooses.
- Idle chose (widget, 2026-10-18): the rumble filter goes in **behind its own switch, default off**. No default flips and no golden re-pins in this run.

## Hard rules
- Every new key defaults OFF. With all new keys off and `phys_ceiling` off, everything stays bit-exact: five TLAW goldens max-abs 0, GOLDEN_META not rewritten, both live MD5s identical, and the live dict grows no key (the MD5s hash the whole dict). Any move is a STOP.
- `phys_ceiling` stays default off. Do not flip any default. Do not re-pin goldens.
- CPU: decay-8 cube (shared off, two sources, colour on, Surfaces on) at or under 2.40 ms, with every new key off AND with all of them on. Over is a STOP. Do not raise the ceiling.
- A WORKLET_VER / app.js bump is allowed only if a browser-loaded file changes. Update the asserts in `tests/test_quick_pins.py` with it. That is not a golden re-pin.
- Do not retune 1/r, SRCDIST, D-PROX, Smooth, the limiter, 0.7, the 0.55 fold, Surfaces, PLACE, ROOMTONE (HARM_Q 8, HARM_DB -0.3, HARM_MAX 16), makeup, `g_decay`, or the decay lock with the keys off. Do not start SL4, Phase 4 or Movement.
- Play and Render must match (one shared function per feature, same as `phys_ceiling_pack`).

## Step 1 - Backup
`software_backup_2026-10-18_preAMBIENCE.zip`, excluding `.venv` and `__pycache__`.

## Part 1 - Clean, saved listen harness
1. The script that made the SMALLDECAY listens was not found. Write one and keep it: `handoff_build_support_2\roadmap\smalldecay\make_listens.py`, reproducing the method in `smalldecay\listen\listen_report.json` (first 8 s of the guitar convolved with `render()` of a unit impulse, PLACE positions, Flat, lock 1.8 s, early 0, direct 0). Check it reproduces the existing `_off` files before changing anything. Report the null.
2. Make a cleaned copy of the test guitar. Never overwrite the original. Remove DC, high-pass zero-phase at 20 Hz, and repair the 0.5 s splice clicks with short crossfades (about 5 ms). Or, if the clicks can't be repaired cleanly, pick a click-free 8 s stretch of the same take. Save it next to the original with `_clean` in the name. Report its peak, DC, energy under 20 Hz, and the largest sample-to-sample jump before and after.
3. The listen output reports sample peak, true peak (4x oversampled), limiter dB and limited-sample count, DC, energy under 20 Hz, and octave T60 (63 Hz-4 kHz), per file. All new listens use the clean guitar.

## Part 2 - Rumble filter, key `sub_hp`, default off
- A 2nd-order Butterworth high-pass at 15 Hz on the signal **entering the FDN tank** (the injects), once per bus, outside the loop. It does not touch direct or early sound. It is not a filter on every bounce.
- If the diagnosis shows DC also being generated inside the loop (not just entering), report it and STOP rather than putting a filter in the loop.
- Same filter in Play (wasm) and Render. Key off: no filter state is created or run, so bit-exact.
- Measure: with `sub_hp` on, the output DC and energy under 20 Hz per room, and whether the 3x4 room still trips the limiter (with the original guitar, to prove the filter alone fixes it, and with the clean guitar).

## Part 3 - The long bass with `phys_ceiling` on
SMALLDECAY measured the boot room at 2.08 / 2.34 / 2.16 s at 63 / 125 / 250 Hz with the key on, against `T_eff` 1.8 s, and longer than the key-off file. First re-measure with the clean guitar and `sub_hp` on. The sub-5 Hz drift may have inflated the T20 readings.
- If the low bands then sit within T60_TOL (0.08 relative) of `T_eff`, report it and change nothing.
- If they are still long, find why (section fit, the 63 Hz clamp, the identity fallback on left bus line 20, interaction with the kept axial peak) and fix it inside `phys_ceiling_pack` so no band decays slower than `T_eff`. If the fix needs a design choice, STOP and report the options.

## Part 4 - Ambience: the Decay dial sets how hard the walls are (only when `phys_ceiling` is on)
Idle wants the natural sound of `phys_ceiling`, but still able to dial in lots of reverb. The mechanism:
1. The dial no longer acts as a hard ceiling when `phys_ceiling` is on. Instead it sets one **wall hardness** factor `k` that scales the absorption of every face: `alpha'(f) = clamp(k * alpha(f), ALPHA_MIN, 0.99)`, with `ALPHA_MIN` 0.01.
2. `k` is set from a fixed **reference room**, the boot 6x3x8 with the current cards: solve for `k` so the reference room's physical 500 Hz-1 kHz mean T60 (from `room_target`, air on, humidity 0.35) equals the dial. Use the same `k` in every room size. So a small room stays short at the same dial (physics: T scales with volume over surface), a big room rings longer, and turning the dial up makes every room livelier. Air absorption keeps the highs dying first.
3. Per-octave target in the loop: `T_eff(f) = T_phys(f; k)`, with no `min(dial, ...)`. If `k` hits the `ALPHA_MIN` floor on any face, report the longest mid T60 reachable for each listen room and in the reference room.
4. `line_t60`, `g_decay`, makeup, `planned_fdn_ms` and `harmonic_pack` keep reading the armed dial, as SMALLDECAY Round 2 locked. If a long dial makes the render too short for the tail, report it and do not change `planned_fdn_ms`.
5. The read-only Mix row (`POST /api/phys_preview`) shows this room's resulting physical mid T60, the octave row, and `k`. The knob keeps the request. With the key off, nothing changes.
6. Surfaces on: the same one cascade as SMALLDECAY. The Surfaces absorption is scaled by `k` the same way. No second cascade.
7. If Part 4 cannot be done inside the existing pack path (no new opcode), STOP and report.

## Listens (to `roadmap\ambience\listen\`, clean guitar)
Rooms: boot 6x3x8, 4.5x6x2.8, 3x4x2.5, 2x2.5x2.2 at the PLACE positions.
- Per room: `A_today` (all keys off), `B_phys` (`phys_ceiling` on with Part 4, `sub_hp` on, dial 1.8), `C_phys_dial4` (same at dial 4.0).
- Extra: boot `D_phys_dial8` (dial 8.0), and boot `E_today_subhp` (keys off apart from `sub_hp` on), so Idle can hear the rumble filter alone.
- Name the files clearly. Report the numbers from Part 1.3 per file, plus `k`, and Play-vs-Render on one small room with everything on (null and T60 match).

## Gates
pytest (full), node, selfcheck, the harness, quick pins. Re-hash the five goldens, GOLDEN_META and both live MD5s with all keys off. Record the CPU numbers above. Write the landing into the Current pin and BUILD_RUN_LOG. Defaults stay off.


---

## IDLE OVERRIDE (2026-10-18 18:17) - `sub_hp` defaults ON. This block wins where it conflicts.
Idle: "just turn it on for now. no point in having that rumble."
- `sub_hp` (Part 2, 15 Hz 2nd-order HP on the FDN input) **defaults ON**. This overrides "every new key defaults OFF" and "do not re-pin goldens" for `sub_hp` only. `phys_ceiling` and Part 4 stay default OFF.
- Order, so the change is provable:
  1. Build `sub_hp` with it forced off first. Prove bit-exact: five TLAW goldens max-abs 0, GOLDEN_META and both live MD5s unchanged. Any move here is a STOP.
  2. Flip the default to on. Re-render and re-pin the five goldens, rewrite GOLDEN_META, and record the new empty-body and stored-centre live MD5s. Report old -> new for every one, plus the max-abs difference and the null in dB per golden against the old file, and the level change under 40 Hz and from 40 Hz up (the second should be tiny).
  3. Any test that pins the old sums must be re-pinned, not loosened. List each one. Anything that moves above 40 Hz by more than 0.1 dB is a STOP.
- With `sub_hp` on and `phys_ceiling` off, the default sound must differ only below about 40 Hz.
- Listen `A_today` becomes the new default (with `sub_hp` on). Add `A_old` for boot only (all keys off, the old default) so Idle can compare. `E_today_subhp` is dropped.
- Update the Current pin with the new golden hashes, GOLDEN_META and MD5s. Keep the old values in the pin under "pre-AMBIENCE".


---

## ROUND 1 REVIEW ACCEPTED (2026-10-18) - binding for Step 1, except the PENDING item
Build's Step 0 findings are accepted as written in that review. In short:
- `sub_hp`: one causal 2nd-order Butterworth at 15 Hz, designed at the posted sample rate, on `xA` and `xB` in `bus_sample` before the `inj`/`injB` multiply (six biquads). Render: the same designer on the excitation in `render_fdn_ir` (impulse and movement `drive` paths) and `render_binaural_fdn_ir`. Never forward-backward. Key off: the call is skipped and no field is added. Not in the feedback. Do NOT stop Part 2 on the "DC generated in loop" sentence (the review showed it is not).
- The 0.1 dB stop above 40 Hz is measured on **power**, not the time-domain null. The phase null is reported, not a stop. Expected about -0.085 dB at 40 Hz and -0.014 dB at 63 Hz.
- Re-pin list after the flip (re-pin, never loosen): the five goldens and GOLDEN_META (t03/t04/t05 tol_db unchanged), test_quick_pins (sha1s, GOLDEN_META_SHA1, EMPTY_MD5, CENTRE_MD5), test_smix_desk GOLDEN_SHA1, test_s_audit_api both MD5s, test_b6_heights _DEFAULT_LIVE_MD5, test_b2_render_length d18.f32/d4.f32 prefixes (re-save). WORKLET_VER 57->58, app.js?v=60->61, also at test_live_stereo.py:614, test_mic_colour_relative.py:989, test_b2_render_length.py:56. T60_TOL 0.08 and small_lock08 must not move; if they do, STOP.
- Part 1: copy the method in listen_report.json (test_guitar_dualmono.wav in roadmap/robotic_1240/, the per-row PLACE positions and room_WHL). Null make_listens.py against the existing _off wavs first.
- Part 3: re-measure before editing. No "bass cannot exceed the dial" clamp. If it is the kept axial peak / design_line cancel, STOP with options.
- Part 4: k scales card_alpha before chamber_to_specular, clip(k*alpha, 0.01, 0.99), one k solved on boot (6,3,8). Leave the make_spec dial/T_mid anchor out of the ceiling path. Report identity_n. planned_fdn_ms stays; report where the tail outlasts the file. /api/phys_preview returns this room's physical mid, the octave row and k.

## IDLE DECISION (2026-10-18 18:44) - bass in Part 4: realistic wall bass absorption, physics path only
Replaces the PENDING block. Part 4 may be built.
- In the `phys_ceiling` path only (not Surfaces, not the default cards, not `make_spec`), add a low-frequency **membrane/panel absorption** term to every face before `k` is applied. It stands for plasterboard on studs, windows, doors and flexing floors. Starting values (textbook gypsum-board-on-studs order of magnitude; mark them as such in the code comment): add alpha 0.20 at 63 Hz, 0.15 at 125 Hz, 0.08 at 250 Hz, 0 from 500 Hz up, log-interpolated like `card_alpha`.
- Target: in the boot room at dial 1.8, after solving k with this term, 63 / 125 / 250 Hz come out at 1.2-1.4x the 500 Hz-1 kHz mid. If the starting values miss that range, scale the whole bass term by one factor until 125 Hz sits at about 1.3x, and report the factor. If no single factor gets 63-250 Hz into 1.1-1.5x, STOP and report.
- Should k scale the bass term too? No. k scales the card alpha only. The bass term stays fixed, because panel absorption is the structure, not the surface finish. At high dials (4, 8) the bass ratio will grow. Report the 63/125/250 Hz times at dials 1.8, 4 and 8 for all four rooms.
- Re-solve k with this term in. Report k per dial.
- Everything else in ROUND 1 REVIEW ACCEPTED stands.


---

## ROUND 2 REVIEW ACCEPTED + IDLE DECISION (2026-10-18 19:12) — BINDING, overrides earlier blocks where they differ

The Round 2 review (read-only, against the real code) is accepted in full. These points are binding:

1. **sub_hp sites, live (`live_stereo.c`).** On the one-source path (`st->two` off), the tank input is `x = 0.5*(xL+xR)`, and `xA`/`xB` are 0 (`run_partition`, around lines 3435–3442). That path is the TLAW goldens path. The one-source sample drives the A-bus biquad state. Six biquads still fit: 3 buses × 2 sources.
2. **Filter the tank copy only.** On the one-source path, `xin` feeds both the early lane and the FDN add (around 2578–2592). Filter a copy on the FDN add only. The early write and the direct write (2487–2498) stay unfiltered. On the two-source path, filter only the tank copies `0.5*xA*injUse` / `xB` (2650–2654, 2698–2702). Early uses `imgA`/`imgB`, which stay unfiltered.
3. **surfOn and radA paths.** When either is on, the biquad sits on the FDN source actually injected (`srcSmp` / `diffIn` / `diffArr`, filled around 3444–3488). The `LS_DC` (1e-18) add stays after the high-pass. `tint` stays where it is.
4. **Render.** Apply one high-pass to the excitation that enters `process_block_poly` in `render_fdn_ir`. Never filter both `inj` and `drive`, or the movement path gets filtered twice. Each impulse column starts from a cold biquad with the same coefficients. Apply the same change to `render_binaural_fdn_ir` so it does not drift.
5. **Bass formula (exact).** `alpha(f) = clip(k * card_alpha(f), 0.01, 0.99) + s * bass(f)`, then the existing `chamber_to_specular` inside `face_bounce_db` / `room_target`.
   - Build it on a ceiling-path card copy (`absorb_fn`) only. Do not edit `default_surfaces`, and do not put `bass` in `make_spec`.
   - `bass(f)` is log-interpolated over knots 63/125/250/500 Hz = 0.20/0.15/0.08/0, clamped below 63 Hz.
6. **Bass scale s.** Solve `s` so that boot (6,3,8) at dial 1.8 gives T(125)/mid = 1.30, where mid is the mean of 500 Hz and 1 kHz. The review's number is about **0.106**, which gives ratios 1.19/1.30/1.28.
   - The comment must name 0.20/0.15/0.08 as textbook plasterboard/window/floor values, used here times the reported s.
   - STOP only if no single s puts 63/125/250 Hz all inside 1.1–1.5×. The review found 0.06–0.13 does.
   - k stays at about 0.776/0.333/0.152 for dials 1.8/4/8. Re-solve it with s in place and report it.
7. **IDLE DECISION: the bass term stays fixed (not scaled by k or the dial).** The 1.2–1.4× box is the dial-1.8 target only.
   - At dial 4 and 8, the bass times grow but their ratio to the mid falls. The review predicted 0.85/0.98/1.09 at dial 4 and 0.51/0.61/0.83 at dial 8. That is ACCEPTED, not a STOP.
   - Report the actual times and ratios for every room at dials 1.8/4/8.
8. **ALPHA_MIN at dial 8.** At dial 8, `k*card` drops below 0.01 at 63/125/250 Hz and is clipped to 0.01. Report it. It is not a STOP.
9. **Part 3 axial-peak item.** The axial-peak / `design_line` sentence in Part 3 is a REPORT, not a session end. Build the bass term.
   - After the term is in, STOP with options only if a band still misses the new T_eff because of the kept axial peak or an identity fallback.
   - There is no "bass cannot exceed the dial" clamp. Boot at 63 Hz, dial 1.8, comes out at about 2.14 s, and that is intended.
10. **Gates already matching the code, kept as written:**
    - The power-based 0.1 dB stop above 40 Hz. The 15 Hz high-pass is −0.085 dB at 40 Hz and −0.014 dB at 63 Hz.
    - The phase null is a report only.
    - Harness `golden_cmp tol_db=-100` stays, and the files are re-pinned.
    - Do not stop on loop DC. The +0.52 dB at 0 Hz is a `design_bus` identity fallback.
    - k is solved on boot `room_target(6,3,8)`.
    - Pass a false `make_spec` anchor on the ceiling path.
    - Report `identity_n` from the existing `_identity_n` count.
    - `planned_fdn_ms` is unchanged (2790/6090/12090 ms). Report bass T against the file length, and do not extend the file.
11. **`/api/phys_preview`.** It must return this room's physical mid, the octave row and k, from the same helper as the pack. With the key off it still returns `on: false`.
12. **Part 1 listens.**
    - Guitar: `roadmap\robotic_1240\test_guitar_dualmono.wav`.
    - Copy each row's own `placed` and `room_WHL` from `listen_report.json`. Boot uses the unscaled stand (sx 2.6, space 0.25). The small rooms use the PLACE poses.
    - `room_WHL` order is engine (W,H,L): 4.5x6x2.8 → [4.5,2.8,6.0], 3x4x2.5 → [3.0,2.5,4.0], 2x2.5x2.2 → [2.0,2.2,2.5].
    - Null the new script against the existing `_off` wavs before any DSP change.
13. **Re-pin list, completed:**
    - Five goldens + GOLDEN_META: `test_quick_pins.py` 31–40 and `test_smix_desk.py` GOLDEN_SHA1.
    - `test_s_audit_api.py` 25–26: both MD5s.
    - `test_b6_heights.py` 45: empty MD5.
    - `test_b2_render_length.py` 168–183: the d18/d4 prefixes. That body sends no `sub_hp`, so after the flip an ABSENT key must turn the filter ON inside the param build.
    - `test_quick_pins.py` 73–75: WORKLET_VER, `live_fdn.js?v=`, `app.js?v=`.
    - `test_live_stereo.py` 616 and `test_mic_colour_relative.py` 990: `live_fdn.js?v=57` → 58, as well as the WORKLET_VER lines 614 and 989.
    - `index.html`: `live_fdn.js?v=58` and `app.js?v=61`. `pack_room.js` bumps only if it changes.
    - Harness t01: a new coefficient field must land in both the Python packer and `packRoom`.
    - `scrub` zeroes the new biquad state next to `harmZ`/`slZ`.
    - T60_TOL 0.08 and `small_lock08` stay. Any move there is a STOP.
14. **Order.**
    - First prove bit-exact with an explicit `sub_hp: false`: the call is skipped and no live-dict field is added.
    - Then flip the default so a missing key means ON, re-pin, and report old → new for every pin.
    - `phys_ceiling` stays default OFF.

Step 1 (build) may now run in a fresh session.
