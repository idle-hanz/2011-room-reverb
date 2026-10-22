# C / WASM performance roadmap (after the 26 Sep C rewrite)

**Written:** Sat 26 Sep 2026, ~22:00 BST
**All timings are box measurements** (shared Linux Xeon VM, Node 20 / V8, gcc 12-class, zig 0.16 from `pip install ziglang`), per 128-sample block. The budget is **2.667 ms at 48 kHz**. The user's PC is not measured.

## 1. Where we are (VERIFIED, see live_play_fix_audit.md)
- **Play** = one C core (`engine/live_stereo.c`) → WASM (`zig cc -target wasm32-freestanding -O3 -msimd128`), driven by the thin shim `fdn_worklet.js`. Rebuilding on the box gives bit-identical output to the shipped wasm.
- **Render** = Python/numpy (`engine/fdn.py`, `render_pipeline.py`). `fdn_core.c` (ctypes) is legacy and skipped when Dffs are present. The tests build `live_stereo.c` natively as a `.dll` for null tests.
- **Cost (WASM, user settings):**
  - FDN + Early, colour on: 1.214 ms (45.5 %); bypass: 0.482 ms.
  - Two sources, colour on: 1.770 ms (66.4 %).
  - The colour FIR is ~60 % of the total.
  - Native gcc −O3 is ~1.2–1.4× faster than WASM (1.009 ms / 1.276 ms).
- **Silence (subnormals):** 3.6–3.9 ms/block native and 3.8 ms WASM once the input stops, versus 0.32–0.37 ms with FTZ/DAZ forced on (native only). **This is the most urgent performance item.**

## 2. Scattering stage cost (Track C prototype kernel; box)
- **Kernel,** per line per sample:
  - 1 fractional read (specular) → biquad;
  - K sparse cluster reads → sum → biquad.
- **Two layouts benchmarked:**
  - **scalar:** per-sample, all lines interleaved;
  - **block-major:** per line: 128 interpolated reads into a mirrored history ring, then K contiguous axpy passes, then the two biquads.

  The block-major layout is what should ship.
- **"Lines"** = cluster-carrying early taps. **Play has 3 buses × 32 = 96 per source, and 192 with two sources.**

**Block-major (ms per 128-block):**

| lines N | K | native gcc -O3 | WASM (zig -O3 -msimd128) | JS (V8, Float32Array) |
|---|---|---|---|---|
| 32 | 0 (read+spec biquad only) | 0.021 | 0.052 | 0.044 |
| 32 | 8 | 0.029 | 0.056 | 0.114 |
| 32 | 16 | 0.039 | 0.060 | 0.180 |
| 32 | 24 | 0.049 | 0.065 | 0.248 |
| 64 | 16 | 0.080 | 0.121 | 0.368 |
| 128 | 8 | 0.123 | 0.233 | 0.478 |
| 128 | 16 | 0.163 | 0.247 | 0.740 |
| 128 | 24 | 0.200 | 0.265 | 1.008 |

**The scalar per-sample layout is much worse** (WASM N=32 K=16: 0.62 ms; N=128 K=16: 2.83 ms, which is over budget).

Raw logs: `scattering_fitter/bench/{native_scalar.txt,native_block.txt,node_results.txt}`.

### 2.1 Budget table (current engine + scattering, WASM, box)
The scattering line is an **upper bound**: the K=0 part duplicates a read the early lane already does. Values are interpolated between the N=64 and N=128 rows.

| Case | today | + scattering K=16 | total | % of 2.667 ms |
|---|---|---|---|---|
| 1 source, colour on (96 cluster lines) | 1.214 | +0.18 | ~1.40 | ~52 % |
| 1 source, colour bypass | 0.482 | +0.18 | ~0.66 | ~25 % |
| 2 sources, colour on (192 lines) | 1.770 | +0.37 | **~2.14** | **~80 %** |
| 2 sources, colour on, K=8 | 1.770 | +0.35 | ~2.12 | ~79 % |
| silence tail today (no FTZ) | 3.8 | — | **3.8** | **>140 %** |

**Recommendations:**
1. Fix denormals first (§3).
2. Ship scattering with K=16 for one source, and K=8 or "L/R buses only" for two sources.
3. Consider skipping clusters for taps whose scattered energy is below −40 dB relative to their specular energy (most smooth-wall taps; see the prototype, where reflected scattered share is ≤ 5 % below 2 kHz).

## 3. Safety rules for the C core (apply to Play and Render builds)
- **Denormals.** WebAssembly supports IEEE subnormals but exposes **no FTZ/DAZ control**; native SSE `_mm_setcsr` tricks are unavailable in wasm [EMSIMD; WASMdesign148; WASMsimd2].
  - **Remedy (pick one, apply to every IIR/allpass/1-pole state and to float ring writes):**
    - add and subtract a tiny alternating offset (±1e-18 … 1e-20) per block into recursive states; or
    - clamp |state| < 1e-15 → 0 once per block [EarLevel].
  - Add a CI test: 2 s of noise, then 60 s of silence. **Per-block cost must stay within 1.5× the playing cost.**
- **No allocation in `process()`.** Today: `live_bind` lays out one arena; `live_stereo` does not allocate (VERIFIED by reading). Keep it that way: the scattering cluster tables (offsets, amplitudes) live in the room blob or arena and are rebuilt on param change, off the audio thread.
- **Watchdog.** Keep `scrub()` (non-finite → reset) and `soft_limit()`. Add:
  - a per-block energy watchdog on the FDN state (if Σy² > 1e4 × the running mean, reset lines and post a message);
  - a CPU-time watchdog in the worklet shim: if `currentTime` advances slower than wall time, drop to "early only" and report via `port.postMessage`.
- **Parameter smoothing.** Delays are already smoothed (`SMOOTH`). Crossfade cluster tables over one block when geometry or materials change: keep the old and new tables and ramp 0→1. Never swap mid-block.
- **Deterministic RNG** for cluster offsets and signs: key = (seed, bus, line, face-set). This matches the Surfaces Δd SHA-256 convention and keeps Render/Play bit-comparable.

## 4. AudioWorklet + WASM best practice (cited)
- WASM in `AudioWorkletProcessor` avoids JS JIT/GC hiccups; the render quantum is 128 frames and "only 3 ms at 44.1 kHz" [CHOI2018].
- Compile the module on the main thread and transfer it via the `AudioWorkletNode` constructor options ("pattern B"), so that compiling doesn't glitch the stream [CHOI2018]. **The app already does this** (bytes in `processorOptions`). Improvement: pass a compiled `WebAssembly.Module`, not bytes.
- If a kernel needs blocks ≠ 128, use a ring buffer inside the processor. This adds latency and **does not add time budget** [CHOI2018; GCLwasmRB].
  - The app's FIR partition = 128 (+128 samples latency). Don't raise the partition size to save CPU without accepting more latency.
- Keep audio data on the WASM heap. Copy in/out once per quantum (the HeapAudioBuffer pattern) [CHOI2018]. Today the shim copies 2 × 128 floats each way, which is fine.
- A worker + SharedArrayBuffer pattern exists for heavy C/C++ ports. It requires COOP/COEP headers and is looser-synchronised [CHOI2018; GCLsab; ringbuf.js]. **Not needed at current load.**
- SIMD: use `-msimd128`. Emscripten documents that denormal/rounding modes cannot be controlled in wasm SIMD [EMSIMD].

## 5. Roadmap: one shared C core for Render (ctypes) and Play (WASM)
1. **Denormal guard + silence CI test** (§3). Small, and fixes a real overrun.
2. **Split `live_stereo.c` into kernels, each with a pure-C API** (no JS or Python types):
   - `fdn_loop.c`: Hadamard FWHT (N=32/64/128 templated), `diffuse()`, peaking. Unlock N=64/128 via a compile-time N or a runtime N ≤ 128 with a fixed arena.
   - `early_taps.c`: fractional tap read + **per-hit serial cascade** (absorb biquads per hit, the same stages Render builds in `surface_filter_stages`) + the Track C specular shelf.
   - `scatter.c`: velvet clusters (block-major, mirrored history ring), scatter shelf.
   - `colour_fir.c`: partitioned FFT (already SIMD `mac_bins`). This is the biggest cost; consider non-uniform partitioning (a short head partition plus longer tail partitions) to cut the FFT count without adding latency.
3. **Render uses the same C via ctypes.** Build `live_core.dll` / `.so` from the same sources. Python keeps geometry and params only (image sources, fits, packing), and Render calls `core_process(blob, in, out, n)` offline. This gives true Render = Play parity.
   - It also resolves the z⁻¹ vs same-sample difference: pick one (z⁻¹ is simpler and already in Play), and have Render call the same code.
   - Retire `fdn_core.c` and the dead `loop_mix` payload.
4. **Memory layout:**
   - Keep per-line interleaved lanes (FDN/early A/B). They're good for per-sample loop reads.
   - For scattering, use the block-major history ring per line (2× mirrored, 2048 samples ≥ 30 ms cluster + 128).
   - Keep hot state (biquad z1/z2, delays) in SoA arrays of N for SIMD over lines in the FWHT and loop update.
5. **SIMD:**
   - FWHT butterflies across 4 lines (f32x4) or f64x2.
   - Cluster axpy over time (f32x4, contiguous).
   - The partitioned FFT is already SIMD.
   - Biquads stay scalar per line but can be run 4 lines at a time (SoA) where latency allows.
6. **Test harness** (extend `tests/test_live_stereo.py` + `v2/wasm_harness.js`):
   - **Null test** native `.dll/.so` vs WASM on the same blob and input. Expect bit-identical, or ≤ −140 dBFS if `-ffast-math` differs. Today native and WASM are the same source; I verified shipped vs rebuilt WASM = 0 diff.
   - **Null test** Render (ctypes core) vs Play (WASM), ≤ −100 dBFS after the parity decision in item 3.
   - **CPU regression:** fixed blobs (user settings: 1 source colour on/off, 2 sources), 3000 blocks. Fail if more than 10 % over baseline on the CI machine. Include the silence-tail case.
   - **Stability:** g√N 0.99, Dffs ±0.98, 60 s, no NaN, and tail decays.
   - **Track C:** scattering off (all s=0) ⇒ bit-identical to today; energy per octave within ±0.5 dB (see brief).

## References
- **[CHOI2018]** H. Choi, "Audio worklet design pattern", Chrome for Developers blog, 2018. https://developer.chrome.com/blog/audio-worklet-design-pattern
- **[GCLwasmRB]** Chrome Labs Web Audio Samples, "Ring Buffer in AudioWorkletProcessor". https://googlechromelabs.github.io/web-audio-samples/audio-worklet/design-pattern/wasm-ring-buffer/
- **[GCLsab]** Chrome Labs, "AudioWorklet, SharedArrayBuffer, and Worker". https://googlechromelabs.github.io/web-audio-samples/audio-worklet/design-pattern/shared-buffer/
- **[ringbuf.js]** P. Adenot, ringbuf.js. https://github.com/padenot/ringbuf.js/
- **[EMSIMD]** Emscripten docs, "Using SIMD with WebAssembly" (no control of denormal/rounding modes). https://emscripten.org/docs/porting/simd.html
- **[WASMdesign148]** WebAssembly design issue #148 "What about subnormals?". https://github.com/WebAssembly/design/issues/148
- **[WASMsimd2]** WebAssembly SIMD issue #2 "Allow flushing of subnormals". https://github.com/WebAssembly/simd/issues/2
- **[EarLevel]** N. Redmon, "Floating point denormals", EarLevel Engineering, 2019. https://www.earlevel.com/main/2019/04/19/floating-point-denormals/
