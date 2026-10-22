# Fault investigation — 9 Oct 2026

Read-only. Nothing under `software\` was edited. No golden was touched. Idle’s server on port 7860 was not restarted. The page check used port 64056. After the runs, all 40799 files under `software\` matched the pre-run timestamp and size snapshot (bytecode writes were off).

No fix is applied. Anything that changes loudness or the default sound is for Idle.

Pin used: `HANDOVER.md` Current pin, `WORKLET_VER` 52. Claims are tagged VERIFIED / LIKELY / PROPOSAL.

Measurements: `measure_f1_f2.py`, `measure_f3_ui.py`, `measure_f1_early.py`. Numbers: `f1_coeffs.json`, `f1_renders.json`, `f1_early.json`, `f2_positions.json`, `ui_capture.json`. Renders are 0.2 s of noise, peak 0.5, 48 kHz, colour BYPASS, decay lock 1.8 s unless the Hall button row says otherwise. The limiter knee is identity through ±0.95 (`render_pipeline.py` `soft_limit`).

---

## F3 — Mix “Room mic” on Centre goes silent. Mic page does not. VERIFIED

Cause: the Mix place handler sets `place_c = "room"` and copies the stand into `room_c_*`, and it leaves `third_mic` at `"off"`. Boot ORTF is `third_mic: "off"` (D20, centre off). Both the page and the server then force centre gain to 0.

- `software/static/js/app.js` 1030–1048. On Room it saves `cThirdBeforeRoom` (1038) and snaps the stand (1045). It does not assign `state.third_mic = "room"`. Return to stand writes the saved value back (1039–1041).
- `app.js` 586 and 478: `third_mic === "off"` sets `mic_gain_c` to 0. `app_server.py` 500–501 does the same.
- Mic page `app.js` 1102–1118: `[data-third="room"]` sets `third_mic = "room"` and `place_c = "room"` and snaps. Gain stays at the fader (0 dB → 1).

Page, fresh boot, free port (VERIFIED, `ui_capture.json`):

| Click | place_c | third_mic | mic_gain_c | posted mic C | matrix |
| --- | --- | --- | --- | --- | --- |
| Boot | array | off | 0 | absent | C −∞ / −∞ |
| Mix Room on C | room | off | 0 | 3, 1.5, 1.5 | C −∞ / −∞ |
| Mic Room | room | room | 1 | 3, 1.5, 1.5 | C −6.0 / −6.0 |
| Mix Room on L | place_l room, C still off | off | 0 | L at 2.915, 1.5, 1.5, gain 1 | L 0.0 / −∞ |

Mute and route stayed pan / not muted on every row. L is not silenced.

Render of those bodies, Direct and Early down (VERIFIED, `f1_renders.json`):

| Body | peak | RMS | tail RMS | limiter |
| --- | --- | --- | --- | --- |
| Boot ORTF | −13.72 dB | −35.83 dB | −36.26 dB | 0 |
| Mix Room C | −13.72 dB | −35.83 dB | −36.26 dB | 0 |
| Mic Room C | −15.57 dB | −38.23 dB | −38.65 dB | 0 |

Mix Room C matches boot sample for sample in this test: the new centre adds nothing. Mic Room C is audible and 2.4 dB quieter RMS. Makeup falls from +12.25 dB to +8.16 dB once C joins the loudest fold (`f1_coeffs.json`), which is most of that drop. Centre pan at 0 dB is −6 dB per side, which is what the matrix shows.

The Source page still draws C from `room_c_*`, so the strip looks detached while the gain is zero. That is the “decouples but inaudible” report.

PROPOSAL, not applied. In the Mix place handler, when `cap === "c"` and `name === "room"`, set `state.third_mic = "room"`. The saved `cThirdBeforeRoom` and the return-to-stand restore can stay. Sound: ORTF centre, silent today, becomes the Mic-page centre at the snapped stand. Boot stays centre-off until that click. L and R are unchanged. A few lines in `app.js`. It does change what that click does to the mix, so it is Idle’s call. If centre should stay off, the other shape is to keep the gain at 0 and stop drawing that strip as a live mic.

---

## F1 — Level versus distance, limiter when far, Hall loud

### What moves

Makeup is one gain for the whole mix. It sets the loudest Mixer fold of the 1/r² injects to 0.7, then applies `sqrt(1−(g√N)²)`, then clamps to [0.05, 256] (`fdn.py` `ir_rms_makeup_from_inject`, 516–572). Geometric level is `1/r²`, and a distance at or under 1e-9 returns 0 (`early_field.py` 1422–1430).

Play (`live_fdn_params`, `render_pipeline.py` 2183–2208) and Render (`combined_ir`, 1310–1319) call that same function. With the decay lock on, both rewrite `g` to `structure_gain_for_rt60 / N` before the call (1766–1769 and 2183–2187). The FDN bus then takes the same loop trim on both paths: −4.51 dB with the lock on, −1.70 dB with it off (`fdn.py` 267–284, applied at `render_pipeline.py` 2367 for Play). Early is multiplied by the same makeup (1314–1319). Direct is a spike of 1, times 0.55, and it is not 1/r² (`render_listen_direct_ir`, 1128–1186). `direct_makeup` is returned in the live params (2389) and is not a symbol in `live_stereo.c`. The worklet multiplies makeup onto FDN and early only (`live_stereo.c` 2601–2602).

Solo centre, cardioid aimed at the source, Direct and Early down. Makeup is the Play figure. The render columns are the file (VERIFIED):

| Distance | Makeup | Render peak | RMS | Tail RMS | Limiter |
| --- | --- | --- | --- | --- | --- |
| 0.5 m | −12.84 dB | −12.29 dB | −35.17 dB | −35.70 dB | 0 |
| 1 m | −0.77 dB | (coeff only) | | | |
| 2 m | +11.33 dB | −13.69 dB | −35.52 dB | −36.01 dB | 0 |
| 4 m | +23.50 dB | (coeff only) | | | |
| 6 m | +30.68 dB | (coeff only) | | | |
| 8 m | +35.81 dB | −12.67 dB | −35.48 dB | −35.82 dB | 0 |

Makeup rises about 12 dB each time the distance doubles (the inverse of 1/r²). From 0.5 m to 8 m that is +48.6 dB of makeup. The rendered FDN noise stays flat: peak spread 1.4 dB, RMS spread 0.4 dB.

Direct only, same solo centre (VERIFIED): peak −17.23 dB and RMS −40.88 dB at both 0.5 m and 8 m. That is `0.5 × 0.55 × 0.5` (noise peak × fold × centre pan). Distance changes the delay and not the spike.

Early only. The first solo-centre early rows were silent, because early is the L/R capsules and that body had those gains at 0 (`render_pipeline.py` 1315–1316). A second pass put L and R on the stand at gain 1, centre off, Direct and FDN down (`f1_early.json`, VERIFIED):

| Distance | Makeup | Render peak | RMS | Tail RMS | Limiter |
| --- | --- | --- | --- | --- | --- |
| 0.5 m | −15.68 dB | −15.41 dB | −39.41 dB | −41.46 dB | 0 |
| 2 m | +7.61 dB | (coeff only) | | | |
| 8 m | +31.93 dB | −12.88 dB | −36.76 dB | −37.96 dB | 0 |

Early makeup follows the same rise. The rendered early file is 2.5 dB louder at 8 m than at 0.5 m (peak), and the tail is 3.5 dB louder. That is the same direction Idle heard, at a few decibels, on this noise. It is not the full 48 dB of makeup.

All-up solo centre (Direct, Early, and FDN faders up, L/R gains still 0 so Early adds nothing): peak −9.83 dB at 0.5 m and −10.38 dB at 8 m. The extra over FDN-only is the direct spike.

### Presets and the two screenshots

Stand or button, Play makeup (VERIFIED coeffs). Renders where noted.

| Case | Distance | Makeup | Render peak | RMS | Limiter |
| --- | --- | --- | --- | --- | --- |
| Studio stand, C off | 3.05 m | +11.10 dB | not rendered | | |
| Boot ORTF, C off | 3.29 m | +12.25 dB | −13.72 dB | −35.83 dB | 0 |
| Club stand, C off | 11.1 m | +37.24 dB | not rendered | | |
| Hall button | 48.0 m | +48.16 dB | −9.87 dB | −32.72 dB | 0 |
| C far, L/R on boot stand | 5.43 m | +12.50 dB | −13.93 dB | −35.99 dB | 0 |
| C on the source coordinates | 0 | +11.06 dB | −11.87 dB | −34.87 dB | 0 |
| C 0.30 m above the source, L/R on the stand | 0.30 m | −20.00 dB | coeff only | | |

Hall’s makeup is +36 dB above boot. The noise file is 3.9 dB hotter at the peak than boot, and it does not limit. The Hall button also puts Direct at 0 dB and turns the decay lock off; boot has Direct down and the lock on. Hall’s own FDN first-tap estimate is −22.54 dB against boot −14.58 dB. A separate Hall render with Direct down was not made, so the +3.9 dB is the whole button, not the tank alone.

Screenshot 554 (C in the far corner, Play, guitar, limiter 14.1 dB / 582 samples) and 555 (C on the source, no badge) were not reproduced by these renders. Every render in this pass, including Hall, reported limiter reduction 0. A full-scale copy of the flat FDN rows would be 6 dB hotter than the measured peaks near −12 dB, still under the 0.95 knee. Colour was BYPASS, so a measured-mic resonance is not in these files. The 14.1 dB badge stays a Play observation on that guitar file. Cause of that specific badge: not found in this noise pass.

What the screenshots do line up with is global makeup. Makeup follows the loudest capsule and turns the others down with it. With L/R left on the boot stand:

- C far (5.4 m) does not beat L/R, so makeup stays +12.5 dB, the same region as boot.
- C placed on the exact source coordinates contributes 0, because `geometric_level` returns 0 at 1e-9 m. Makeup stays +11.1 dB. The render is 2.1 dB louder than the far case, not quieter.
- C 0.30 m from the source (the height gap in 555: mic 1.50 m, source 1.20 m, floor spots overlapping) sets makeup to −20.0 dB. That is 32 dB under the far case. The close capsule’s own first tap stays near −15 dB. The stand pair is the part that drops.

Idle’s “softer as it approaches” matches that global gain: once the moving capsule is the closest, makeup falls about 12 dB per halving of its distance, and every other capsule falls with it. The moving capsule’s own FDN level stays about flat, which is the AGC holding the loudest arrival. A real room would have let that capsule rise by the same 12 dB per halving. The control is doing the job its comment states, and that job removes the rise.

### PROPOSAL, not applied

Do not retune 1/r² or the 0.55 fold.

- Freeze makeup at the stand distance (the level before the mic is moved). The default picture stays. A closer mic gets louder and a farther mic gets quieter, about 12 dB per doubling, which is the geometric law already in the injects. Hall’s long stand stays as loud as it is now, because the reference is that stand. One close capsule stops ducking the others. Size: medium, both callers of `ir_rms_makeup_from_inject` (Play and Render). This changes the sound as soon as a mic leaves the reference.
- Lower `target_peak` (0.7) or add output headroom so a hot file clears the knee. Size: small. It does not make a close mic louder. These noise files never reached the knee, so it does not explain the rows above.
- Stop tracking makeup with distance. Close becomes loud, far becomes quiet, and Hall loses the +36 dB of extra makeup. Size: large, and it changes the default sound.

Idle’s sentence (“I like the automatic gain control but it seems to work too well”) fits the first option. The choice is Idle’s.

---

## F2 — Mic page still draws Centre on the stand. Sound uses the room spot. VERIFIED

T9 left Top, Combined, and the Source plane unbuilt. This pass confirms that, on the current page.

Sound (VERIFIED, `f2_positions.json` and the page post): `heardMix` posts `mic_x/y/z_c` and the yaw while the strip is Room (`app.js` 594–604). A heard body with the spot at (5.5, 2.5, 0.4) produces audio centre (5.5, 2.5, 0.4) through `apply_desk_geometry` / `centre_position`.

Display, same spot typed into the room fields after Mic Room (VERIFIED, `ui_capture.json`):

- Space `/api/images` returned C at (3.0, 1.5, 1.5). The request carried `room_c_x` and did not carry `mic_x_c`. `build_images_payload` (`image_geometry.py` 221–225) uses the stand prepare only. `api_images` (`app_server.py` 849–870) does not pass a desk.
- `/api/polar` request had `room_c_x` 5.5, `place_c` room, `third_mic` room, and no `mic_x_c`. `polar_field.py` 507–511 will move the stand only when desk positions are present, so this request stays on the stand. The Source-plane caption is fixed text (`polar_field.js` 155): “Plane through L, R and the source · centre added with its delay”.
- Mic-page readout stayed “space 0.17 m · C 0 cm · 1.50 m high” with the hint “The stand, from above.” Top draw and the hit targets use `geo.mic_centre` / `geo.mic_left` / `geo.mic_right` (`mic_desk.js` `drawTop` caption at 470, `hitTop` 964–970, `hitSide` 986). Dragging a capsule writes `centre_dz` or `space` (`applyTopDrag` 1056–1071), including when the strip is Room. Yaw drag already writes `room_<slot>_yaw` when the strip is Room (1020–1024). Each-mic aim uses that room yaw (`aimYaw` 882–887). That aim path was read in code and not re-shot on the canvas.
- Room 3D places `micCentre` from `RoomMath.compute` (`room_3d.js` 568, `room_math.js` 127). `compute` never reads `room_c_*`. The 3D claim in the old screenshot 547 description was not re-checked in the browser.

PROPOSAL, not applied. Display only. When `stripIsRoom`, Top, Side, their hit tests, the combined polar, the source plane, the 3D capsules, and the Space mic ticks should read the room spot. A hit on a Room strip should write `room_<cap>_*`, not `centre_dz` or `space`. Leave `heardMix` as it is. Sound impact: none. Several view files. T9 scoped this as unbuilt, not a regression.

---

## F4

Not retested. The fault note records Source-page detach, drag, and wall stop, and the Mic-page window and Return to stand, as already working.

---

## Stopped here

One pass. No code under `software\` was changed. The guitar’s 14.1 dB limiter badge was not reproduced. Studio and Club were makeup figures only. The 0.30 m centre was a makeup figure only.
