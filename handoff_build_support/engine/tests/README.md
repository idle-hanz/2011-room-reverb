# Engine regression / acceptance pack (`run_all.py`)

Run it after any engine change. It is read-only: it imports `software/` and writes only to a temp dir, `--out` and `golden/` (the latter only with `--regen-golden`).

```
python run_all.py --sw "/path/to/software"             # full run, ~4-7 min on the box
python run_all.py --sw "/path/to/software" --quick     # skip slow Render tests (t12, t13, t18)
python run_all.py --sw "/path/to/software" --only t09,t10
python run_all.py --sw "/path/to/software" --perf-scale 1.5   # slower machine: loosen CPU limits
python run_all.py --sw "/path/to/software" --regen-golden     # rewrite goldens (t03/t04 only)
```

## Requirements
- A Python that can import `software/app_server.py` (numpy, scipy, fastapi). The app's own `.venv` works, as does the box venv `/workspace/scratch_er_dropout/venv/bin/python`. Pass it with `--python`, or run `run_all.py` with it.
- `mic_fitter/` must sit next to `software/`, because the mic colour code loads it.
- `node` for all Play/WASM tests: it runs the real `static/js/fdn_worklet.js` packer and `static/wasm/live_stereo.wasm` through `lib/wasm_run.js`. **Idle's PC has no node (VERIFIED 2026-09-27), so run the pack on the box**, or install node first. Without node the Play tests report SKIP/ERROR.
- gcc or clang, optional, for t02 (checks the wasm really was built from `live_stereo.c`).
- Statuses:
  - PASS / FAIL.
  - SKIP: a tool is missing or `--quick` was used.
  - PENDING: the feature isn't built yet.
  - XFAIL: a known gap. It is reported but does not fail the run.
  - ERROR: the harness broke.
  - The exit code is 1 on any FAIL or ERROR.

## Tests and thresholds

| id | what | threshold | snapshot 2026-09-27 | sw_fix (F1-F3) | sw_fix_same (F1-F3+F5) |
|---|---|---|---|---|---|
| t01 | Python packer == worklet `packRoom` | bit-exact | PASS | PASS | PASS |
| t02 | wasm == native build of `live_stereo.c` | max diff ≤ 1e-6 | PASS | PASS | PASS |
| t03 | Play IR with features off vs golden (std_unlocked, std_lock18 × colour off/on, 1.5 s) | null ≤ −100 dB | PASS | FAIL (expected: F3 changes delays → regenerate) | FAIL (same) |
| t04 | Render IR vs golden (std_unlocked, BYPASS, 0.5 s) | null ≤ −100 dB | PASS | PASS | PASS |
| t05 | Source radiation omni == golden | null ≤ −100 dB | PENDING | PENDING | PENDING |
| t06 | Scattering amount 0 == golden | null ≤ −100 dB | PENDING | PENDING | PENDING |
| t07 | Tail energy (80 ms–1 s) invariant under source yaw 0/90/180 | spread ≤ 0.5 dB | PENDING | PENDING | PENDING |
| t08 | FDN stability, Dffs 0 / +0.98 / −0.98 / as-is, decay 8 s, 15 s noise + 15 s silence | finite, and last 5 s ≥ 3 dB below the first silent 5 s | FAIL (+0.98: −39.6 → −34.8 dB) | PASS | PASS |
| t09 | Silence CPU (denormals), WASM | silence ≤ 1.3× play and ≤ 50 % budget (colour off) / ≤ 75 % (colour on) | FAIL (4.02 vs 0.55 ms) | PASS | PASS |
| t10 | Play T30 500 Hz–8 kHz vs dial, 3 scenes | ±15 % | FAIL | PASS | PASS |
| t11 | Late 9/11 kHz T60 (slow HF residue) | ≤ 1.25× dial | FAIL (21.7 / 25.0 s) | PASS (1.81 / 1.80) | PASS |
| t12 | Render T30 vs dial (std, 1.8 s) | ±15 % | FAIL | PASS | PASS |
| t13 | Play vs Render: tail T30 ±10 %/band, octave balance ±1.5 dB, tail level ±1 dB, stereo correlation ±0.1, direct 0 smp / ±0.5 dB; early field is XFAIL | as listed | FAIL | FAIL (level −5.8 dB, balance, correlation) | XFAIL (early field only) |
| t14 | Level sanity, hot noise ±0.3 (−15.2 dBFS RMS), colour on | peak < 0.95, finite | PASS (0.498) | PASS (0.727) | **FAIL (0.997)**, see brief |
| t15 | Active CPU: 1 source + colour ≤ 60 % budget, 2 sources ≤ 85 % | × `--perf-scale` | PASS (1.17 / 1.77 ms) | PASS (1.25 / 1.80) | PASS (1.45 / 2.02) |
| t16 | Diffusion layers separate (a new surface Δd key, distinct from `diffusion`/`dffs`) | key exists | PENDING | PENDING | PENDING |
| t17 | Play follows `hadamard_n` | params n == 16 when asked | PENDING | PENDING | PENDING |
| t18 | FDN-only Play tail nulls Render | ≤ −30 dB | FAIL (+0.8) | FAIL (+1.4) | PASS (−47.5 / −48.3) |

- Result files: `results_snapshot_2026-09-27.json`, `results_candidate_sw_fix.json`, `results_candidate_sw_fix_same.json`.
- t16 was re-run on all three trees after a regex fix (its first version matched `"dffs"` and gave a false PASS).
- CPU numbers are from the box Xeon in node, not from Idle's PC.

Notes:
- **t08** forces the loop to g = 0.99/√N on trees without `line_t60`, and forces Dffs to +0.98, which the UI cannot reach today (Dffs ≤ 0 while `diffusion_master` = −0.5). It guards the unclamped server path and any future sign change.
- **t10–t13** use the `decay_lock` scenes. `std_unlocked` (Feedback slider, fdn_g 0.8) is the "features off" reference, and F2 must not change it.
- **t05–t07** turn from PENDING into real checks when the matching keys appear in `app_server.py`, `render_pipeline.py`, `surface_colour.py` or `engine/early_field.py`:
  - `source_pattern`/`source_radiation`/`source_directivity*`, set to `'omni'`
  - `scatter*`, set to 0
  - `source_yaw`/`src_yaw*`
  - If Build uses other names, adjust `find_key` patterns in the test.

## Goldens
- `golden/` holds float32 stereo IRs at 48 kHz: 4 Play and 1 Render, generated from `snapshot_2026-09-27` (hashes in `golden/GOLDEN_META.json`).
- **Regenerate only when an output change is intended and understood**:
  1. Land the change.
  2. Run the full pack and check that everything other than t03/t04 is as expected.
  3. `python run_all.py --sw <tree> --regen-golden`
  4. Commit `golden/` together with a note of why (e.g. "F3: Play delays rounded at 48 kHz").
- Expected golden impact of the brief's fixes:
  - F1 (denormals): none (ASSUMED; t03 should still pass).
  - F2 (line absorption): only the `std_lock18` goldens.
  - F3 (delay rounding at the Play rate): all Play goldens.
  - F5: goldens for any scene where Dffs ≠ 0 (all of them).
  - Render golden (t04, unlocked): unchanged by F1–F5 (VERIFIED on both candidate trees).
- Suggested order: land F1 → run (t03 must PASS) → land F2+F3 → run → regenerate goldens.
