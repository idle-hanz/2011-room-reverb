# Paste-ready fix-up prompt for Build (same window)

---
Shared-tail P5 fix-up. Change only the shared-loop sign vector. Leave everything else alone.

Background (box research is in `handoff_build_support_2\research_shared_fdn\p5_fix\REPORT.md`):
- P5's excess LF/mid coherence comes from L and R reading one modal set. CSIGN_D makes it worse in the shared loop: its cross-line terms add coherence.
- Swapping in a fully new d fixes P5 but breaks P6 (LF thirds move 5–8 dB), because the off networks use CSIGN_D.
- Any shared-loop d must be invariant under the line mirror π = index-bit swap (b0 b4)(b1 b3). Otherwise P7 drops to about −12 dB.
- The minimal mirror-safe change is CSIGN_D with entries 3 and 24 flipped from −1 to +1 ({3, 24} is one π orbit).

Do this in `software/engine/live_stereo.c`:
1. Next to CSIGN_D, add:
   ```c
   /* Shared loop only. CSIGN_D with the mirror orbit {3,24} flipped. Invariant under
      pi = (b0 b4)(b1 b3), so the mirror stays exact; not a Walsh row (max|Hd|/32 = 0.375).
      Lowers shared-tail L/R LF coherence and keeps the LF spectrum of the H.D loop (P6). */
   static const double CSIGN_DS[32] = {
       1.0, -1.0, -1.0,  1.0, -1.0, -1.0,  1.0, -1.0,
      -1.0,  1.0, -1.0,  1.0,  1.0,  1.0,  1.0,  1.0,
      -1.0,  1.0,  1.0,  1.0, -1.0,  1.0,  1.0,  1.0,
       1.0,  1.0,  1.0,  1.0, -1.0,  1.0,  1.0,  1.0
   };
   static const double *g_csignTab = CSIGN_D;
   ```
   In `fwht32`, use `g_csignTab[k]` instead of `CSIGN_D[k]`. Keep the `if (g_csign)` guard as it is.
2. In `run_partition`, inside `if (st->shared) { ... }`, wrap only the call `bus_sample(st, BUS_C, x, xA, xB, split, t, hn, doFwht, doDiff);`:
   - set `g_csignTab = CSIGN_DS;` just before it;
   - set `g_csignTab = CSIGN_D;` just after it.
   
   This covers the C loop's FWHT and its diffuser (`diffuse32` also calls `fwht32`), for bank A and bank B. Don't change jitter (300 µs, seed 1), the taps, shG, or the L and R `bus_sample` calls. fwht8/fwht16 are untouched.
3. Add a test, e.g. in `tests/test_shared_tail.py`. Parse CSIGN_DS from the C source and assert:
   - d[pi(k)] == d[k] for all k;
   - d[0] == +1;
   - max|H·d|/32 < 1;
   - exactly two entries differ from CSIGN_D (3 and 24).
4. Rebuild the wasm and re-pack the usual way. Then run:
   - the full shared-tail suite P1–P10;
   - `test_s4b_tail_solo_runaway.py` (comb);
   - `test_fdn_passivity.py`;
   - the parity, binaural and selfcheck tests.
   
   Off, binaural and parity must stay bit-exact against the current wasm (P1 / P8 max|diff| = 0).
   Optional cross-check: with shared on, your IRs should equal those from `research_shared_fdn\p5_fix\c\ref\F12_csign_ds_j300.wasm` (box prototype, same source plus this change) bit-for-bit, or at least to ≤ −120 dB.

Expected results (box, this snapshot):
- P5 rms/max:
  - default .057/.100
  - big .039/.075
  - small .085/.120
  - mid .088/.125
  - ortf_wide .135/.221 (passes its own limit, see below)
- P6 worst level 0.56 dB, worst third-octave 3.22 dB.
- P4 worst 3.9 %. P7 −600 dB. P9 ok.
- Comb on 2.02/3.16 dB, ac19.36 .141/.158 (gate 0.20).
- CPU unchanged within noise.

Do not tune anything to make ortf_wide pass. No jitter, seed, weight or extra flip changes: the box screen of 222 variants shows those passes are seed-lottery and fail held-out scenes.
- **Idle's decision D2 (locked 2026-10-02):** give ortf_wide its own P5 limit of rms ≤ 0.15 / max ≤ 0.25 in the P5 check (`test_shared_tail.py` and the phase P5 runner, wherever the 0.09/0.15 limit lives). Every other scene keeps 0.09/0.15 unchanged. Add a short code comment: "one shared network can't decorrelate a wide spacing as much as separate networks; scene limit accepted by Idle, D2". Don't loosen any other gate.
- Note it in HANDOVER.md: shared-tail column-sign tweak (entries 3 and 24 set to +1, shared loop only) and the ortf_wide P5 limit of 0.15/0.25, with the measured .135/.221.
- Report every number above next to the box values. If any number differs by more than 0.005, stop and report it; don't adjust.
---

## If Idle picks D3 (R750s7, not recommended) instead, add on top of the above
- Jitter: `js = 450.0e-6 * sr` in `shared_prepare`. In `shared_jit`, change the seed term `0x9e3779b9U * 1u` to `0x9e3779b9U * 7u`.
- Per-mic line weight, computed in `shared_prepare` for each bus b in {L, R, C} and each line i:
  - `w = 0.25 + 0.75 * m->inj / c->injS` (when `c->injS != 0`, else 1);
  - `wB = 0.25 + 0.75 * m->injB / c->injSB` likewise.
  
  Store them as new Line fields and multiply them into the shared tap gains:
  - `yBlk[bb][i][t] = w * shG * ring…`
  - `yBlkB … = wB * shGB * …`
  
  Don't renormalise shG or shGB.
- Expected:
  - P5: default .044/.092, big .055/.081, small .043/.087, mid .065/.118, wide .078/.123.
  - P6: level ≤ 0.87 dB, raw ≤ 3.14 dB.
  - Comb ac19 .123/.130.
  - IR target `c\ref\R750s7_alt.wasm`.
- Known: shared-tail level is about +0.9 dB higher than off. Held-out scenes big_off (P5 max .188) and ortf_narrow (P6 4.37 dB) fail.
