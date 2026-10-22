# Package 1: IIR (SOS) mic colour verification

**Tree tested:** Build's live `software\`, snapshot taken 28 Sep 2026 at 20:40 BST (`snapshot_2026-09-28_2040`), compared with the 27 Sep snapshot. The PC tree was not written to.

**Tags:** VERIFIED means a script in `tools/` measured it and the number is in `results/`. ASSUMED means it is a judgement.

## What Build changed (VERIFIED, diff 27 Sep → 28 Sep)

- **New files:**
  - `mic_colour/sos_fit.py`
  - `mic_colour/sos_table.py`
  - `mic_colour/sos_tables/*.json` (20 mics)
- **Changed Python:** `colour.py`, `live_bank.py`, `modes.py`, `render_pipeline.py`, `app_server.py`.
- **Changed Play side:**
  - `engine/live_stereo.c`: SOS `run_sos` and `design_sos` next to the FIR path.
  - `static/js/live_fdn.js` and `fdn_worklet.js` (comment only).
  - The wasm.
  - `index.html` and `app.js`.
  - `WORKLET_VER` 28 → 30.
- **Other:** `requirements.txt` gains scipy. There is a new `colour_impl` switch, `"sos"` (default) or `"fir"`, which applies to both Render and Play.
- **F1 is also in:** Build already landed the denormal guard (`LS_TINY`/`LS_DC`, `ls_flush` in `tint()`, the FIR silent-partition guard). `run_all` t09 passes: silence costs 0.47–0.59 ms/block.

## Pass/fail summary

| Check | Criterion | Result | Verdict |
|---|---|---|---|
| Tables vs 27 Sep prototype | identical parameters | all 20 identical to `wtable_params_48000.json`; every preset hash matches | PASS |
| SOS vs fitter model, 48 kHz (AT-C1) | ≤ 0.5 dB, 20 Hz–20 kHz, 1–180° | worst 0.46 dB (U87 Omni) | PASS |
| SOS vs fitter model, 44.1 kHz (AT-C4) | ≤ 0.6 dB | **U87 Omni 0.69 dB** (180°, 14.8 kHz); **NT2A Omni 0.62 dB** (180°, 16 kHz); other omnis 0.53–0.55 | **FAIL, 2 of 20** |
| SOS at 88.2 / 96 kHz | no Build criterion | up to 1.3–2.1 dB (Schoeps Omni 2.12 dB); U87 Omni about 1 dB even below 8 kHz. The 48 kHz parameters are not rate-independent | informational |
| SOS vs MEASURED (Zenodo) | adds nothing to the fitter's own miss | SOS adds ≤ ~0.1 dB over model-vs-measured (e.g. SM57 19.6 / 3.31 dB max/RMS, the same as the model). The large maxima are pattern nulls (a model limit) | PASS |
| Stability | all poles inside the unit circle | worst radius 0.998927 (NT2A Cardioid, 96 kHz); float32 coefficients change the response ≤ 0.043 dB | PASS |
| HPF on (10 mics), < 100 Hz | the old FIR missed by 14.5–23 dB | SOS vs model+HPF ≤ 0.19 dB below 100 Hz (FIR: 15.5–26.3 dB). At ≥ 100 Hz: 0.37 dB at 48k, 0.69 dB at 44.1k | **PASS (the miss is fixed)** |
| Play null, SOS vs old FIR | ≈ same sound where the FIR was right | lock18 −60.9 / −53.0 dB, octave difference ≤ 0.025 dB; unlocked −58.2 / −56.1 dB; two sources (default B) −60.9 / −53.5 dB. `u87_hpf` −26.7 dB (0.77 dB at 125 Hz: this is the FIR being wrong) | PASS |
| CPU per 128-sample block (node wasm, median of 3) | AT-C3 | 1 source: SOS 0.626, FIR 1.230, colour off 0.531 ms (colour +0.095 ms). 2 sources: SOS 0.983, FIR 1.447, off 0.852 ms | PASS (SOS about 2× cheaper than FIR) |
| Play (C `run_sos`) vs Render (Python `apply_sos`), direct path | same filter | identical within 1e-7 dB; HPF case at 50 Hz is −18.196 dB in both | PASS |
| Render null, SOS vs FIR | — | −59.7 / −52.2 dB | PASS |
| Render cost | not slower than FIR | full 1.5 s Render IR: **SOS 22.8 s vs FIR 13.8 s vs bypass 14.0 s**, because of the pure-Python loop | **FAIL (perf)** |
| Two sources placed apart | colour applied | **90 colour entries > MAX_IRS 64**. The worklet fails and colour is silently off (the bug also exists on 27 Sep) | **FAIL (existing bug)** |
| Sample-rate mismatch (K11) | not silent | unchanged: colour turns off silently when `colour.sr != ctx.sampleRate` | open (known) |

## Bugs, with file and line (latest snapshot)

1. **Play colour bank overflow with two sources.** `engine/live_stereo.c:55` (`MAX_IRS = 64`) and `static/js/fdn_worklet.js:158-159` (`nIrs > 64` → `_fail("Live mic filters are too long.")`).
   - Entries are keyed per exact angle rounded to 1e-4° (`mic_colour/live_bank.py:22-23`, `_deg`).
   - With B at `sx_b=1.5, sz_b=5.5` the bank needs 90 entries. Play output with SOS and with FIR is then bit-identical: no colour at all. VERIFIED (`results/play_checks_two.json`, test `test_colour_play_bank_fits_two_sources_apart`).
   - Fix, either:
     - (a) raise MAX_IRS for SOS entries (only 17 floats each; the C `sos[MAX_IRS][MAX_SOS*5]` arrays are cheap); or
     - (b) bucket the bank angle to 1° (colour changes < 0.05 dB per degree, ASSUMED from the model's smoothness); or
     - (c) both.

     In every case, report the failure in the UI instead of silently dropping colour.
2. **Render SOS is a per-sample Python loop.** `mic_colour/sos_fit.py:123-142` (`apply_sos`).
   - Cost: 55 ms per 1 s buffer, against 0.55 ms for `scipy.signal.sosfilt`, which gives **bit-identical** output (VERIFIED). scipy is now in `requirements.txt`.
   - Fix: `from scipy.signal import sosfilt; return sosfilt(sos_as_scipy, x)`, with `sos_as_scipy = [[b0,b1,b2,1,a1,a2], ...]`. Keep the loop as a fallback when scipy is missing.
3. **44.1 kHz accuracy (AT-C4) fails for 2 omnis.** Build's test checks only SM57 at 44.1k (`tests/test_mic_colour_relative.py:727-733`).
   - The tables were fitted at 48 kHz and reused at other rates.
   - Options: per-rate tables (fit at 44.1k too), or a bilinear pre-warp of the corner frequencies. **DECISION FOR IDLE** whether 0.69 dB at 14.8 kHz at 180° is audible enough to matter (ASSUMED: marginal).
4. **Stale-table risk.** `mic_colour/sos_table.py:38-51` (`_load_one`) checks `schema` but never `preset_hash`, so an edited preset would silently use old SOS parameters. Fix: compare with `preset_hash(store.get(mic))` and fall back to FIR or identity with a warning. All 20 hashes match today (VERIFIED).
5. **No table builder.** The brief's step 2 (fit tables from presets) is missing. Only `write_v1_from_v0` exists (`sos_table.py:85-95`), and it hard-codes `repo_root/handoff_build_support/research/cheap_colour/results/wtable_params_48000.json`, a handoff folder that will not exist in the repo. A new preset cannot get a table.
6. **Docstring mismatch.** `sos_table.py:64-68`: `pack_for` docstring says it returns None for a missing table, but it returns `False`. Callers must treat both as identity.
7. **Silent truncation.** `engine/live_stereo.c:737` (`design_sos`) silently truncates when k > MAX_SOS. Current tables need k ≤ 4 (3 sections plus the HPF), so this is safe today (VERIFIED). Add an assertion in the Python packer.
8. **K11 is unchanged.** `static/js/live_fdn.js:162` sets `on = colour.on && colour.sr === ctx.sampleRate`, so colour silently turns off on a mismatch. `live_bank.py` returns "off" when the rate is unknown. Suggest showing a status message.
9. **Play air/shelf still uses 44.1 kHz coefficients while Play runs at 48 kHz (F4).** This is not a colour-file issue; it is noted here because it also affects Play-vs-Render.

## Not measured

- Listening. No A/B was done; Idle should listen to at least the U87 Omni at 44.1k and the two-source scene after bug 1 is fixed.
- Real-time behaviour in a browser (only node + wasm was measured).

## Files

- `tools/eval_sos.py` computes the model, MEASURED and FIR comparisons, stability, HPF and rates. Run it as `--sw <software> --mf /workspace/mic_fitter --out results/`.
- `tools/play_checks.py` covers the Play nulls, CPU, Render cost and null, and the direct-path Play-vs-Render check. It needs node.
- `tools/render_ir_impl.py` is `render_ir` plus `colour_impl`.
- `results/summary_table.md` has the per-mic table (all 20 mics).
- `results/eval_sos.json` has the raw numbers.
- `results/play_checks*.json` hold the Play/Render numbers.
