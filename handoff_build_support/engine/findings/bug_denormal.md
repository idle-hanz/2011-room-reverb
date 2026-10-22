# Bug 1: denormals in silence push Play's cost over budget

Snapshot: `/workspace/build_support/snapshot_2026-09-27/software` (taken from the PC on 2026-09-27). The shipped `static/wasm/live_stereo.wasm` is bit-identical in output to a zig rebuild and to a native gcc build of `engine/live_stereo.c`, so native timings are a valid stand-in (VERIFIED, IR max diff 0).
Budget: 128 samples at 48 kHz = 2.667 ms per block.

## Reproduction (VERIFIED)
- Harness: `tools/run_native.c` in `bench` mode (native gcc -O3, optional hardware FTZ/DAZ flag) and `tools/wasm_run.js` in `bench` mode (the real `fdn_worklet.js` packer plus the wasm in node). Scene: the page scene with humidity 0.5, decay lock 1.8 s, 6 s of noise at ±0.3, then silence.
- Per-block cost 4–10 s after the input stops:

| Build | Case | Playing | Silence (current) | Silence (fixed) |
|---|---|---|---|---|
| native gcc, box Xeon | colour off | ~0.36 | **3.7–3.8** | 0.38 |
| native gcc, same code with hardware FTZ/DAZ | colour off | – | 0.35–0.37 | – |
| WASM in node (box) | colour off | 0.77 | **4.03** | 0.56 |
| WASM in node (box) | colour on | ~1.3 | **4.66** | 1.26 |
| WASM in node, HTML bench page run under node (1 s windows, smoke test) | 2 sources, colour on | 1.5 | **15.5** | 1.53 |

All numbers are in ms per block, measured on the box Xeon, not Idle's PC. Numbers from the 1 s smoke test are noisy, but the 2-source silence blow-up (5.8× budget) is well outside that noise.
- Hardware FTZ/DAZ on the unchanged code brings the cost down to the fixed level, which proves the extra cost is subnormal arithmetic (VERIFIED). WebAssembly has no FTZ/DAZ control, so the fix has to be in code.

## Root cause (VERIFIED, line numbers from the snapshot's `engine/live_stereo.c`)
- `tint()` (lines 894–930) holds the injection-side air 1-pole (`airZ*`) and the humidity shelf biquad (`sz1*`/`sz2*`) for every line and bank (4 kinds × 96 lines). It runs every sample even when its input is 0. After the input stops, those double states decay exponentially into the subnormal range and stay there for a long time.
- `tools/denorm_probe.c` result after 5 s of silence: **96/384 air states and 128/768 shelf states subnormal**. Peaking filters, feedback (`fb`) and the colour FIR had none at that point.
- Only happens when humidity > 0 (air on). With humidity 0 the cost does not blow up (VERIFIED).
- A secondary source is the float early-lane ring, which briefly held about 279k subnormal samples around 1 s after the stop, plus partitioned-FIR partitions fed tiny non-zero inputs while the FIR goes cold (`fir_part`, near lines 1190–1215).

## Fix (proven in `work/sw_fix/software`; diff in `briefs/live_stereo.c.fix.diff`)
1. `static inline double ls_flush(double x)` returns 0 when |x| < 1e-20. Apply it to `z`, `s1` and `s2` at the end of `tint()`. It is a feedforward state, so this has no audible effect.
2. Add `#define LS_DC 1e-18` (about −360 dBFS) to every FDN loop input (`xinArr[i]` and `mixed`, 4 places). Recirculating values then never sink into the subnormal range. The DC is far below audibility and is removed by nothing; it just sits there at 1e-18.
3. In `fir_part`, a partition detected as silent writes exact zeros into `g_re[PART+i]` and `prev[i]`.
- Tried and **rejected**: per-sample flushing of ring writes, feedback and peaking states. It cost 0.15–0.25 ms per block natively and isn't needed.
- Measured after the fix: silence stays ≈ playing cost or lower for 42 s. The colour FIR goes cold at about 12 s and costs drop further. Without the loop DC (item 2), only a small bump appeared (0.43 vs 0.36 ms at 60 s with T60 8 s), so item 2 is cheap belt-and-braces (VERIFIED).
- Output effect: the added 1e-18 DC and flushes below 1e-20 are ~−360 dBFS, far below float32 resolution of any real signal (ASSUMED inaudible, by magnitude). No separate F1-only golden null was recorded. The `sw_fix` goldens differ from the snapshot because of F2/F3 (see `bug_tail_length.md`). If Build lands F1 alone, t03 should still pass at −100 dB (ASSUMED; check it).

## Acceptance
- `tests/run_all.py` **t09_silence_cpu**: silence cost (late window after 2 s playing + 14 s silence) must be ≤ 1.3× playing cost and ≤ 50 % of budget colour off / ≤ 75 % colour on (× `--perf-scale`). Snapshot result: FAIL (4.02 vs 0.55 ms). `sw_fix` result: PASS (byp 0.555, col 0.677 ms).
- On the PC, open `bench/live_stereo_cpu_bench.html`. The "ratio" (silence/play) column should be ≤ 1.5 (page highlights > 1.5 in red) for the fixed engines.
