# CPU bench for Play's WASM engine

Idle's PC has no `node` (VERIFIED with `where.exe` on 2026-09-27), and nothing was installed. So the PC bench is a self-contained page instead.

**`live_stereo_cpu_bench.html`** (about 7 MB, works offline)
- **How to use:**
  1. Double-click it (Chrome, Edge or Firefox).
  2. Press **Run**. It takes about 3 minutes.
  3. Press **Copy results** and paste them back.
- **What it measures:** per-128-sample-block cost on the main thread (budget 2.667 ms at 48 kHz), for:
  - 3 engines: the current shipped wasm, the fix F1+F2+F3, and the fix + F5.
  - 3 cases each: 1 source colour off, 1 source colour on, 2 sources colour on.
- **Windows per run:** 6 s of noise ("play"), then silence measured from 4 to 10 s after the stop ("silence").
  - The "ratio" (silence/play) column exposes the denormal bug: it is > 1.5 on the current engine.
- It uses the same room blobs, IRs and routing as the box tests (std room, decay lock 1.8 s, humidity 0.5).
- **Numbers vs the real app:**
  - Main-thread timing should be close to AudioWorklet cost (ASSUMED).
  - The real app also spends time in the browser's audio graph, so treat these numbers as engine-only.
- Generator: `make_bench_page.py` (needs the box work dir). Rebuild after changing the wasm.

Box smoke test of the page's own JS (node with stubbed DOM, 1 s windows, box Xeon; indicative only):

| engine | case | play ms | silence ms |
|---|---|---|---|
| current | 1 src, colour off | 0.60 | **3.78** |
| current | 1 src, colour on | 1.29 | **4.39** |
| current | 2 src, colour on | 1.51 | **15.5** |
| fix F1-F3 | 1 src, colour off / on / 2 src | 0.70 / 1.35 / 1.61 | 0.53 / 1.28 / 1.53 |
| fix + F5 | 1 src, colour off / on / 2 src | 0.85 / 1.56 / 1.95 | 0.85 / 1.45 / 1.89 |
