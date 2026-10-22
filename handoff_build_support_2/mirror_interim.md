# Mirror asymmetry: interim findings (1 Oct 2026, about 10:40 BST)

> **Superseded by `MIRROR_ASYMMETRY_BRIEF.md`, written about 11:30 BST.** One correction since this note: the first line order put the direct image on line 0, which made the FDN bus +6.23 dB hotter (t14 FAIL). Column 0 is the only column of H with a non-zero sum. The final order τ = (b0 b4)(b1 b3) keeps (0,2,0) on line 0: t14 +0.13 dB, PASS, and the mirror is still bit-exact.

**Trees used.** All work is box-only, on Build's tree from the read-only snapshot of **1 Oct 07:36 BST** (`snapshot_2026-10-01_0736`, `work/new1001`). I also ran that tree plus the rebased patches (`work/p6`). I have not re-read the PC since then; any edits Build is making now are not included. PC `software\` was not touched.

**Scene.** Idle's 09:43 hall:
- Room 57 × 34.2 × 97 m, stand at x 28.5 (= W/2).
- A at x 44.09, B at x 12.91 (mirrored).
- Yaw ±55 cardioid, space 0, SM57 sides, C muted, FDN only.
- Decay lock 0.71 s. The lock is ASSUMED on, because with the lock off the server reports 1.37 s.

**Measure.** A's (L, R) output is compared with B's swapped (R, L) output. For a perfect mirror the null is −∞.

## Ranked causes (all VERIFIED by measurement on the box)

### 1. Two-source Play colours source B with source A's colour map (dominant)
- **What happens:** in `live_stereo.c` `mix_partition`, the filter instances come only from `fdnIdx` (A's map), and `yBlk = yA + yB`. As a result:
  - B's FDN goes through A's per-line filters.
  - B's **early** lane also falls back to A's filters: `early_target` only finds filters in A's FDN set, and the `early_b` ids (A's R-side filters) are never in the L-bus set.
- **Size:**

  | Case | Band difference | ILD difference | Overall level | Null |
  |---|---|---|---|---|
  | Balance A vs B (Measured) | up to 13.2 dB (rms 10.5 dB) | 26 dB | 7.9 dB | −1.7 dB |
  | Balance centre (output should be its own mirror) | 4.9 dB | 9.8 dB | – | – |

  - Balance A vs B: the 80 ms energy also differs by ±13 dB.
  - Balance centre: the reverb image is pulled sideways.
- **Isolation:**
  - With colour BYPASS the two-source asymmetry falls to the one-source level.
  - Giving B its own FDN map (JSON substitution, then a C prototype) removes it.
- **Pending patches:** this is the same on p6. No pending patch fixes it.
- **Render:** two-source Render is NOT affected (each source is rendered with its own taps and colour).

### 2. The 32-image table is not left/right symmetric (`LIVE_32`)
- (1,−1,0) has no (−1,−1,0) partner, and (−1,−2,0) appears twice (index 23 and 24).
- The comment in `voice_table_32.py` suggests the original Reaktor fan-out has this gap.
- **Size (one source, or colour bypass):** band up to 1.5 dB (rms 0.5 dB), ILD 1.7 dB, null −20 dB, T30 differences up to about 20 % (T30 is noisy at this sparse 0.71 s decay).
- **Fix tested:** with a symmetric set (index 23 → (−1,−1,0)), the band difference falls to 0.21 dB and the null to −33 dB.

### 3. FDN line order vs Hadamard
- B's lines carry the mirror images in a permuted order, and the Sylvester Hadamard is not invariant under that permutation.
- **Size:** the residual after fix 2 is about 0.1–0.2 dB band difference and a −28 to −33 dB null.
- **Fix tested:** reorder the lines so that mirror pairs sit at (i, τ(i)), with τ = swap(bit0, bit2) ∘ swap(bit1, bit3).
  - This keeps H exactly, keeps i%3 (the peaking axis) and keeps ±1 unscaled.
  - Result: **bit-exact** one-source mirror (null below −2900 dB) in Play and in Render.
  - It works the same with space 0.17.

## Ruled out or minor
- **K1 (crossed yaw):** does not break the mirror. p6 + τ is bit-exact.
- **Peaking:** contributes 0. Depth 0 gives the same numbers.
- **Balance law:** symmetric (linear (1,0) ↔ (0,1), 0.04 dead zone).
- **Mirror:** about the room centre W/2 (correct here, since the stand is at W/2).
- **Delay rounding and the C bus:** no effect.
- **Direct lane:** already symmetric.
- **"Play still uses the old shelf":** a stale static note (`index.html` `micPlayNote`). Play does use Measured SOS colour (Play = Render, null −31 dB). It is not a cause.
- **Harness/API caveat:** if no toe/yaw is sent, the server falls back to the Reaktor diverg law (L 0.25 rad, R 0.75 rad), which is a rotated, non-mirror array. The UI sends ±55, so this is not Idle's issue.
- **WAV input:** two-source mode feeds WAV left → A and right → B. If Idle's WAV channels differ, part of what he hears is the content itself.

## Prototype fix (box only, not on the PC)
1. **Image table (`early_field.py`):** a symmetric, τ-ordered `LIVE_32`. The direct image moves to index 0; `direct_line_index` is dynamic.
   - Selfcheck asserts `LIVE_32[2] == (0,0,0)`, so Reaktor parity should keep the old order.
2. **Colour (`live_bank.py`):** emit `colour.fdn_b` (B's own per-line, per-bus map). The ids are reused from `early_b`, so 0 to a few new IRs.
3. **Route:** `live_fdn.js` / `fdn_worklet.js` route grows 230 → 326.
4. **C:** add `fdnIdxB` and a separate `yBlkB`. B lines and B early go to the `fdnIdxB` filters. `MAX_FILT` goes 112 → 176 (filters about 87 → about 145 with two sources).

**Result on Build tree + τ + B map, and on p6 + τ + B map:** the new `tests/test_mirror_symmetry.py` passes 10/10:
- one source;
- two sources hard A/B, FDN and early lanes, Measured and Bypass;
- balance centre;
- Render.

**Fix 2 alone (B map, without τ):** two-source falls to the one-source level (band 1.5 dB), and the centre ILD falls from 9.8 to 0.26 dB.

**Still to do:** regression runs of the prototype (Build tests, selfcheck, phase suite, CPU with two sources and colour on), the brief, the plan item and the Desktop sync.
