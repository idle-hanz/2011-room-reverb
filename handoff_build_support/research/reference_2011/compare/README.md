# compare/: 2011 reference vs rebuild harness

The capture steps for Idle are in `../CAPTURE_GUIDE.md`. This folder turns his WAVs and JSON sidecars into a report.

```
PY=/workspace/scratch_er_dropout/venv/bin/python
$PY compare_ref.py --refs <dir of RR2011_*.wav + same-stem .json> --out <report dir> [--lock-variants] [--jobs 2]
```

| File | Role |
|---|---|
| `compare_ref.py` | Main harness. It maps the sidecar to a rebuild body (each mapping tagged VERIFIED/ASSUMED in `body_from_sidecar`), then renders `render_current`, `play_current`, `play_F1-F3` and `play_F1-F3+F5` (plus `lock_*` with `--lock-variants`). It measures both sides and writes `COMPARE_REPORT.md`, `compare_report.json` and `<stem>_edc.png`. |
| `rr_metrics.py` | Metrics: Schroeder EDC; T20/T30/EDT per octave (125 Hz–8 kHz); two-slope fit (early/late T60 and the knee); envelope late-T60 at 9 and 11 kHz (HF residue) and near-Nyquist energy; tail spectral balance re 1 kHz; L/R correlation (early 0–80 ms, late); first arrival and the sample-0 level re direct; `fine_timing` (normalised cross-correlation lag and null in W1 = first-pass images and W2 = 40–150 ms loop trips). |
| `rr_tree_driver.py` | Subprocess run per software tree (dump params, pack, and run the Render or the WASM Play IR). It does not write inside any tree. The Dffs-knob override is applied in memory. |
| `capture_template.json` | Sidecar schema `rr2011.capture.v1`. |
| `make_test_standins.py`, `run_standin_tests.sh` | **TEST-ONLY** stand-ins, clearly labelled, NOT 2011 data. |
| `test_standins/`, `test_reports/` | Stand-in inputs and the reports the harness produced from them. |

## Verdict logic

- **(a)** For the captures with Diffusion Master ≠ 0, the harness looks at whether the reference is two-stage (late/early T60 at 1 kHz: median ratio ≥ 1.5 and two-stage in ≥ 50% of captures). If it is, and the rebuild's unlocked late slope matches (median |ln err| ≤ ln 1.35), the answer is **KEEP** the two-stage tail and apply F2 to decay-lock only. If the reference is two-stage but the rebuild misses the late slope, the answer is: keep the structure, but first fix the Dffs scale (from the Diffuser "Diffusion" reading). If the reference is single-slope (ratio < 1.3 or < 25% of captures), the answer is **APPLY F2 generally**. Anything in between is MIXED: listen-test.
- **(b)** The decision is made at sample level. First, the first-pass images (W1) of the integer-delay `F1-F3` tree must line up with the reference (c1 ≥ 0.5). If they do, the harness compares the W2 null of the reference against `play_F1-F3` (z^-1 loop) and against `play_F1-F3+F5` (same-sample). The deeper null wins, provided it is ≤ −10 dB and at least 3 dB deeper than the other. If W1 does not line up (for example because the 2011 delay lengths use different rounding), the result is **INCONCLUSIVE**, with a weak decay/spectral-score hint, and it says which tree the images line up with best. That last note matters for F3.

## Stand-in test results (TEST-ONLY, 27 Sep 2026)

| Stand-in | What it is | (a) | (b) | As intended? |
|---|---|---|---|---|
| TS1 synth two-stage | Synthetic noise with two decay slopes | two-stage seen, rebuild slope does not match → "fix Dffs scale first" | inconclusive (synthetic, no images) | yes |
| TS2 synth single | Synthetic noise with one slope | APPLY F2 generally | inconclusive | yes |
| TS3 = play_current | Rebuild Play current (fractional delays) | KEEP (err 0.07) | inconclusive: flags that the images line up with play_current rounding (the F3 question) | yes |
| TS4 = play_F1-F3+F5 | Same-sample loop | KEEP | **SAME-SAMPLE**: W2 null −120 dB vs z^-1 −18.5 dB | yes |
| TS5 = play_F1-F3 | z^-1 loop | KEEP | **ONE-SAMPLE**: W2 null −120 dB vs same-sample −18.5 dB | yes |

The harness separates the two loop timings cleanly when the delay lengths match. With real 2011 captures, (b) is only decidable if the 2011 delay lengths line up with one tree's rounding. If they don't, the report says so, and F3 has to be sorted first (the optional 44.1 kHz capture helps here).

## Caveats

- The 2011 per-surface peak EQ, the Res one-pole (Mic Response < 19 kHz) and AGC are not mapped. The guide asks Idle to neutralise them.
- The Render is limited by `--render-secs` (default 8 s). Late T60 > 8 s is then fitted from a truncated tail, so use Play (15 s default) for long tails.
- All rebuild numbers in the reports come from actual renders. Nothing in the stand-in reports is 2011 data.
