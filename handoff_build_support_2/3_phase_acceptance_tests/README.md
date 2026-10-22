# Package 3: phase acceptance tests (P0–P6, product locks, SOS colour)

pytest tests that encode the roadmap's success criteria. They run on the box, or on any machine with **node** and a Python that can import `software/app_server.py` (numpy, scipy, fastapi, pytest). The PC has no node, so run them on the box.

## Run

```bash
python -m pytest tests -q --sw /path/to/software            # fast set (~1 min)
python -m pytest tests -q --sw /path/to/software --slow     # plus the Render-heavy tests (~2 min)
python run_phase_tests.py --sw /path/to/software --slow --out results/x.json   # run_all.py-style table + JSON
```

- `mic_fitter/` must sit next to `software/`, as for `run_all.py`.
- Nothing in `--sw` is written. The helpers use a pytest temp dir.
- `harness/` is a vendored copy of `engine/tests/run_all.py` and `lib/`, reused for Play (node + wasm), Render and packing. Some tests call run_all tests directly (t01, t02, t05–t07, t15). Goldens are not vendored.

## Status meaning

| Status | Meaning |
|---|---|
| PASS | Criterion met. |
| FAIL | The feature **is** in the tree and misses its criterion: a real bug. |
| XFAIL | A probe (`tests/probes.py`, source-text check) says the feature is not in the tree yet. The reason names the phase. When the feature lands, the probe flips and the real assertion runs. |
| SKIP | node, zig or `--slow` is missing. |

## What each file covers

| File | Phase | Criteria encoded |
|---|---|---|
| `test_p0_engine.py` | P0.1 | Denormal guard in the source. Silence costs ≤ 1.5× playing and ≤ 0.5 budget (colour off) / 0.75 (colour on). |
| | P0.2 | Play T30 within **±8 %** of the dial (task spec; the roadmap says ±10 % and run_all ±15 %) for 1.8 / 0.8 / 4.0 s scenes, 500 Hz–8 kHz. T60 independent of Dffs (0 / −0.5 / −0.9). 9/11 kHz late T60 ≤ 1.25× dial with no narrow-band peak > 6 dB. Render T30 ±8 % (slow). decay_lock off ⇒ line_t60 = 0. |
| | P0.3 | jitter_D does not move Dffs. |
| | P0.4 | FDN-only Play-vs-Render null ≤ −30 dB gate, with −60 dB reported as the roadmap target. |
| | P0.5 | `/api/defaults` == client state (names the K5 mismatches). scipy in requirements. loop_mix not dead. diffusion_master clamped to **[−0.5, 0]**. One diffusion_master value, **−0.25**, everywhere including `app.js`. |
| `test_p1_blob.py` | P1 | WORKLET_VER consistent (live_fdn.js, index.html `?v=`, repo tests). BLOB_LEN == packer (t01). wasm == C (t02). v2 header/sections, MAX_BLOB ≥ 16384, old wasm silent on v2 (xfail until P1). |
| `test_p2_air.py` | LOCK / P2 | Direct is air-free in Play and Render (humidity 0 vs 1, bit-identical). No air on the FDN return (C: every `tint()` acts on `x*inj`; none in `read_peaked`/`diffuse`; Python: air only in `build_inject_from_taps`). Humidity 1-pole and shelf are separable stages (combined == product). Render stage order image → air → surfaces → mic. ISO fit, `air_shelf=0` null, Play/Render early null (xfail until P2/P4). |
| `test_p3_p4_surfaces.py` | LOCK / P3A / P3B / P4 | Per-hit cascade is serial: stages([A,B]) == stages(A)+stages(B), response == product. Render cascades all hits. Curtains wall-only; mute-all; Play cascade null / bypass / CPU (xfail until built). |
| `test_p5_p6.py` | LOCK / P5 / P6 | **No scattering inside the FDN loop** (C `diffuse`/`read_peaked`/`fwht`, Python FDN class). Scatter s=0 bit-identical, scatter after air, energy (xfail). Omni source identity, tail yaw-invariance (xfail). |
| `test_decisions_2026_09_28.py` | LOCKED 28 Sep | K1 single `YAW_X_SIGN` (Python == JS, no second sign); **source at left ⇒ L louder and earlier** for XY 90/120, ORTF, NOS, DIN, MS (Play; Render slow for ORTF/XY90/MS). K2 `air_lp` default 0. K3 default source gives **29 distinct delays per bus** (and an empty API body gets 2.6/1.2); client matches. K4 FDN-first defaults and **no stale-early replay** when the early fader is raised mid-play (wasm `switch` mode). Headroom: trim table shape, **t14 FDN bus ±0.5 dB of pre-F2**, whole mix informational (XFAIL with numbers). |
| `test_locks.py` | LOCK | Unscaled ±1 Hadamard (Python matrix, C fwht has no scale). 1/r² geometric level. All 32 early images inject into the FDN. Two diffusion layers on separate keys (xfail until P0.3). |
| `test_colour_sos.py` | COLOUR | 20 SOS tables match their preset hashes (48k, and **44.1k tables match too**). AT-C1 48k ≤ 0.5 dB. AT-C4 44.1k ≤ 0.6 dB (**all 20 mics**). **Unsupported rates (32k/88.2k/96k): colour off with a notice** (decision 7). Stable poles at 44.1k/48k. **numpy vectorised SOS == Build's loop** (`6_colour_per_rate/tools/apply_sos_fast.py`). HPF-on < 100 Hz ≤ 0.5 dB. **Two sources apart fit MAX_IRS**. Colour CPU (t15). |

## Results on the box (VERIFIED, 28 Sep 2026, final run 22:22–22:27 BST)

| Tree | PASS | FAIL | XFAIL | SKIP | Log |
|---|---|---|---|---|---|
| Latest snapshot (Build's 28 Sep IIR work) | 30 | 2 | 52 | 0 | `results/phase_latest_decisions.{log,json}` |
| **p5 = latest + patches 01–09** (F2, F3, locked decisions) | **60** | **2** | **22** | **0** | `results/phase_p5.{log,json}` |
| *(earlier)* latest / p4, before the decision tests | 30 / 38 | 2 / 3 | 33 / 24 | 0 | `results/phase_latest.*`, `phase_p4.*` |

**Real FAILs on p5:**

1. `test_colour_play_bank_fits_two_sources_apart`: **146 entries > MAX_IRS 64** (latest: 90). **Cause VERIFIED 1 Oct: K3's default source position** (p6: 146 at 2.6/1.2, 90 with the source pinned at 3.0/1.5, 87 with one source). Build raised MAX_IRS to 128 on 29 Sep, which still does not fit 146. Play colour is silently off with two sources. Build's call (raise MAX_IRS, or bucket angles; see `6_colour_per_rate/README.md`).
2. `test_p0_2_t60_play_within_8pct[small_lock08]`: 500 Hz T30 **0.884 s (+10.5 %)** with diffusion −0.25 (it was 0.722 s, −9.8 %, at −0.5). The other 14 band×scene values are within ±8 %. ASSUMED estimator variance in a small room.

- The AT-C4 44.1k FAIL on latest (U87 omni 0.69 dB, NT2A omni 0.62 dB) **passes on p5** with the 44.1k tables (worst 0.408 dB).
- XFAIL on p5: the unbuilt phases (P1 v2 blob, P2 ISO air, P3/P4 surfaces, P5/P6, the separate diffusion layer), plus `test_headroom_t14_whole_mix_informational` (+1.61 dB; direct/early not trimmed, an open decision).
- On latest, the decision tests mostly XFAIL (features not in the tree). The latest run was made at 22:0x BST, before the t14 pin moved to diffusion −0.25; its headroom tests XFAIL either way (no trim table).

## 1 Oct 2026: Build's 29 Sep tree

| Tree | PASS | FAIL | XFAIL | SKIP | Log |
|---|---|---|---|---|---|
| Build's tree (snapshot 1 Oct 07:36) | 36 | 0 | 48 | 0 | `results/phase_new1001.{log,json}`, `results/run_all_new1001.*` |
| + rebased patches (`p6`) | 60 | 2 | 22 | 0 | `results/phase_p6.{log,json}`, `results/run_all_p6.*` |

- The new-tree log shows 36/1/47. The 1 FAIL came from a bug in `test_headroom_t14_whole_mix_informational`, which raised instead of XFAILing when the trim table was absent. It is fixed and re-run: XFAIL.
- See `../NEXT_SESSION_PLAN_2026-10-01.md`.

## Changes in this round (28 Sep, decisions)

- New `tests/test_decisions_2026_09_28.py` (18 tests on p5, all PASS except the informational XFAIL).
- `test_colour_sos.py`: the 88.2/96k informational test was replaced by the 44.1k-table and unsupported-rate tests; stability now covers 44.1k/48k only; added the numpy SOS equality test.
- `test_p0_engine.py`: clamp must be exactly [−0.5, 0]; the single value must be −0.25.
- `harness/run_all.py` t14:
  - Pins sx 3 / sy 1.5 / air_lp 0.25 / diffusion −0.25.
  - Reference re-measured on latest: FDN −27.18 dB, mix −16.37 dB, peak 0.512.
  - Asserts the FDN bus within ±0.5 dB and reports the mix delta.
  - p5: FDN −27.09 (+0.09) PASS; mix −14.76 (+1.61); peak 0.559 at the tree defaults.
- `harness/lib/wasm_run.js`: new `switch` mode (burst, then total output with parameter changes at given times) for the K4 replay test.

## Integration with run_all.py

- Same scenes (`harness/run_all.SCENES`), the same Ctx helpers, and the same PASS/FAIL/XFAIL/SKIP vocabulary.
- `run_phase_tests.py` prints the same kind of one-line-per-test table and writes JSON.
- Suggested flow after any engine change:
  1. `run_all.py`
  2. `run_phase_tests.py --slow`
  3. `pytest software/tests`

## Added 1 Oct 2026: `tests/test_mirror_symmetry.py`

Ten tests (one is `--slow`) for the Two sources + Mirror asymmetry. See `../MIRROR_ASYMMETRY_BRIEF.md` §5.

- **Criterion:** A vs mirrored B, at most 0.1 dB per 1/3-octave band, null at most −60 dB.
- **Status:** XFAIL until the fix lands; the probe is a symmetric `LIVE_32` plus `fdn_b` in `mic_colour/live_bank.py`.
- **Harness change:** `harness/lib/wasm_run.js` `buildRoute` now emits 326 ints (`fdn_b`, falling back to `fdn`). This is backward compatible: worklets with ROUTE_LEN 230 copy only the first 230, so results on old trees are unchanged (VERIFIED).
