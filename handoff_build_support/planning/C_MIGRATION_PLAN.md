# C migration plan — one C core for Play, Render and (later) the plugin

Written 27 Sep 2026 (BST). **Tags**

- **VERIFIED**: read in the snapshot (`planning/snapshot/software/`) or the briefs.
- **ASSUMED**: design proposal or estimate.
- **[n]**: numbered sources at the end.

This document gives Build a researched plan so the move to C is not improvised. It sits alongside BUILD_ROADMAP.md, where it is phase P7; parts of it (§6 denormals, §3 loop semantics) are needed as early as P0.

---

## 1. Where things are today (VERIFIED)

| Piece | Language | File(s) | Notes |
|---|---|---|---|
| Play block (FDN ×3 buses + tank B, early lanes, tint, in-loop peaking, colour FIR, direct fold) | C → WASM | `engine/live_stereo.c` (1481 lines) → `static/wasm/live_stereo.wasm` | `N=32`, `PART=128`, `FFTN=256`, `MAX_PART=64`, `MAX_IRS=64`, `MAX_FILT=112`, `LANES=4`, `MAX_BLOB=8192`. Line state and coefficients in double, rings in float. Fractional delays, `SMOOTH=0.0025`. |
| Worklet glue | JS | `static/js/fdn_worklet.js` (`BLOB_LEN=1981`), `static/js/live_fdn.js` (`WORKLET_VER=28`) | thin wrapper |
| Legacy fast FDN | C (.so via ctypes) | `engine/fdn_core.c` `fdn32_process` | dense 32×32 matvec, **no Dffs, no mic 1-pole**. Used only if `fdn_core.so` exists and neither is active. |
| Render FDN | Python | `engine/fdn.py` (`process_block_poly`, `diffuser_output_mix`, `dff_after_master`), `engine/fdn_stub.py` | per-sample Python loop (slow); integer delays; same-sample implicit Dffs solve |
| Early field | Python | `early_field.py`, `image_geometry.py`, `absorb_masks.py`, `surface_colour.py` | geometry, per-hit cascade (scipy `lfilter`) |
| Mic colour | Python + C (Play FIR) | `mic_colour/*` (`live_bank.py` builds Play partitions) | MEASURED_SHELF etc. |
| Pipeline / packing | Python | `render_pipeline.py` (`live_fdn_params` :1347, `_attach_loop_mix` :1337) | `n_had=32` hardcoded for Play |
| Server | Python | `app_server.py` | FastAPI |

**Parity gaps today (VERIFIED)**

1. Loop semantics: z⁻¹ in the Play diffuser feedback vs a same-sample solve in Render.
2. Fractional vs integer delays.
3. Play N fixed at 32; Render N from 8 to 128.
4. Play early taps have no per-hit surface cascade.
5. `loop_mix` is shipped but unused.

## 2. Recommendation in one paragraph

Build **one portable C99 core, `rr_core`, by splitting `live_stereo.c`**. Do not grow `fdn_core.c`; delete it after parity. Compile the same sources:

- with zig to `wasm32-freestanding` + SIMD128 for Play;
- with zig (or MSVC/clang) to a native shared library that Python calls through `ctypes`, so Render's DSP becomes the C core;
- later, with the same core, behind a thin CLAP (and optionally VST3) wrapper.

Keep geometry, coefficient fitting, preset loading and blob packing in Python at first. They are not per-sample and are easy to test. Move them to C only when a consumer without Python needs them (the plugin, or 60 fps drag in Play). One loop semantic (decided in P0.4) is used everywhere and recorded in the blob.

## 3. Loop semantics: same-sample vs one-sample (decide in P0.4)

**VERIFIED**

- Without Dffs, both paths are "read → Hadamard → ×g → +xin → write" on the same sample. There is no difference; the delay line provides the loop delay.
- With Dffs (the in-loop Schroeder allpass per line, coefficient `dffs` clamped to ±0.98), the allpass has a delay-free feed-forward term (−dffs·x). Together with H, that makes a **delay-free loop**:
  - Render solves it exactly: y = M(u − D·xin), M = (I + g·diag(dffs)·H)⁻¹.
  - Play breaks it with a one-sample delay: fb = g·H·y[n−1] inside `diffuse()`.

**Analysis (ASSUMED; the Phase 0 worker should confirm or reject it)**

- The loop gain of the broken path is about g·√N·max|dffs| (H is unscaled ±1, so ‖H‖ = √N), which is ≈ 0.88 for typical values. So the z⁻¹ is a *structural* change, not a small HF phase tweak: it changes the modal pattern and the effective decay near Nyquist.
- Shortening each line by one sample cannot compensate, because the z⁻¹ sits in the feed-forward path, not the recirculating one.
- This may be related to the 9/11 kHz residue and the long-tail bug. Flag it to the engine/ worker.
- Historically, Reaktor cannot evaluate delay-free feedback loops. Its docs say that when a feedback connection occurs, "a 1 sample delay has automatically been added" at a point marked "Z", and that the point "could appear at some other input" depending on version [R1][R2].
  - So the 2011 original **did** have a unit delay somewhere in every loop. **Where** it sat in the original structure is UNKNOWN; the Structure screenshots would show the "Z" mark.
  - That makes z⁻¹ the historically faithful choice, provided its position matches.

**Options**

| Option | Cost per sample per tank | Pros | Cons |
|---|---|---|---|
| (a) Exact same-sample solve in C: precompute dense M (N×N) when parameters change, then y = M·v | N² MAC: 1024 at N=32 (~131k per block per tank; ~393k for 3 buses), 4096 at N=64 (4×), 16k at N=128 | matches today's Render; mathematically clean allpass-FDN [S3] | loses the O(N log N) FWHT advantage; much heavier at N=64/128; M must be recomputed on every Dffs change (O(N³) off-thread) |
| (b) z⁻¹ in both Play and Render (as Play does now) | FWHT O(N log N) + N | cheapest, already running live, Reaktor-faithful in kind | Render changes sound slightly; decay-lock maths must include it |
| (c) z⁻¹ placed where the original Reaktor Structure has it | same as (b) | most faithful | needs the Structure evidence |

**Recommendation: (b) now, moving to (c) if the Structure shows a different Z position. Keep (a) as a compile-time option (`RR_LOOP_EXACT`) for a reference build.**

- The blob field `loop_semantics` (see ROADMAP §2) makes the choice explicit.
- Null tests run per semantic.

## 4. Proposed module split (C, ASSUMED design)

```
engine/c/
  rr_api.h        public C ABI: rr_create(sr, max_block, flags) / rr_set_blob(ptr,len) / rr_process(in[],out[],n) / rr_reset / rr_stats / rr_destroy
  rr_blob.c/.h    v2 header + section table parser, validation, CRC (ROADMAP §2)
  fdn_loop.c      Hadamard FDN: fwht (unscaled ±1), per-line Dffs allpass, g, in-loop peaking, humidity 1-pole on inject; N compile-time 32/64/128 or runtime ≤128
  early_taps.c    early lanes, src write-side filters, tint (air 1-pole + ISO shelf), per-hit cascade (read side)
  scatter.c       Track C cluster (read side)
  src_radiation.c source radiation coefficient evaluation (Phase 2 of source brief) + filters
  colour_fir.c    uniform → non-uniform partitioned FIR (mic colour)
  fft.c           radix-2/4 real FFT (current code) — SIMD later
  denormal.c/.h   guard policy (§6)
  simd.h          f32x4/f64x2 shims: wasm_simd128.h, SSE2/AVX, NEON, scalar fallback
  live_stereo.c   → becomes a thin Play wrapper calling rr_* (keeps the exported live_* names the worklet uses)
  fdn_core.c      → deleted after Render parity
```

- **No allocation in `rr_process`** (real-time rule). Use a fixed arena sized at `rr_create`, e.g. by N_max and ring length. Today's WASM already uses static arrays, VERIFIED.
- **Memory layout**: SoA for per-line state (lines × lanes) so FWHT butterflies and biquad banks vectorise.

## 5. What moves from Python to C, and in what order

The order is chosen by (cost in Render) × (parity value) ÷ (risk).

| Step | Move | Why first | Parity gate |
|---|---|---|---|
| C1 | **FDN loop** (`fdn.py` per-sample loop → `fdn_loop.c` via ctypes) | the biggest Render cost (pure-Python per sample); closes the semantics gap once and for all | Render(C) vs Render(Python) with the same semantics: ≤ −100 dBFS (double) |
| C2 | **Early taps + per-hit cascade + air** (scipy `lfilter` per tap → `early_taps.c`) | removes the scipy runtime dependency from the audio path; Play needs the same cascade (ROADMAP P4) | ≤ −100 dBFS vs Python |
| C3 | **Colour FIR** (Render currently uses numpy/scipy convolution; Play already C) → shared `colour_fir.c`, then **non-uniform partitioning** | ~60 % of Play CPU (BRIEF); shared code gives Render/Play bit-parity | uniform vs non-uniform ≤ −120 dBFS; CPU −30 % target (ASSUMED) |
| C4 | **Scatter + source filters** (born in C in P5/P6 Play, Render calls them) | avoids writing them twice | brief nulls |
| C5 | **Coefficient builders**: `coef_for_dir` (source), `scatter_tables`, `surface_filter_stages`, ISO shelf design → C | needed for the plugin (no Python) and 60 fps drag | ≤ −120 dB coefficient diff vs Python reference (float64) |
| C6 | **Image geometry** (`image_geometry.py`, `early_field` image list) → C | only for the plugin; Python stays the reference | same image list (order + delays within 1e-9 s) |

Stays in Python for good: the server, UI endpoints, preset files, fitters, and plotting. The Python reference implementation is kept, not deleted, as the oracle for tests.

## 6. Denormal policy

- **WebAssembly has no flush-to-zero mode.** Its float semantics are IEEE 754 with subnormals honoured, and there is no MXCSR-style control [W1][W2]. The measured silence cost of 3.8 ms/block vs 1.2 ms playing (VERIFIED, BRIEF) is exactly the symptom.
- Policy (ASSUMED, standard practice [E1]):
  1. **WASM (and all builds): explicit guard in the core.**
     - Add a tiny alternating DC/noise offset (±1e-20, sign flips per block) to the FDN inject and to recursive filter inputs.
     - Or clamp states with |s| < 1e-15 to 0 once per block (cheap, SIMD-friendly).
     - Prefer the per-block state flush for bit-exact native-vs-WASM equality: a noise offset is fine as long as it is deterministic and identical on every target.
  2. **Native (Python lib and plugin):** also set FTZ/DAZ (x86 MXCSR bits 15 and 6; ARM FPCR.FZ) at `rr_process` entry and restore on exit.
     - Plugins must restore: hosts share the thread. JUCE's `ScopedNoDenormals` is the familiar pattern.
     - The explicit guard stays, so results don't depend on FTZ. Tests run with FTZ off to prove it.
- CI test `test_silence_cost`: 60 s of silence ≤ 1.5× playing cost (from `c_wasm_performance_roadmap.md`).

## 7. Fixed vs variable N

- VERIFIED: Play N = 32; Render N ∈ {8, 16, 32, 64, 128} (UI buttons 8/16/32/64).
- Recommendation (ASSUMED):
  - Compile specialised kernels for N ∈ {8, 16, 32, 64, 128}. FWHT stages are then unrolled; the dispatch is a switch on N at `rr_set_blob`.
  - Size the rings for N_max = 64 in Play (memory: 64 lines × 4 lanes × ~1 s × 48k × 4 B ≈ 49 MB; note the current max-memory flag is 1 GB, VERIFIED).
  - Gate N = 128 to Render/native only.
  - CPU scales roughly linearly with N for the line work and N log N for the FWHT. At N = 64, 2 sources would exceed the budget (ASSUMED from 1.77 ms at N = 32), so the watchdog must refuse or shed.
- The three buses × 32 lines structure (L, C, R each a full FDN, VERIFIED) is kept. Variable N applies per bus.

## 8. SIMD

- WASM: `-msimd128` is already on the build line (VERIFIED). Use `wasm_simd128.h` intrinsics (f32x4, f64x2) [Z2][W3].
  - The FWHT butterflies on f32x4 or f64x2 are 4× or 2× wide.
  - Biquad banks go SoA across lines, 4 lanes.
  - FFT radix-4.
- Precision: the line state and coefficients are double today (VERIFIED), so f64x2 is only 2 lanes. Test float line state with a null of ≤ −60 dB vs double over a 10 s tail. If it passes, f32x4 doubles the throughput. Keep double for the recursive biquads at low frequencies, where float quantisation raises the noise floor.
- Native: the same code through `simd.h`, targeting SSE2 baseline / AVX2 (runtime dispatch optional) / NEON.
- **Bit-exactness caveat**: bit-exact native vs WASM requires the same operation order and no FMA contraction. Compile with `-ffp-contract=off` on every target, with no `-ffast-math`. Otherwise use a tolerance of ≤ −140 dBFS.

## 9. Builds

| Target | Command / tool | Notes |
|---|---|---|
| Play WASM | `zig cc -target wasm32-freestanding -O3 -msimd128 -nostdlib -ffreestanding -Wl,--no-entry -Wl,--export-memory -Wl,--export=... -o static/wasm/live_stereo.wasm engine/c/*.c` (current line VERIFIED in the `live_stereo.c` header) | Add `-ffp-contract=off`. Pass a compiled `WebAssembly.Module` to the worklet (roadmap doc). Hosting on idlehanz.com: if a SharedArrayBuffer ring (ringbuf.js) is adopted, the page must be cross-origin isolated (COOP/COEP headers) [M1]. |
| Native lib for Render | `zig build-lib -dynamic` or `zig cc -shared -O3 -ffp-contract=off engine/c/*.c -o rr_core.{dll,so,dylib}`; zig cross-compiles all three from one machine [Z1] | Python binds with **ctypes** (stdlib, no build step) [P1]. `numpy.ctypeslib.ndpointer` for arrays. cffi is optional if the API grows [P2]. Ship prebuilt DLLs for Windows (Idle's PC) and fall back to Python when missing (the same pattern as `fdn_core.so` today, VERIFIED). |
| Plugin | CLAP first (MIT, pure C ABI; the C core drops straight in) [C1]. VST3 SDK is MIT since 3.8.0 (VERIFIED on the Steinberg portal) [V1]. AU needs Apple's SDK (terms not checked). JUCE 8 is dual AGPLv3 / commercial EULA [J1]: an open-source AGPL release is fine; closed or commercial needs a paid seat. | Recommendation: **CLAP + VST3 directly, or via a light MIT wrapper**, to avoid JUCE licensing if Idle may sell or keep it closed. Studio One supports VST3, and CLAP in recent versions (ASSUMED; check the current Studio One release notes before committing). |

**Shared-room linking for Studio One track FX (ASSUMED design, to be prototyped)**

- Goal: several track-insert instances (one per source) share one room and one late tail.
- Facts: most hosts load all instances of a plugin into the host process, so they share the DLL's static memory, unless the host sandboxes plugins [K1]. Studio One's sandboxing behaviour must be checked; ASSUMED in-process.
- **Design A (recommended)**:
  - A **Room** instance on an FX channel owns the geometry, the FDN and the mic colour.
  - Each track's **Source** instance renders its direct + early (it has its own position and radiation) and sends its **FDN-inject** signal out of a second output bus. The user routes that bus to the Room channel through the host's normal sends or sidechain. The host routing is sanctioned and gives deterministic timing.
  - Room parameters are shared through an in-process registry keyed by a room ID, carrying geometry and surfaces: a lock-free snapshot exchanged by atomic pointer swap, never on the audio thread's critical path.
- **Design B**: pass audio between instances through in-process ring buffers. It needs no host routing, but host processing order isn't guaranteed, which forces one block of latency and breaks with sandboxing or offline bounce. Avoid it.
- State: each instance saves the room ID and its own blob. The Room instance saves the shared geometry. Blob v2 with CRC protects presets.

## 10. Parameter blob / ABI versioning

- Blob v2 as in ROADMAP §2: magic 2, major, minor, section table, optional CRC32.
- C ABI: `rr_api_version()` returns major·1000 + minor. Python checks it at load and refuses a mismatched DLL, falling back to the Python engine.
- Rules:
  - Adding a section means a minor bump.
  - Changing the meaning or order of fields in a section means that section's version bumps and the parser keeps reading the old version for one release.
  - Removing something means a major bump.
- The Python packer is the single writer and the C parser is the single reader. A golden-blob test file per version is checked in (`tests/golden/blob_v2_default.bin`).

## 11. Verification: bit-exact vs tolerance

| Comparison | Target | Why |
|---|---|---|
| native C vs WASM C, same blob | **bit-exact** (`-ffp-contract=off`, same op order, guard not FTZ-dependent) | same source; catches compiler/flag drift |
| any stage at null settings (omni source, scatter 0, flat cards, air_shelf 0, mute none) vs the stage compiled out | **bit-exact** | BRIEF requirement (omni null, scatter null) |
| Render(C) vs Render(Python reference), same semantics, double | ≤ −100 dBFS peak error over 3 s IR | reference oracle |
| Render vs Play (after P7 both use the C core) | ≤ −100 dBFS; until then ≤ −60 dB (BRIEF parity figure) | the product promise "what you hear is what you render" |
| float-state vs double-state FDN | ≤ −60 dB over 10 s tail; T60 within 2 % | SIMD f32x4 decision |
| decay accuracy | T60 per octave within ±10 % of dialled | P0.2 |

## 12. Testing strategy

1. **Golden IRs**: 6–8 fixed rooms (small, large, two-source, N = 16/64, extreme Dffs, all-mute). Store 48 kHz float IRs plus SHA-256 hashes. The C build must reproduce the hash (bit-exact targets) or pass the tolerance.
2. **Unit tests in C** (zig test or a tiny C harness): FWHT orthogonality (HᵀH = N·I), allpass magnitude = 1, biquad vs Python coefficients, blob parser fuzz (random bytes never crash; bad CRC is rejected).
3. **pytest via ctypes**: extend `tests/test_live_stereo.py` (the existing 10 tests, VERIFIED). Every existing test must pass against the native lib as well as the Python engine.
4. **Stability**: 60 s of white noise at max g / max Dffs gives no NaN/Inf. Keep `scrub()` / `soft_limit()` / `finite_d()` (VERIFIED in the current C). Also check the energy bound with g < 1.
5. **Silence and denormal**: `test_silence_cost` (§6).
6. **CPU regression**: the bench from `engine/bench` (parallel worker) in CI. Fail if > +5 % vs the stored baseline per config (1 source, 2 sources, all features).
7. **Listening A/B**: per roadmap phase. Blind ABX of Play vs Render bounce for P7.

## 13. Suggested PR sequence for P7

1. P7.1 Carve out `rr_api.h` and `rr_blob.c`. `live_stereo.c` calls them. Same wasm output (bit-exact).
2. P7.2 Split `fdn_loop.c` and `early_taps.c` out of `live_stereo.c`, with no behaviour change (bit-exact).
3. P7.3 Native build + ctypes binding + Render uses the C FDN (C1). Delete `fdn_core.c`.
4. P7.4 C2 (early/cascade/air in C for Render).
5. P7.5 C3 non-uniform colour FIR (CPU win; bit-exact vs uniform is impossible, so use tolerance).
6. P7.6 Variable N kernels (8–128) and Play N selectable up to 64.
7. P7.7 SIMD pass with the float-state experiment.
8. P7.8 C5/C6 coefficient builders + geometry in C (plugin prerequisite).

## Sources

- [R1] Native Instruments, *REAKTOR 6 Building in Primary* (PDF): "a 1 sample delay has automatically been added because of it", https://docs.native-instruments.com/pdf-guides/REAKTOR_6_Building_in_Primary_English_0817.pdf
- [R2] Native Instruments, *Reaktor 5.5 Core Reference* (the "Z" feedback mark, "could appear at some other input") and *REAKTOR 6 Building in Core* §4.10 Feedback Connections, https://docs.native-instruments.com/pdf-guides/Reaktor_5_Core_Reference_English.pdf , https://docs.native-instruments.com/pdf-guides/REAKTOR_6_Building_in_Core_English_0618.pdf
- [S1] J.-M. Jot & A. Chaigne, "Digital Delay Networks for Designing Artificial Reverberators," AES 90th Conv., paper 3030, 1991, https://aes.org/publications/elibrary-page/?id=5663
- [S2] J. O. Smith III, *Physical Audio Signal Processing*, "FDN Reverberation" (Hadamard / lossless matrices, damping filters), https://ccrma.stanford.edu/~jos/pasp/FDN_Reverberation.html
- [S3] S. J. Schlecht, "Allpass Feedback Delay Networks," IEEE TSP 69:1028–1038, 2021, doi:10.1109/TSP.2021.3053507 (CC BY), plus fdnToolbox https://github.com/SebastianJiroSchlecht/fdnToolbox
- [S4] D. Rocchesso & J. O. Smith, "Connections between FDNs and Waveguide Networks," ICMC 1994 (lossless ⇔ unit-circle eigenvalues)
- [W1] WebAssembly design issue #148 (subnormals / FTZ), cited in `findings/c_wasm_performance_roadmap.md`
- [W2] WebAssembly spec, numerics: IEEE 754 semantics without a flush-to-zero mode, https://webassembly.github.io/spec/core/exec/numerics.html
- [W3] Emscripten docs, "Using SIMD with WebAssembly," https://emscripten.org/docs/porting/simd.html
- [E1] EarLevel Engineering, "A note about de-normalized numbers," https://www.earlevel.com/main/2019/04/19/floating-point-denormals/
- [Z1] Zig documentation (language reference / `zig cc` cross-compilation), https://ziglang.org/documentation/master/ ; `zig cc` as a drop-in C compiler: https://andrewkelley.me/post/zig-cc-powerful-drop-in-replacement-gcc-clang.html
- [Z2] wasm SIMD128 in clang (`wasm_simd128.h`), https://github.com/llvm/llvm-project/blob/main/clang/lib/Headers/wasm_simd128.h
- [P1] Python docs, `ctypes`, https://docs.python.org/3/library/ctypes.html ; NumPy `numpy.ctypeslib`, https://numpy.org/doc/stable/reference/routines.ctypeslib.html
- [P2] cffi docs, https://cffi.readthedocs.io/
- [C1] CLAP (MIT), https://github.com/free-audio/clap
- [V1] Steinberg VST 3 SDK licensing (MIT since 3.8.0), https://steinbergmedia.github.io/vst3_dev_portal/pages/VST+3+Licensing/Index.html
- [J1] JUCE 8 licence (dual AGPLv3 / JUCE EULA), https://juce.com/legal/juce-8-licence/ and the JUCE forum statement "JUCE 8 is dual-licensed under both the AGPLv3 and the JUCE licence"
- [K1] JUCE forum / KVR on cross-instance communication (instances normally share the host process), https://forum.juce.com/t/two-instances-of-my-plugin-communicating-with-each-other-in-a-daw-project-whats-a-good-approach/62913
- [M1] MDN, SharedArrayBuffer security requirements (cross-origin isolation), https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer
- CHOI2018 (Hongchan Choi, "Audio Worklet: The Future of Web Audio," ICMC 2018), ringbuf.js (Paul Adenot), https://github.com/padenot/ringbuf.js , both as cited in `c_wasm_performance_roadmap.md`
