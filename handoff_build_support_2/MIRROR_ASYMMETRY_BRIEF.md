# MIRROR ASYMMETRY BRIEF: Two sources + Mirror sound different left vs right (1 Oct 2026)

- **Who/when:** box agent, 1 Oct 2026, 09:50–11:00 BST.
- **Tags:** VERIFIED = measured on the box by a script or test; ASSUMED = judgement or an unconfirmed input.
- **Trees:**
  - Build's tree from the read-only PC snapshot of **1 Oct 07:36 BST** (`snapshot_2026-10-01_0736`, box `work/new1001`).
  - The same tree + the rebased patches (`work/p6`, item 1 of the plan).
  - Build has been editing `software\` since this morning. **None of those edits are included.** Re-run the test in §5 on Build's current tree.
  - PC `software\` was only read, never written.
- **Files:**
  - Scripts and raw results: `7_mirror_symmetry/` (`scripts/`, `results/`).
  - Prototype diffs: `7_mirror_symmetry/prototype/`.
  - Acceptance test: `3_phase_acceptance_tests/tests/test_mirror_symmetry.py`.
  - Interim note: `mirror_interim.md`.

## TL;DR

- **The audible cause is a Play two-source bug (VERIFIED).** Source B's reverb and early lanes are filtered with **A's** per-line mic-colour filters, so B sounds as if it came from A's side.
  - Balance A vs B: up to **13 dB** per band, **26 dB** ILD difference, 8 dB level.
  - Balance centre: the image leans sideways by **9.8 dB ILD**.
  - It is not fixed by any pending patch (the same on the rebased p6). Render is fine.
- **The smaller, one-source cause:** the Reaktor 32-image table has a missing mirror partner, and the FDN line order is not mirror-compatible with the Hadamard. Together: **1.5 dB**, null −20 dB.
- **Fix:**
  - (A) a B-side colour map `fdn_b` (0 extra IRs for mirrored sources);
  - (B) a symmetric image table in a Hadamard-automorphic line order that keeps (0,2,0) on line 0.
- **Prototype (box):** bit-exact mirror in every case, all regressions unchanged, two-source CPU +7–15 %.
- **Acceptance:** `tests/test_mirror_symmetry.py`, A vs mirrored B within **0.1 dB per 1/3-octave band**.

## 1. Idle's report and the test scene

**Report:** with Two sources + Mirror on, moving Balance from A to B sounds different on each side. It is much less noticeable when one source is moved around.

**Scene (from his 09:43 screenshots):**

| Setting | Value |
|---|---|
| Hall | 57 × 34.2 × 97 m |
| Stand | (28.50, 24.25), h 1.90, so on the room centre line |
| Source A | (44.09, 34.89), h 1.88 |
| Source B (mirror) | (12.91, 34.89), h 1.88 |
| Capsules | space 0; cardioid yaw ±55 (ASSUMED, from "Custom" plus the page default) |
| Mics | SM57 sides; C muted |
| Colour | Measured |
| Hadamard | 32 |
| Decay | lock 0.71 s (ASSUMED: with the lock off the server reports 1.37 s for this room, not 0.71) |
| Air | humidity 0.5, 1-pole 0.25, shelf 1 |
| Faders | FDN only (Direct/Early/Host at −inf) |

The lock-off case gives the same ranking (see §2).

**Measure:** A's output (L, R) against B's output swapped (R, L). For a true mirror this is identical. Metrics, from 100 Hz to 16 kHz:
- 1/3-octave band level difference;
- 80 ms early energy;
- T30 per octave;
- ILD and band coherence per 1/3 octave;
- the null.

## 2. Ranked causes (all VERIFIED; numbers are Play unless marked)

| # | Cause | Where | Size in Idle's scene | Fixed by a pending patch? |
|---|---|---|---|---|
| **1** | **Two-source Play colours source B with source A's colour map.** The filter instances on each bus are created only from `fdnIdx` (A's per-line map), and `yBlk = yA + yB` goes through them. B's **early** lane also falls back to A's filters: `early_target()` only accepts filters already in A's FDN set, and B's `early_b` ids are A's opposite-side filters, so they are never in that set. B's reverb is therefore coloured as if it came from A's side | `live_stereo.c` `bus_sample` / `mix_partition` / `early_target`; `live_bank.py` (no `fdn_b`) | Balance A vs B: band diff **up to 13.2 dB (rms 10.5)**, **ILD diff 26 dB**, level 7.9 dB, ±13 dB in the first 80 ms, null −1.7 dB. **Balance centre** (output should be its own mirror): band 4.9 dB, **ILD 9.8 dB**, so the reverb image leans sideways. The same happens with the lock off (12.6 dB band, 25 dB ILD) and on p6 (13.6 dB band, 26.9 dB ILD) | **No.** Same on p6. Render is **not** affected: two-source Render renders each source with its own taps and colour (VERIFIED, 2-source Render null equals the 1-source numbers) |
| **2** | **The 32-image table is not X-symmetric.** (1,−1,0) at index 18 has no (−1,−1,0) partner; (−1,−2,0) appears twice (index 23 and 24). The two same-row duplicates (0,1,1) and (0,0,1) are self-mirror and harmless. `voice_table_32.py` records this as the original Reaktor fan-out (ids 47/49) | `engine/early_field.py` `LIVE_32` | One source (or colour Bypass): band **up to 1.5 dB (rms 0.5)** near 100 Hz, ILD 1.7 dB, null −20 dB, T30 up to about 20 % (T30 is noisy in this sparse 0.71 s FDN). With the symmetric set (index 23 → (−1,−1,0)): 0.21 dB, null −33 dB | No |
| **3** | **FDN line order vs Hadamard.** B's line i carries the mirror of A's line i image. As a whole network, B's FDN is A's FDN with the lines permuted by σ (nx → −nx), and the unscaled ±1 Sylvester Hadamard is not invariant under that σ | `LIVE_32` order + `fwht` | Residual after fixing cause 2: band 0.1–0.2 dB, null −28 to −33 dB, T30 up to about 9 % | No |
| – | **K1 (crossed yaw)** | R04 | **0.** p6 + fix 3 is bit-exact | – |
| – | **Peaking axis `i % 3`** | `read_peaked` | **0** in this room (depth 0 gives the same numbers). It would matter if lines moved between axis classes, which the fix below avoids | – |
| – | **Play "old shelf" vs Measured** | `index.html:142` `micPlayNote` | The text "Play still uses the old shelf" is **stale static text** (never toggled). Play uses the Measured SOS bank: Play vs Render, one source, null −31 dB, band ≤ 0.04 dB. **Not a cause.** Remove or fix the note | – |
| – | Balance law, mirror flag, delay rounding, C bus | `source_balance_gains`, `mirror_source_b`, `room_math.js:60–67`, `app.js:1785` | **0.** Balance is linear and symmetric ((1,0) ↔ (0,1), 0.04 dead zone). Mirror uses W − sx on the server and in the UI (about the room centre, which equals the stand X here). The direct lane is already exact | – |

### Other things to know (not causes in Idle's scene)

1. **Two-source input is per channel.** WAV left drives A and WAV right drives B (`run_partition`). If Idle's file has different L and R content, part of what he hears is the material itself. Check by ear with a dual-mono WAV.
2. **The mirror is about the room centre W/2, not the stand X.** With an off-centre stand there is no exact mirror anyway, because the walls are not symmetric about the stand. That is design, not a bug. Possibly show a hint in the UI.
3. **Diverg fallback (API and harness only).** If no `toe_half_deg` or yaw is sent, the server uses the Reaktor Diverg law (L 0.25 rad, R 0.75 rad). That is a rotated array and by design not mirror-symmetric (it gave 8.8 dB here). The page always sends ±yaw, so this does not apply to Idle. Tests must send yaw.
4. **Other Hadamard sizes (Render only).** One-source Render asymmetry is 0.33 dB at N = 16 (order effect) and 0.01 dB at N = 64.
   - The 8/16/64/128 tables are mirror-symmetric multisets, but their order does not commute with H.
   - Low priority; Play is 32-only.

## 3. Fix (prototype VERIFIED on the box; keeps the locks)

The locks kept are: unscaled ±1 Hadamard, early images excite the FDN, per-line colour, and per-line delays from image distances.

### Fix A: B gets its own FDN colour map (cause 1, the audible one)
- **`mic_colour/live_bank.py`:** emit `colour.fdn_b = {l,c,r: [ix.idx(θ_B(i, bus), bus)]}` from `taps_b`, next to `early_b`.
  - For L/R these are the ids `early_b` already uses, so the bank grows by **0 IRs**.
  - For C it also grows by 0 when B is a mirror. A **non-mirrored** B adds about 30 C-bus entries (cap test 150 → 180), which item 2's cap must cover. Alternatively, skip the C map when the C gain is 0.
- **Route (`live_fdn.js` `buildRoute`, `fdn_worklet.js`):** ROUTE_LEN 230 → **326**. Append 3 × 32 `fdn_b` ids after `direct_b`, falling back to `fdn`.
  - **Bump WORKLET_VER** (35 after R09's 34): an old cached worklet would copy only 230 ints.
- **`live_stereo.c`:**
  - Add `fdnIdxB[3][N]` and load it in `live_load_route`.
  - Keep `yBlk` as A only and add `yBlkB` for B.
  - In `mix_partition`, after the A loop, run the B lines through `fdnIdxB` (take/share filters through the same `map[]`).
  - Use `early_target(st->fdnIdxB[b], …)` for B early.
  - The colour-off path sums `yBlk + yBlkB`.
  - `MAX_FILT` 112 → **176**. With two sources, about 58 + 58 + 29 FDN filters plus 6 direct = about 151. The FDL memory grows 7.3 → 11.5 MB.
- **CPU:** two-source colour runs about 1.7× as many filter instances. See §6 for the measured cost; re-run t15 with colour actually on.

### Fix B: mirror-symmetric, Hadamard-compatible image order (causes 2 and 3; makes one source exact too)
1. **Symmetric set:** index 23 (−1,−2,0) → **(−1,−1,0)**. That gives 30 unique images; only the 2 self-mirror duplicates remain.
2. **Order the 32 lines so that mirror partners sit at (i, τ(i))**, where τ is a bit-swap involution of the 5-bit line index.
   - **Why a bit swap:** a bit permutation leaves the Sylvester H unchanged (P H Pᵀ = H, exactly, still unscaled ±1).
   - **Which bits:** swapping bits of the same weight mod 3 keeps the peaking axis `i % 3`. The usable swaps are (b1 b3) plus one of (b0 b2), (b0 b4) or (b2 b4).
   - **Slots:** each such τ has 8 fixed indices, which hold the 8 self-mirror singletons. Its 12 pairs hold the 10 true ± pairs and the 2 duplicate pairs (swapping identical images is a no-op).
   - **Choice:** `7_mirror_symmetry/scripts/tau_search.py` picks the τ and assignment that keep the most images at their Reaktor index. **τ = (b0 b4)(b1 b3)** keeps 15 of 32, including **index 0 = (0,2,0)**.
   - **The order** (`scripts/tau2.json`):
     `(0,2,0) (-1,1,0) (0,0,1) (1,-2,0) (0,-2,0) (1,2,0) (-1,0,1) (1,-1,1) (0,0,1) (-1,-1,0) (0,0,0) (1,1,1) (1,0,1) (1,0,0) (0,-1,0) (0,1,1) (1,1,0) (0,1,0) (1,-1,0) (1,2,1) (-1,2,0) (0,2,1) (-1,0,0) (1,-2,1) (-1,-2,0) (-1,2,1) (-1,1,1) (0,1,2) (-1,-1,1) (-1,-2,1) (0,1,1) (0,0,2)`.
   - **The direct image moves from index 2 to index 10.** No τ of this kind can fix index 2. `direct_line_index()` is dynamic, but the selfcheck asserts `LIVE_32[2] == (0,0,0)` and the 29-unique count.
   - ⚠ **Line 0 is special (VERIFIED):** the bus sums all lines, and column 0 is the only column of H with a non-zero sum (+32). So whatever image sits on line 0 recirculates coherently into the output.
     - My first ordering put the direct on line 0. It made the FDN bus **+6.23 dB** hotter (t14 FAIL).
     - The final ordering keeps (0,2,0) on line 0: t14 +0.13 dB vs p6's +0.08 dB, PASS.
     - **Any reorder must keep a weak image on line 0.** The t14 level test guards this.
3. **Proposal:** keep the Reaktor table as `LIVE_32_REAKTOR` for `reaktor_parity` (bit-exact with the 2011 patch, including its gap), and make the τ-ordered symmetric table the default for every other mode.
   - Update the two selfcheck asserts.
   - Regenerate goldens (plan item 4).
4. **Other N (Render only):** apply the same rule (find a bit permutation that pairs mirrors and keeps i%3; search script TODO). Low priority.

**Simpler alternative for two sources only:** reorder `taps_b` by σ so that B's line i is the mirror of A's line i. This would make two-source A/B exact (with Fix A) but leave the one-source asymmetry (cause 2: 1.5 dB) and would need B-side bookkeeping everywhere. **Not recommended**; Fix B is cleaner and fixes both.

**Prototype diffs:**
- `7_mirror_symmetry/prototype/MIRROR_on_p6.diff`: against the tree + rebased patches. It applies cleanly with `patch -p1` (dry run VERIFIED).
- `MIRROR_on_build_1001.diff`: against Build's 07:36 tree.

Both are 238 lines (τ = (b0 b4)(b1 b3) ordering) and touch `early_field.py`, `live_stereo.c`, `live_bank.py`, `live_fdn.js` and `fdn_worklet.js`. **Verified:** `patch -p1` on a clean copy reproduces the prototype trees exactly (wasm excluded; rebuild it). The prototype replaces `LIVE_32` outright and does **not** bump WORKLET_VER or keep a parity table. Build should add both.

## 4. Result of the prototype (VERIFIED)

| Tree | One source (Play) | Two sources A vs B, FDN + Measured | Two sources A vs B, early + Measured | Balance centre (L vs R) | Render one source |
|---|---|---|---|---|---|
| Build 07:36 | 1.52 dB / null −19.8 | **13.2 dB, ILD 26.2** | 13.2 dB, ILD 26.3 | **4.9 dB, ILD 9.8** | 1.54 dB / −19.8 |
| + Fix A only | 1.52 dB | 1.52 dB, ILD 1.66 | 1.39 dB | 0.13 dB, ILD 0.26 | 1.54 dB |
| + Fix B only (either τ) | **exact** (−2993 dB) | 12.9 dB, ILD 25.4 | 12.9 dB | 4.8 dB, ILD 9.6 | exact (−229 dB) |
| **+ A + B** (Build 07:36 and p6) | **exact** | **exact** | **exact** | **exact** | **exact** |

"Exact" means a null below −200 dB and every metric 0.00.

- `test_mirror_symmetry.py`: **10/10 PASS** on Build 07:36 + A + B and on p6 + A + B, with the final τ = (b0 b4)(b1 b3) order. The first τ = (b0 b2)(b1 b3) also passed 10/10, but failed t14 (above). On the unfixed trees it reports 2 pass + 8 xfail.
- Regressions: see §6.

## 5. Acceptance test (for Build)

`3_phase_acceptance_tests/tests/test_mirror_symmetry.py`. Run it with `python -m pytest tests/test_mirror_symmetry.py --sw <software> [--slow]`.

**Scene:** Idle's hall above, with yaw ±55 sent explicitly. A at x 44.09; B at W − 44.09 (two-source Mirror, balance −1 / +1; and one source moved to B).

**Criteria.** Compare A (L, R) with B (R, L), 100 Hz–16 kHz:

| Metric | Limit |
|---|---|
| Null | ≤ −60 dB |
| Any 1/3-octave band | ≤ **0.1 dB** |
| ILD difference per band | ≤ 0.1 dB |
| Band coherence difference | ≤ 0.01 |
| 80 ms early energy | ≤ 0.1 dB |
| T30 per octave | ≤ 2 % |

**Cases:**
- one source;
- two sources hard A/B for the FDN-only and early-only lanes, Measured and Bypass;
- balance centre (the output must equal its own L/R swap);
- Render one source (`--slow`).

The prototype reaches exactly 0, so these limits are float-noise margins.

**Mapping to a one-line "A vs mirrored B within X dB per band" criterion:** X = 0.1 dB. Today's values are 13.2 dB (two sources) and 1.5 dB (one source).

**XFAIL until landed.** The probe is: `LIVE_32` is a mirror-symmetric multiset **and** `fdn_b` appears in `mic_colour/live_bank.py` or `render_pipeline.py`. If Build names it differently, update `_landed()`.

**Harness change (backward compatible):** `harness/lib/wasm_run.js` `buildRoute` now emits 326 ints (`fdn_b`, falling back to `fdn`). Worklets with ROUTE_LEN 230 copy only the first 230, so old trees give identical results (VERIFIED: the base tree numbers are unchanged).

## 6. Regression and CPU on the prototype (p6 + A + B, final τ; VERIFIED)

| Check | p6 (rebased patches) | p6 + A + B |
|---|---|---|
| Build's `test_live_stereo.py` + colour tests | 28/28 | **28/28** |
| `engine/selfcheck.py` | 44/44 | **42/44** (see below) |
| Phase suite `--slow` (now includes the 10 mirror tests) | 60/2/22/0 before the mirror tests | **70 pass / 2 fail / 22 xfail** |
| run_all `--quick` | 8 pass, 0 fail | **8 pass, 0 fail**, t14 FDN +0.13 dB |
| CPU, Idle's hall, colour **on** (90 IRs), node bench, mean ms per 128-sample block (budget 2.667) | one source 0.55; two sources 0.96 | one source 0.58; two sources **1.03–1.16 (+7–15 %)** |

**Notes on the table:**
- **Selfcheck:** the 2 FAILs are the expected Reaktor-table asserts: `test_32_indices_exact_set` (29 unique, direct at index 2) and `test_mix_buses_independent` (`assert LIVE_32[2] == (0,0,0)`). Keep them for the parity table and add mirror asserts for the default table.
- **Phase suite:** the same 2 FAILs as p6, both pre-existing and both already in the plan:
  1. Two-source colour cap. Now **180** > 128 (p6: 146): the cap test uses a **non-mirrored** B (sx_b 1.5, sz_b 5.5), whose C-bus `fdn_b` thetas are new. For **mirrored** scenes `fdn_b` adds **0** entries (Idle's hall 90 → 90; std K3 default 150 → 150). The symmetric set alone adds 4 (146 → 150).
  2. The small-room 500 Hz / 1 kHz T30 tolerance (0.732 s vs 0.8 ± 8 %).
- **Cap and CPU:** item 2's cap decision must now cover up to about 180. `MAX_IRS` 192 does; the C-bus B map can also be skipped when the C gain is 0. The prototype raises only `MAX_FILT`.
- **What the CPU bench covers:** today's t15 `2src_col` number runs with colour **off**, because its scene is over the cap. The bench above is the colour-on number.
