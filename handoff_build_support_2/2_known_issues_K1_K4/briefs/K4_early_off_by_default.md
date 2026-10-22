# K4: early reflections are off by default. CONFIRMED

## LOCKED 28 Sep 2026: FDN-first defaults + stale early lane FIXED (Idle)

**Defaults** (patch `05_K2_K3_K4_defaults.diff`):
- FDN fader 0.5 (0 dB), and the direct and early faders 0 (`app.js`; `index.html` `fader_direct` value 0).
- `early_wet` = **1.0** in the client state. It is now the early-bus *enable*, and the heard early send is `early_wet × stripLinear(early fader)` (`heardMix`). So raising the early fader works at once, and at fader 0 the bus stays silent.
- The Reaktor-parity preset now sets `early_wet = 1.0` too, with its early fader still at 0.
- **Server defaults** (`DEFAULTS["early_wet"]` 0, `direct_wet` 1) are **unchanged on purpose**. The server field is the *post-fader* send, the page always sends it, and the server defaults only matter to API callers that omit it. ASSUMED acceptable. It is listed as a small remaining K5 mismatch.
- Old saves: a saved `early_wet: 0` would now mute the early fader. `heardMix` treats a missing value as 1. Saves with an explicit 0 are rare (ASSUMED; the old value was always overwritten).

**Stale early buffer fix** (patch `06_K4_stale_early_lane.c.diff`, `engine/live_stereo.c` `bus_sample`):
- The early lane (and EARLYB with two sources) is now **written every sample**, even while the early send is off. It is only read and accumulated while on (`runEarly`).
- Before, the write was skipped, so the ring kept the input from just before the fader was lowered. Raising the fader replayed it.
- The wasm was rebuilt. The native build (gcc) passes Build's `test_live_stereo.py`.
- **Test** (`test_k4_raise_early_fader_no_stale_replay`, uses the new `wasm_run.js switch` mode):
  - Noise runs 0–2 s. Early goes off at 1.0 s and back on at 2.5 s.
  - From 2.5 s the output must null against an early-always-on run.
  - VERIFIED before the fix: null −1.0 dB, max diff 0.059 (a −24.6 dBFS burst over a −50.5 dB tail).
  - After the fix: bit-identical (max diff 0).
- **CPU:** `tint()` plus the lane write now run while early is off. Measured with run_all t09/t15 (package 4 README).
- **Not fixed** (brief only): the FDN lane has the same pattern when `fdn_wet` falls to ≤ 1e-4 (the FDN fader at −∞) and is raised again. The loop state freezes and resumes.
  - It matters less, because FDN is on by default and resuming a frozen tail is less jarring than replaying input.
  - Fix options: (a) keep running the loop at fader −∞ (costs CPU); (b) clear the FDN lanes on the off→on transition (a `scrub`-style clear of the LANE_FDN ring, O(ring)).
  - Build's call.

---

*Original brief (history, before the decision):*

**Status:** CONFIRMED (VERIFIED by `scripts/k4_early_off.py`).

## Evidence

- **Server:**
  - `app_server.py:74`: `DEFAULTS["early_wet"] = 0.0`.
- **Client:**
  - `static/js/app.js:85`: `early_wet: 0`.
  - `app.js:90`: `fader_early: 0`.
  - The parity preset sets them to 0 again (`app.js:167`, `app.js:179`).
  - `stripLinear(state, "early")` (`app.js:296`) turns fader 0 into gain 0.
- **Sound:** a fresh page, and a Render with no body, have **no early reflections at all**. When turned on (early_wet 1), the early bus carries **−17.8 dB of the energy in the first 80 ms**, and the first 80 ms change by −16.9 dB relative to the default.
- **Lock holds:** early_wet does not change the FDN (max difference 5e-18). The images still excite the FDN when the early bus is muted, as the lock requires.

## Side finding (code read; the audible effect is ASSUMED)

- `engine/live_stereo.c:1003` and `:1040-1046` (`bus_sample`):
  - When `early_wet` ≤ 1e-4, the early lane is neither read nor written (`if (runEarly) {...}`).
  - When the user raises the early fader during playback, the lane still holds **stale samples** from the last time it was on. These play out once, over up to one `max_delay`. `fdn_wet` gating behaves the same way.
- Proposed fix:
  - Keep writing the early lane whenever `runFdn || runEarly` (it is only a float store).
  - Or zero the lane on a 0 → >0 transition.

## Proposed change

- The default level is a **DECISION FOR IDLE**. Two parts of the Structure design (early images, and the images exciting the FDN) are there to be heard.
- Suggested starting point: `early_wet` 1.0, with `fader_early` at the same travel as direct/FDN (0.5). Change it in `app_server.py:74`, `app.js:85`, `app.js:90` and `app.js:167/179`, and record it in `parameters.csv`.
- If the early level should stay at 0 for gain-staging reasons, say so in the UI (e.g. the fader starts at −∞ but is labelled).

## Acceptance

- Package 3's `/api/defaults` test covers the parity between server and client.
- Add: the default scene has an early bus energy > −30 dB relative to the total in the first 80 ms, if Idle chooses "on".

## Listening check

- Early fader at 0 vs 0.5, on a clap in the default room.
