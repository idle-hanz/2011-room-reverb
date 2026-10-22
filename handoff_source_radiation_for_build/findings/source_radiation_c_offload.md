# Source radiation: CPU cost and C/WASM offload plan

All timings are **box measurements** (Intel Xeon VM, 8 vCPU, gcc 13 -O3, Node v20.19.2). They are not measured on Idle's PC. The VM is noisy (±30–50 % run-to-run), so treat them as order-of-magnitude figures.
Budget: 128 samples at 48 kHz = **2.67 ms per block**.
WASM was measured with **zig cc -target wasm32-wasi -O3 -msimd128** (zig from the scattering stream's box venv), run in Node 20 WASI. The Play build uses wasm32-freestanding with the same flags. See `bench/bench_wasm_zig_simd128.csv`. There is no emcc on the box.
Sources: `bench/src_bench.c`, `bench/src_bench.mjs`, CSVs in `bench/`.

## 1. Kernel
Per (image, capsule-bus) line: `v = g·x → RBJ high-shelf (TDF-II) → two cascaded one-poles → mix`. That is 5 mul-adds for the biquad plus ~6 for the poles/mix, about 13 flops per sample. There is **no alloc in process()**; coefficients live in SoA arrays.

## 2. Measured cost per 128-sample block (3 buses, lines = 3 × N images)

| N images (lines) | C lines-inner (scalar) | C SIMD-8 lanes | C lines-outer | Node JS | % budget (C SIMD / JS) |
|---|---|---|---|---|---|
| 32 (96) | 29 µs | 19–21 µs | 52 µs | 50 µs | 0.8 % / 1.9 % |
| 64 (192) | 57 µs | 37–42 µs | 105 µs | 108 µs | 1.5 % / 4.0 % |
| 128 (384) | 114–133 µs | 72–84 µs | 209 µs | 280 µs | 3.0 % / 10.5 % |

**WASM (zig -O3 -msimd128, Node 20, box):**

| N images (lines) | lines-inner | SIMD-8 lanes | lines-outer | coefficient recompute (all lines) | ×4 multi-point |
|---|---|---|---|---|---|
| 32 (96) | 39 µs | **19.5 µs** | 66 µs | 10 µs | 261 µs |
| 64 (192) | 77 µs | **36 µs** | 131 µs | 18 µs | 558 µs |
| 128 (384) | 177 µs | **72 µs** | 265 µs | 38 µs | 1325 µs |

So WASM is ≈ native for the SIMD layout and ~1.3–1.5× for the scalar layout, consistent with the scattering stream's 1.2–1.4×.

Related costs:

| Item | C | Node JS | Note |
|---|---|---|---|
| Per-sample coefficient ramp (block-rate interpolation while dragging) | ~2× static (56–111 / 111–227 / 222–463 µs) | not measured | Only while a parameter moves. |
| Coefficient recompute, all 3N lines (pow/exp/cos) | 6 / 12 / 25 µs | 31 / 59 / 114 µs | Once per block at most, on drag. |
| Multi-point ×4 (4 × lines) | 115 / 231 / 464 µs | 197 / 384 / 771 µs | Linear in M. |
| Diffuse (FDN-inject) filter | 1 biquad per source per bus ≈ <1 µs | <1 µs | Negligible. |
| Direct-path filter | 1 per bus | — | Negligible. |

Reading the numbers:
- The "lines-outer" loop is latency-bound, because the biquad recurrence is serial.
- Interleaving 8 lines in SIMD lanes (sample loop outer, 8 lanes inner) is about 2.5× faster. That is the layout to use in C/WASM.

## 3. What this means for Play (live_stereo.c: N = 32 lines per bus)

> **Superseded by §7** (the shared per-image filter and the combined budget with scattering). The per-bus estimate below is kept for reference.
Currently, one-source mode feeds **one** shared `tint(line, x*inj, 0)` into both the early lane and the FDN input (`bus_sample`, VERIFIED).

With radiation active:
- the early lane needs `src_i(x)` → tint;
- the FDN needs `diffuse(x)` → tint.

That adds 96 source filters plus a second tint (1 one-pole + 1 biquad) on 96 lines. Two-source mode already runs separate tints (kinds 1/2 early, 0/3 FDN), so there it adds only the source filters (192).

**Estimated extra per block in Play:**

| Mode | C native (box) | WASM (ASSUMED factor) | % budget |
|---|---|---|---|
| One source | ~40–60 µs | ~50–120 µs | 2–4.5 % |
| Two sources | ~60–100 µs | ~70–200 µs | up to ~7.5 % |

If Play is later raised to 64/128 images, scale with the table above.

**Omni fast path (null):** if the source preset is omni, keep today's shared-tint code path. That gives zero cost and bit-identical output.

## 4. Parameter updates on drag

**Phase 1 (lowest risk, matches today's architecture): compute in Python.**
- A source drag already goes UI → `POST /api/live_params` → `render_pipeline.live_fdn_params` → blob → `live_load_room` (VERIFIED: app.js `pushLiveParams`; the per-line air shelf is already shipped as biquad coefficients via `load_shelf`).
- Add the per-line source coefficients (9 floats × 32 shared image lines, plus 3 direct and 1 diffuse filter per source; see §7) plus the per-bus direct and diffuse coefficients to the blob, computed by the **same Python function** Render uses (`engine/source_radiation.py`). This gives parity by construction.
- The drag rate is limited by the server round trip (as source position already is), and the C side ramps coefficients over one block to avoid zipper noise.

**Phase 2 (smooth 60 fps drag, no server hop): move the coefficient maths into the C core.**
- **Compute coefficients where they are used, in the C core.**
  - The worklet sends only `{yaw, pitch, roll, size, preset params}` (about 20 floats per source) through the existing params message.
  - The C core computes each line's emission direction (from the image indices n and positions it already has) and the coefficients. This costs about 6 µs per block in C for 96 lines, so it can run at block rate while dragging.
  - Moving it to the main thread would need 3N × 8 floats per update over postMessage plus JS recompute (30–60 µs). Both are fine, but keeping it in C makes **Render and Play identical**, which is the main reason.
- **Smoothing:**
  - Target coefficients are recomputed at most once per block, and yaw/pitch are smoothed with a one-pole of τ ≈ 20 ms (ASSUMED) on the angles before recompute.
  - Within the block, coefficients are ramped linearly per sample (cost ~2× the static kernel, and only while moving). Alternatively, crossfade two filter states over one block. The ramp is simpler and stable for these shelf/one-pole coefficient sets, because they have no resonance.
  - Existing `SMOOTH = 0.0025` per-sample delay smoothing stays for delays, including size-jitter delay changes.
- **Stop condition:** when |target − current| < 1e-6 on all coefficients, snap to the target and clear the `moving` flag, which skips the ramp cost.

## 5. Shared C core recommendation (align with the scattering stream's roadmap)
One C file (e.g. `engine/src_radiation.c` + `.h`), included by both `live_stereo.c` (WASM, Play) and `fdn_core.c`/a new `render_core` (ctypes, Render):
1. `src_coef(const SrcPreset*, const float dir_local[3], float fs, float size_scale, SrcCoef*)`: the model maths, identical to `source_fitter/model.py` and `prototype/radiation.py:coef_for_dir`.
2. `src_emit_dir(n[3], img_pos[3], rx[3], out[3])` plus `facing_basis(yaw, pitch, roll)`: geometry.
3. `src_bank_process(SrcBank*, const float *in, float *out, int nlines, int nsamp)`: SIMD-8/4 lanes, ramped variant, no alloc, and a denormal flush. Either set FTZ/DAZ (`_mm_setcsr` on x86 native; WASM has no denormal penalty in most engines but is still explicit), or add a 1e-20 DC offset in the one-pole states.
4. `src_diffuse_process` (one biquad per source per bus).
5. **Watchdog:**
   - If a coefficient is non-finite (`finite_d` already exists in live_stereo.c), reset that line's state and set bypass.
   - Clamp `fc ≤ 0.45 fs`, and keep shelf S ≤ 1 so there is no overshoot.
6. **Parity test:** a Python test compiles the same C via ctypes and compares it with `prototype/radiation.py` on 1000 random directions (max |Δ| < 1e-6 relative).

**Alignment:** see §7. Everything goes into the same `live_stereo.c` core the scattering stream plans to split into kernels. It is **not** a second C core.

## 6. Render (offline)
- The Python `render_early_ir` already loops over taps. Adding `src_process_fast` (scipy lfilter, 2–3 calls per tap) costs about the same as the existing peaking/air stages. That is roughly 20–40 ms per render for 32 taps × 3 buses on 1.6 s buffers (box, the prototype renders a full 6×3×8 IR set in about 17 s including the pure-Python FDN stand-in).
- For parity and speed, move to the shared C bank via ctypes in phase 2.


## 7. Alignment with the scattering stream (read 26 Sep ~22:00: `handoff_surfaces_for_build/findings/live_play_fix_audit.md`, `c_wasm_performance_roadmap.md`, `briefs/GROK_BUILD_BRIEF_Surfaces_scattering.md`)

### 7.1 Facts taken from those documents (VERIFIED by that stream, box)
- Play = `engine/live_stereo.c` → `static/wasm/live_stereo.wasm` (zig, -msimd128). `fdn_worklet.js` is a thin shim.
- N is fixed at 32 per bus. The colour FIR (partitioned FFT) is ~60 % of the cost.
- Cost today, per 128-sample block (WASM, box):

  | Case | Cost | % of budget |
  |---|---|---|
  | 1 source, colour on | 1.214 ms | 45.5 % |
  | 2 sources, colour on | 1.770 ms | 66.4 % |
  | + scattering, 1 source (K=16) | ~1.40 ms | ~52 % |
  | + scattering, 2 sources (K=8) | ~2.12 ms | ~79 % |

- **Denormals:** in silence the core rises to 3.8 ms/block (WASM has no FTZ/DAZ). A guard is the #1 prerequisite.
- The Play early tap has **no per-hit surface cascade** (only a broadband √(1−ᾱ) folded into `inj`).
- Scattering adds its filters on the **read side** of the early lane (`ev = bq(spec, ev) + bq(scat, Σ a_k·read)`). It is block-major.
- The blob gets a version field and a larger `BLOB_LEN`.

### 7.2 How source radiation fits the same core (design)
- **Order of the serial cascade in Play:**
  1. the source stage on the early-lane **write** side (per image, before the ring);
  2. then the existing tint (air 1-pole + shelf);
  3. then, on the **read** side, the scattering spec/scat biquads, and in future the per-hit surface cascade slot;
  4. then the colour FIR.

  This is source → surfaces/scatter → mic, as locked. The scattering cluster reads the already source-filtered early lane, so every scattered pulse carries the emission colour of its specular path. That is an approximation (ASSUMED; scattered energy physically leaves in the same emission direction as its specular ray to first order).
- **Share one source filter per image across the 3 buses (recommended default):**
  - Line i is the same image n on every bus. The emission direction differs between capsules by at most **2.0°** in the 6×3×8 m test (box, space 0.3 m).
  - So compute `srcBlk[i][t] = src_i(x)` **once per image per source**, block-major in a pre-pass at the top of `run_partition` (SIMD over lines). `bus_sample` then writes `tint(srcBlk[i][t]·inj, kind)`.
  - This gives 32 filters per source instead of 96.
  - The direction used is the one to the mic centre. Render must use the **same** tables (the centre-capsule direction for images) for parity.
  - The **direct path** keeps per-capsule directions: 1 filter per bus, block-major on x.
- **Diffuse (FDN inject) filter:** once per source per block (block-major on x), not per bus.
- **One-source mode:** with radiation on, the FDN input needs `tint(xd·inj, 0)` and the early lane needs `tint(src_i(x)·inj, 1)`. That is an extra tint per line (the same state layout two-source mode already uses). With radiation off (omni), keep the current shared-tint path, which is a bit-exact null.
- **Blob:** one version bump shared with scattering (v2).
  - Append a `src` section after the scattering section, with a flag per source.
  - It holds 32 × 9 floats per source for the image filters, 3 × 9 for direct and 6 for diffuse: ≈ 330 floats per source (instead of ~1.8 k with per-bus filters).
  - Coordinate `BLOB_LEN` with the scattering build.
- **Denormal guard:** apply the roadmap §3 remedy (alternating ±1e-20 offset per block, or a state clamp) to all source filter states (biquad z1/z2, one-pole p1/p2), the same as the other IIRs. Include the source path in the silence CI test.
- **Kernel file:** when `live_stereo.c` is split (roadmap §5.2), put the source bank in `early_taps.c` next to the per-hit cascade. It is the first stage of the same per-line chain: `line_chain_process` with stages [source, (tint), spec/scat, surface cascade].

### 7.3 Combined Play budget (WASM, box; per 128-sample block; budget 2.667 ms)
Source-radiation increments (from §2 WASM, scaled by filter count):

| Item | Cost |
|---|---|
| Image filters, shared, 32/source | ~7–13 µs |
| Image filters, per bus, 96/source | ~20–39 µs |
| Extra tint split (one source only), 96 lines | ~20–40 µs (ASSUMED ≈ the source kernel) |
| Direct (3) + diffuse (1) per source | ~1–2 µs |
| Coefficient ramp while dragging | ×2 on the image-filter part |
| C-side coefficient recompute (phase 2), 32 lines | ~3–4 µs per block while dragging |

| Case | today | + scattering (stream's numbers) | + source radiation (shared) | total | % |
|---|---|---|---|---|---|
| 1 source, colour on, K=16 | 1.214 | +0.18 | +0.03–0.06 | **~1.43–1.46 ms** | **54–55 %** |
| 1 source, colour bypass, K=16 | 0.482 | +0.18 | +0.03–0.06 | ~0.70 ms | ~26 % |
| 2 sources, colour on, K=8 | 1.770 | +0.35 | +0.02–0.03 | **~2.14–2.15 ms** | **80–81 %** |
| 2 sources, same, per-bus source filters | 1.770 | +0.35 | +0.04–0.08 | ~2.16–2.20 ms | 81–83 % |
| 2 sources, same, while dragging | 1.770 | +0.35 | +0.05 | ~2.17 ms | ~81 % |
| Silence without denormal guard | 3.8 | — | — | 3.8+ ms | >140 % |

**Two sources sit at about 80 %, right on the limit.** Trims, in order of recommendation (keeping the total ≤ ~80 % with margin):
1. **Scattering on L/R buses only when two sources are active** (roadmap option; the centre early lane is already uncoloured): about −0.12 ms, giving **~2.03 ms (76 %)**.
2. **Source filters shared per image** (above): saves 0.03–0.05 ms vs per bus. It is already in the default.
3. **Scattering skip rule** (smooth-wall taps with max(1−S) < 0.01 keep the spike only): saving depends on the room; likely −0.05…−0.15 ms.
4. **Source bypass rule:** lines whose source filter is within ±0.1 dB of identity over 50 Hz–16 kHz (near-axis images, or omni-ish LF-only presets) skip the filter. Saves up to 30 % of the source cost for many presets. Cheap.
5. **Colour FIR non-uniform partitioning** (roadmap §5.2): the biggest lever (~60 % of total), but more work. Do this before raising N or adding multi-point emission.
6. **Not in Play with two sources:** multi-point emission (×M cost) and `tail_follow` (per-line inject) stay Render-only, or one-source-only, until the FIR is optimised.

**Recommended two-source configuration:** shared source filters + scattering K=8 on L/R only + denormal guard, giving **~2.03–2.08 ms (76–78 %)** including drag ramps.

**Watchdog:** use the roadmap's CPU-time watchdog. If overrun is detected, drop in this order: scattering (to spike-only), source filters (to omni, i.e. the null path), then early.
