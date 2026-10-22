# K1: the stereo presets aim the capsules inward (crossed). CONFIRMED

## LOCKED 28 Sep 2026: FIX with ONE convention flip (Idle). Implemented in patch `04_K1_yaw_convention.diff`

**What changed** (no per-preset sign edits; stored yaw numbers in presets and saves are untouched):
- `engine/early_field.py`: new module constant `YAW_X_SIGN = 1.0`. The old convention was −1.
  - `look_vector(yaw) = (YAW_X_SIGN·sin yaw, 0, cos yaw)`.
  - `direction_angles` and `arrival_cos_xz` rotate by `s = YAW_X_SIGN·sin yaw` (was `sin(−yaw)`).
  - Header comment rewritten. The old "facing each other / MS inward" note is kept, marked superseded.
- `polar_field.py`: uses `early_field.look_vector` (no second formula).
- `mic_display.py`: `look_xz` reads `YAW_X_SIGN`.
- `static/js/room_math.js`: `YAW_X_SIGN = 1`, `lookFromYaw = {x: YAW_X_SIGN·sin, z: cos}`, exported.
- `static/js/mic_desk.js`: the polar-desk handle position and the drag inverse use `RoomMath.YAW_X_SIGN`. Dragging right still moves the handle right.
- `room_3d.js` follows automatically from the look vectors.
- **Build's own checks that encoded the crossed image were updated:**
  - `engine/selfcheck.py` `test_two_source_balance_mirror_and_split` had "the source on the visual left is hotter in the right capsule". Direct, direct_gain and FDN-tail assertions were flipped.
  - `tests/test_mic_colour_relative.py::test_early_toys_gated_and_colour_per_tap`: the extreme-theta taps now arrive at 24–30 ms, so the pair window goes from 15 to 40 ms.
  - Result: selfcheck 44/44 and Build's two test files 27/27 pass on p5 (VERIFIED).

**Result** (VERIFIED, real Play path in node, MEASURED_SHELF colour; source at x = 1 m, stand at x = 3 m, about 32° left):

| Preset | direct L−R before → after | early L−R before → after | arrival L/R (samples) after |
|---|---|---|---|
| xy_90 | −7.92 → **+8.10 dB** | −8.09 → **+8.29** | 538 / 539 |
| xy_120 | −8.66 → **+8.86** | −7.87 → **+8.20** | 538 / 539 |
| ortf | −8.03 → **+8.72** | −8.54 → **+8.48** | 533 / 545 |
| nos | −6.23 → **+8.22** | −6.30 → **+8.65** | 528 / 550 |
| din | −6.41 → **+8.19** | −7.53 → **+8.53** | 531 / 546 |
| ms | −4.26 → **+3.51** | −1.74 → **+1.44** | 537 / 539 |

- Render agrees with Play: ortf +8.72, xy_90 +8.10, ms +3.51 dB (VERIFIED, `render_ir`).
- With colour BYPASS, the early bus goes from −0.9…−4.4 dB (crossed) to +3.1…+4.4 dB.
- **Note (VERIFIED):** in one-source Play the direct bus carries no capsule polar gain. The C code stores the raw downmix (`live_stereo.c` `bus_sample`), so with colour BYPASS direct L−R is 0 dB. The polar cue on direct comes from the colour bank (MEASURED_SHELF). This is Build's design, not part of K1.
- `ms_classic` (fig8 ±90): under MEASURED_SHELF the preset's mic owns the pattern, so it behaves like `ms`. It was not re-checked with `ms_decode`, whose polarity is still ASSUMED correct.
- Tests: package 3 `test_decisions_2026_09_28.py::test_k1_*` (single convention, 6 Play presets, 3 slow Render presets).

---

*Original brief (history, before the decision):*

**Status:** CONFIRMED (VERIFIED by `scripts/k1_ortf_crossed.py` and `scripts/k1b_all_presets.py` on the 28 Sep 20:40 snapshot).

**Needs:** Idle's OK and a listen, because the fix changes the stereo image.

## What is wrong

- The engine convention is `look_vector(yaw) = (−sin yaw, 0, cos yaw)` (`engine/early_field.py:1045-1047`). The UI uses the same convention (`static/js/room_math.js:100`). So a **positive** yaw aims toward **−X**.
- The L capsule sits at the lower X (x = 2.915 for the default stand at x = 3).
- Every stereo preset ships with **L negative, R positive**:
  - `static/js/app.js:15` ab_card
  - `app.js:20` xy_90
  - `app.js:25` xy_120
  - `app.js:30` ortf
  - `app.js:35` nos
  - `app.js:40` din
  - `app.js:45` ms
  - `app.js:50` ms_classic
  - `app.js:73` default state
- The server does the same when it derives yaw from `toe_half_deg`:
  - `app_server.py:166-168`: `yaw_l = −toe`, `yaw_r = +toe`
  - `engine/early_field.py:514-523` (`angles_from_toe_half_deg`) returns (−half, +half)
- As a result, the L capsule aims (0.819, 0, 0.574): toward +X, across the R capsule.

## Evidence (VERIFIED)

Default ORTF, source 2 m left of the stand (x = 1 m):

| Quantity | Now (L −55 / R +55) | Fixed (L +55 / R −55) |
|---|---|---|
| Cardioid gain, L / R capsule | 0.539 / 0.963 | 0.955 / 0.520 |
| Direct arrival, L − R | −12 samples (L first, correct) | same |
| Direct level, MEASURED colour, L − R | **−5.4 dB** | +5.5 dB |
| Early reflections only, L − R | **−4.8 dB** | +3.6 dB |
| Direct level, BYPASS | 0 dB (direct spikes carry no polar gain, `render_pipeline.py:663-697`) | 0 dB |

- With the current signs, the time cue says "left" and the level cue says "right". This is the classic symptom of crossed capsules.
- All presets, near capsule minus far capsule, source at x = 1 m (`results/k1b_all_presets.json`):

  | Preset | Shipped | Signs negated |
  |---|---|---|
  | xy_90 | −4.1 dB | +4.1 dB |
  | xy_120 | −5.7 dB | +5.7 dB |
  | ortf | −5.0 dB | +5.3 dB |
  | nos | −3.9 dB | +4.3 dB |
  | din | −4.0 dB | +4.2 dB |
  | ms (L/R parsed as cardioid ±90) | −10.1 dB | +10.2 dB |

  - ab_omni and mono_c are unaffected.
  - ms_classic (fig-8) shows no magnitude difference. The problem there is the S polarity, which needs its own check (ASSUMED).

## Proposed change (pick one; both give the same audio for cardioid presets)

**Option A (recommended, ASSUMED): flip the convention once, in the engine and the UI together.**
- `engine/early_field.py:1047`: `return (math.sin(yaw_rad), 0.0, math.cos(yaw_rad))`
- `engine/early_field.py:1018` and `:1040` (`direction_angles` / `arrival_cos_xz`): use `cos(yaw), sin(yaw)` instead of `cos(-yaw), sin(-yaw)` so they stay consistent with the look vector.
- `static/js/room_math.js:100`: `return { x: Math.sin(yawRad), z: Math.cos(yawRad) };`
- `static/js/mic_desk.js:870`: the drag handle mapping `deg = Math.atan2(-dx, -dy)` must flip with it, to `Math.atan2(dx, -dy)`. Check this in the UI: dragging the L handle outward must give a positive L yaw.
- Update the docstring at `early_field.py:1046`.
- **Plus:** saved projects keep their numbers and are fixed automatically, because they were all authored under the crossed convention.
- **Minus:** it touches the geometry code, so MS decode polarity must be re-checked.

**Option B: flip the signs in the data only.**
- Negate `yaw_l_deg` / `yaw_r_deg` in every preset at `app.js:15-50`, in the state at `app.js:73`, and in the parity presets at `app.js:167/179` if they carry yaws.
- `app_server.py:167-168`: use `yaw_l = +toe`, `yaw_r = −toe`.
- `early_field.py:523`: `return (+half, -half)`.
- **Minus:** old saves stay crossed unless a save-version migration negates them.

## Acceptance

- A new test: source at x = 1 m, ORTF. The L output must be earlier **and** louder, by ≥ 3 dB for early-only and ≥ 5 dB for direct with MEASURED colour.
- Mirror check: source at x = 5 m gives the opposite.
- The same check for xy_90 / xy_120 / nos / din.
- For ms / ms_classic, render the decoded output and check that a left source is louder in L.

## Decision for Idle

1. Confirm the fix is wanted. It moves every off-centre source in the stereo image.
2. A or B.
3. Listen: a snare 2 m left of the stand, before and after.
