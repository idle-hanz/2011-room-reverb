# Two sources from a stereo file

Built 2026-09-22. One source stays the default. Do not rebuild this on a bare continue.

Open with: read `HANDOVER.md`, then build this file. Do not reopen the mix desk, the 3D Left/Right lock, or Air Abs `1/r²`.

**Tag:** ASSUMED upgrade. One source and the downmix stay the default.

## Decision

A stereo WAV is one sound today. Play live sums `0.5·(L+R)` in `fdn_worklet.js` `process`. Render uses `load_wav_mono`. One source dot. The 32 FDN delays are that source’s image times.

A second source has different image times. Do not inject the right channel into the left source’s delay lines. That would make the right voice speak from the left voice’s reflections.

**Two sources** is off until the user turns it on, and only when the file has two channels.

- File left → source A (the existing dot: `sx, sy, sz`).
- File right → source B (new: `sx_b, sy_b, sz_b`).
- Do not swap channels to chase the speakers. Capsule phase on the Mix desk is the flip.

**Mirror** locks B through the width centerline only:

`B = (W − sx, sy, sz)`

Same height, same depth, opposite side. In a rectangle that placement mirrors the image cloud. Do not add a second control that flips the image table. Do not use the point reflection `(W−sx, H−sy, L−sz)`. Do not change `threeZ = L − z` or the floor X axis.

Dragging A while Mirror is on moves B. Dragging B clears the lock and leaves B where it was dropped.

**Balance** sits with the file, before Direct, Early, Host dry, and the FDN. It is not a desk fader.

`bal` is −1…+1. Centre is 0.

- `bal ≤ 0`: gain A = 1, gain B = `1 + bal`
- `bal ≥ 0`: gain B = 1, gain A = `1 − bal`

Centre is both gains at 1. Toward A, B fades out and A stays full. Toward B, the opposite. Hard A is source A alone. Hard B is source B alone.

Then:

- Left × gain A → source A’s direct, early, and FDN
- Right × gain B → source B’s direct, early, and FDN
- Each FDN input is half that scaled channel: `0.5 · left·gainA` into A’s tank, `0.5 · right·gainB` into B’s. The half keeps a hard balance at the old single-tank level
- Host dry, when two sources are on, is still the balanced downmix `0.5·(left·gainA + right·gainB)`, one mono send to both speakers

Two sources off: Balance is hidden. The excitation stays today’s downmix. Mono files cannot turn the option on.

## Doubled vs shared

Doubled:

- Direct A from the scaled left channel, Direct B from the scaled right. Each delay is that source’s own `n=(0,0,0)` time. Both keep the listen law (delayed file × 0.55 fold, then the desk Direct fader). Do not switch Direct to `1/r²` loudness.
- Two-source direct spikes are that source’s pattern gain, divided by the hottest of the three capsules, so the on-axis mic stays at 1. One source stays spike amplitude 1 on L, C, and R. Fig-8 keeps its sign.
- Early the same way, only when Early is up. B uses B’s image delays and B’s inject levels.
- FDN the same way. A’s tank uses A’s image times. B’s tank uses B’s. Do not fold B back into A’s delays.
- Floor, side elevation, and 3D draw both dots. Lattice and Paths draw both image sets. B is a second colour (not amber, not the mic purple/teal/green).

Play sums B’s line output onto A’s line before the colour convolver, so the convolver count stays the same and B’s tail uses A’s per-line filter. Render colours B at B’s own angles. The speaker image is the inject and the direct pattern, which both paths share.

## Where it lives in the code

Play live, `software/static/js/fdn_worklet.js`:

- With the option off, one excitation `x` feeds direct and the one tank.
- With it on, left×gainA feeds A and right×gainB feeds B. Direct writes are scaled by `dirGain` / `dirGainB` (the normalized pattern). B’s tank has its own delay, inject, and Dffs. The two line outputs are added before the mic filter.
- Sum A and B inside the capsule before the existing mic gain / pan / phase fold. The desk does not grow a second Direct fader.
- The worklet input is channel count 2, explicit, discrete, so a stereo file is not folded first.
- `WORKLET_VER` is 28. With Dffs, each tank feeds back the previous sample of `y`. The Play block is `live_stereo`.

`software/static/js/live_fdn.js` `pushParams` forwards `two_sources`, `gain_a`, `gain_b`, and per-bus `b: { delay_ms, inject, dffs, direct_gain }`.

`software/render_pipeline.py` `live_fdn_params`:

- If `two_sources`, build a second `compute_taps` at `(sx_b, sy_b, sz_b)` and attach those delays, injects, Dffs, and direct gains. Direct index is still `n=(0,0,0)`.
- Echo `gain_a` / `gain_b` from `source_balance`.

Render, still path only:

- Keep stereo samples long enough to split. `load_wav_mono` stays the path when the option is off.
- `out = conv(L·gainA, directA+earlyA) + conv(R·gainB, directB+earlyB) + conv(0.5·L·gainA, FDN of A) + conv(0.5·R·gainB, FDN of B)`.
- Moving path (`path_on`) stays the mono downmix. Do not block on it.

`app_server.py` `params_from_body`: `two_sources`, `source_balance`, `mirror_b`, `sx_b`, `sy_b`, `sz_b`. Clamp B inside the room. If `mirror_b`, force `sx_b = W − sx`, `sy_b = sy`, `sz_b = sz` on the server too, so a stale client cannot disagree.

Pictures:

- `room_math.js` — `source_b` on the geometry object when the option is on.
- `room_editor.js` — second handle on the floor and the side view. Hit-test B before A when they overlap. Dragging B sets `mirror_b` false.
- `room_3d.js` — second mesh. Orbit only; placement stays on the floor, same as A. `threeZ = L − z`.
- `/api/images` and `image_views.js` — second tap list, tinted.

UI, next to the file name in `index.html` / `app.js`:

- **One source / Two sources.** Disabled when the WAV is mono (channel count at byte 22 of a canonical WAV is enough).
- **Mirror**, shown only while two sources are on.
- **Balance**, −1…+1, shown only then. Detent at 0.

## Do not

- Do not change Air Abs `1/r²`, the 0.55 Direct fold, FDN makeup, Decay lock, or the desk laws.
- Do not flip floor X or the 3D camera.
- Do not omit FDN inject on line `n=(0,0,0)`.
- Do not IR-RMS the FDN.

## Check

- Mono file: unchanged.
- Stereo, option off: current downmix.
- Option on, Balance at 0, Mirror off: left channel is A’s direct and A’s tail, right channel is B’s direct and B’s tail.
- Mirror on, mic on the centerline: A and B arrive as a pair from opposite sides of the stand. The side is the mic that is aimed at that source. Drag A and B follows. Drag B and the lock drops.
- Balance hard A: right channel is absent from Direct, Early, and the FDN. The image sits on A’s side. Hard B sits on B’s side.
- Lattice shows two clouds. One is the width-mirror of the other when Mirror is on.
- Selfcheck: balance centre is `(1, 1)`, hard A is `(1, 0)`, hard B is `(0, 1)`, mirror of `sx` is `W − sx`. Existing mix tests stay green.
