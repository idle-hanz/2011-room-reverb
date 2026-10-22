# GROK BUILD BRIEF — Track C: Surfaces per-reflection scattering

**For:** Grok Build (implementer)
**From:** Idle's research pass, Sat 26 Sep 2026 ~22:00 BST
**Status:** Research + prototype only. Nothing is wired into `software/`. **Implement only when Idle says go.** Tracks A (materials) and B (Solo/Mute) come first.

**Read first:**
- `findings/live_play_fix_audit.md` (what the current engine is)
- `findings/per_reflection_scattering_research.md` (sources)
- `findings/c_wasm_performance_roadmap.md` (CPU)
- `scattering_fitter/REPORT.md`

---

## 1. Goal
Give each early image tap a physically motivated **specular vs scattered** split per material and frequency:
- The specular spike keeps √(∏(1 − s)) of its amplitude per band.
- The scattered share becomes a short, sparse, Lambert-shaped cluster right after the spike. Only the bands that scatter are smeared.

This must be the same in **Render and Play**, and it must be **feed-forward on early taps only**.

## 2. Locks (unchanged; violating any of these fails review)
- **FDN:** unscaled ±1 Hadamard FDN. **Never replace or scale it. No scattering matrices inside the loop.**
- **Early images excite the FDN.** The **FDN inject is unchanged** by Track C (no double count; see §5.4).
- **Levels:** 1/r² geometric level stays; **the serial per-hit filter cascade** in the early field stays (Track C adds one stage to it).
- **Three separate layers** (Track C adds the third; never merge them):
  1. **Surfaces Δd jitter** (`surface_colour.jittered_distance`: Δd = D·λ_ref·sin²θ·u). This is sub-sample path-length jitter per hit: tiny *time* perturbation of the specular spike, no energy moved.
  2. **Structure Dffs**: the in-loop Schroeder allpass per FDN line (`tap_dff` → `dffs`, used in `diffuse()`). It densifies the *late* field **inside** the loop.
  3. **Track C scattering (new)**: moves *energy* from the specular spike into a feed-forward cluster, per band, per hit, **outside** the loop.
  - ⚠ VERIFIED today: the card key `"diffusion"` feeds **both** Δd (D) and `tap_dff` (Σ Dif × Diffusion Master). Track C must **not** reuse `"diffusion"`. Add a new key (§3).
- **Air:** Structure humidity 1-pole stays separate from the ASSUMED high shelf. Direct is air-free. No air on the FDN return. The cluster uses the same tinted early-lane signal as its tap; it adds no air stage.
- **Honesty:** never fabricate MEASURED. Every preset carries its tag (VERIFIED_MEASURED / VERIFIED_CITED_EST / PROXY / ASSUMED) and its source string.

## 3. Data schema
**Material preset** (`scattering_fitter/presets/<id>.json`, schema `scattering_fitter.material_scatter.v1`):
```json
{ "id": "brick_unglazed", "honesty": "VERIFIED_CITED_EST",
  "scatter_hz": [125,250,500,1000,2000,4000,8000],
  "scatter":    [0.02,0.02,0.02,0.05,0.23,0.41,0.44],
  "model": "logistic_log2f", "params": {"s_lo":..,"s_hi":..,"fc":..,"k":..},
  "rmse_s": 0.006, "source": "...GRAS...", "note": "..." }
```
The bands equal `surfaces_fitter.material.v1` `absorb_hz` exactly.

**Surface card** (A–F; extend `parse_surfaces` / `default_surface`):
- `"scatter": [7 floats 0..1]`. **Default all 0.0**, so the feature is inert until a material sets it.
- `"scatter_preset": "<id>"` (optional; for display).
- The material library (Track A) should carry `scatter` next to `absorb` in each of the 12 presets. Copy it from `scattering_fitter/presets/<same id>.json`.

**Global:**
- `"scatter_amount": 0..1` (default 1.0 once enabled; multiplies every s; UI "Scatter" knob in Surfaces).
- `"scatter_pulses": 16` (8 for two sources; see CPU).
- `"scatter_seed"` (reuse `diffusion_seed` convention: SHA-256 key).

**Solo/Mute (Track B) interaction:**
- A **muted face contributes neither absorption nor scattering**. It is dropped from the hit list before both cascades.
- Solo = only the soloed faces' hits are active (same `effective_surfaces` path).
- The prototype verified this: muting face B removes B from every tap's scatter product.

## 4. Algorithm (per early tap i, per bus)
**Inputs:**
- `hits_i` = `surfaces_hit_by_n(n_i)` after Solo/Mute. **The same list the absorb cascade uses.**
- The tap's arrival time `t_i` (ms).

**Steps:**
1. **Specular energy per band:** `S_b = ∏_{h∈hits_i} (1 − scatter_amount·s_{h,b})`.
2. **Specular filter:** fit `g·HighShelf(f0, G)` to `√S_b` over the 7 bands.
   - Grid over f0 (24 log steps, 150 Hz–10 kHz) × G, closed-form trim. Control rate only; runs on param change.
   - The prototype's worst per-tap fit error is 0.3 dB.
3. **Scatter filter:** fit the same shelf form to `√(1 − |H_spec(f_b)|²)`. Using the *realised* spec magnitude keeps |H_spec|² + |H_scat|² ≈ 1 per band.
   - This is the frequency split: where s is small (LF), H_scat is tiny, so only HF is smeared.
4. **Cluster (DERIVED Lambert envelope):**
   - Width `W_i = clamp(0.778·t_i, 1 ms, 30 ms)`: the 90 % energy point of the x^−5 law. It grows with path length and therefore with order.
   - K pulses (default 16), one per equal-energy slot of the CDF `1 − x^−4` on [1, 1 + W_i/t_i], jittered inside the slot. Sign ±1 from the seeded RNG. Amplitude `1/√K`, so the cluster has **unit energy**. Offsets ≥ 1 sample after the spike.
5. **Output of tap i:** `H_spec ∗ tap_i  +  H_scat ∗ Σ_k a_k · tap_i(t − τ_k)`.
   - `tap_i` is exactly today's early read (the tinted early lane at `delay_i`, including Δd jitter in Render). The existing absorb cascade then applies to both terms (in Render the cascade is linear on the whole tap buffer).
6. **scatter_amount = 0 or no hits ⇒ skip steps 2–5: bit-identical to today** (verified in the prototype: null = 0.0).

## 5. Where it slots (against the audited code)

### 5.1 Render (Python)
- `render_pipeline.render_early_ir()` (L363–477).
- After `_apply_ir_at(bl, dl, press_l, …)` / the grad path builds `bl`/`br` for tap t, and **before** `apply_surface_to_buffer`:
  - build the cluster by placing K extra `_apply_ir_at` impulses at `dl + τ_k` with gain `press·a_k` (and the same for grad), into a separate buffer;
  - `lfilter(H_scat)` that buffer and `lfilter(H_spec)` the spike buffer; add them;
  - then continue with peaking, air, surface cascade and colour exactly as today.
- Cluster tables come from a new pure helper `scatter_tables(taps, surfaces, sr, seed, K, amount)` that returns per tap (offsets, amps, spec b/a, scat b/a). **Put it in a new module `engine/scatter.py`, not in `surface_colour.py`.**
- The FDN inject path (`_inject_levels`, `tap_reflect_gain`) is **unchanged**.

### 5.2 Play (C/WASM)
- `live_fdn_params()` packs per line: `scatter_on`, spec biquad (5 coeffs), scat biquad (5), K, offsets[K] (int samples), amps[K]. That is ~40 floats/line × 32 lines × 3 buses (+B). **Bump `BLOB_LEN` and add a blob version field.**
- `live_stereo.c`, early branch of `bus_sample()` (L1008–1013 one source, L1035–1046 two sources):
  - today `ev = read_lane(..., LANE_EARLY, ..., line->delay)`;
  - add `ev = bq(spec, ev) + bq(scat, Σ_k a_k·read_lane(..., line->delay + τ_k))`.
  - For speed, implement it **block-major** (roadmap §2): per line, read 128 fractional samples into a mirrored history ring, K axpys, 2 biquads. Then write `eaBlk/ebBlk` as today.
- The early lane ring (1000 ms cap) already holds everything the cluster needs (τ ≤ 30 ms). **No new ring.**
- `early_target` / colour FIR routing is unchanged: the cluster is part of the early signal for that line, so it gets the same mic colour as its spike.

### 5.3 Parity
- The same `scatter_tables` output (Python) is used by Render directly and packed for Play. **Identical offsets, signs and coefficients.**
- The residual difference is float32 vs float64 plus the known z⁻¹ vs same-sample FDN difference (early only, so it doesn't matter here).

### 5.4 Why the FDN inject is not changed
- The scattered energy of an early reflection is still *early* energy near that tap. The FDN already receives the full tap energy via `inj`.
- Adding scattered energy to the inject would count it twice.
- **Optional v2, OFF by default:** feed the FDN from `√S̄·xin + √(1−S̄)·cluster(xin)`. This is an energy-preserving *replacement*, not an addition, and still feed-forward before the loop. It only makes the FDN input denser. Evaluate by listening.

## 6. CPU budget (box, WASM; see roadmap §2.1)
| Case | today | + Track C | total |
|---|---|---|---|
| 1 source, colour on, K=16 (96 cluster lines) | 1.214 ms | +~0.18 | ~1.40 ms (52 %) |
| 2 sources, colour on, K=8 (192 lines) | 1.770 ms | +~0.35 | ~2.12 ms (79 %) |

- **Precondition:** the denormal guard (audit §3.1). Silent tails currently cost 3.8 ms/block on the box.
- **Skip rule:** if max_b(1 − S_b) < 0.01, keep the spike only (no cluster). Most smooth-wall, low-order taps qualify.

## 7. Acceptance tests (automate in `tests/`)
1. **Null:** `scatter_amount=0` or all `scatter=0` ⇒ early IR / Play output **bit-identical** to the pre-Track-C build (Render and Play).
2. **Energy:**
   - per tap, |H_spec|² + |H_scat|² within ±0.5 dB at all 7 bands;
   - whole early IR octave energy within ±0.5 dB of before at `amount=1` (prototype: −0.32…+0.07 dB for demo_mixed, −0.23…+0.05 dB for qrd_back_wall; broadband −0.38 / −0.21 dB);
   - `amount` sweep 0→1 is monotone and smooth (no step > 0.2 dB between 0.1 steps).
3. **Level / peak:** early peak does not increase (prototype: 0.063 → 0.063). No new clipping at the soft limiter with the user's settings.
4. **Mute/Solo:** a muted face never appears in any tap's scatter product. Soloing one face gives clusters only on taps that hit it.
5. **Feed-forward proof:** the FDN state trajectory is bit-identical with Track C on vs off for the same input (the loop never sees the cluster).
6. **Parity:** Render early IR vs Play early bus (impulse in, colour bypass) ≤ −60 dB error energy over 0–100 ms.
7. **CPU:** Play block cost increase ≤ 0.25 ms (1 source, K=16) on the CI box, plus the silence-tail test from the roadmap.
8. **Determinism:** same params + seed ⇒ identical cluster tables across runs and machines.

## 8. A/B listening checklist (Idle)
Use the same patch, the same seed, and loudness-matched output (it should already match within 0.5 dB).
1. Snare / clicks, brick walls: the "zip" of discrete early echoes should soften at 2–8 kHz. Timing and pitch must not change, and there must be no flam.
2. Plywood / panelling room: HF early field denser, LF unchanged.
3. **Smooth plaster / glass: should sound almost identical** (s ≤ 0.05). If it doesn't, something is wrong.
4. QRD on the back wall: back-wall echoes lose their "slap" across mids and highs, and the stereo image widens slightly.
5. Sustained vocals: no chorus/comb artefacts. If you hear flanging, the cluster offsets are too regular (check the seed/jitter).
6. Scatter knob sweep while playing: no clicks and no level jump.
7. Mute a face: its scattering disappears along with its absorption.
8. Two sources: listen for glitches (CPU). If there are any, drop to K=8.

## 9. What NOT to do
- ❌ Don't put the cluster, allpasses or velvet matrices **inside the FDN loop**, and don't scale or replace the Hadamard.
- ❌ Don't reuse the `"diffusion"` card key or the Δd jitter for scattering, and don't change Structure Dffs.
- ❌ Don't add scattered energy to the FDN inject (double count). The optional v2 is a replacement, and it is off by default.
- ❌ Don't use ISO 17497-2 diffusion coefficients (d) as s.
- ❌ Don't label GRAS or ODEON numbers "MEASURED" (they are estimates by their own authors), and don't promote PROXY/ASSUMED presets (gypsum, carpets, curtain) without a cited table.
- ❌ Don't add air to the cluster or to the FDN return. Don't touch direct.
- ❌ Don't implement per-sample scalar clusters in Play (measured 10× slower than block-major).
- ❌ Don't retune the listened mix to compensate. The energy test must pass instead.

## 10. Files
- `scattering_fitter/`: `run_fit.py`, `scattering_fitter/{sources,model}.py`, `presets/*.json` (12 library materials + 3 diffusers, plus `index.json`), `plots/`, `proto/room_proto.py`, `bench/` (C / WASM / JS kernels + logs), `reports/`, `REPORT.md`.
