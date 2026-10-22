# S5 (SURF v1, D-UI26 = A): CPU decision for Idle

3 Oct 2026, 16:50 BST. Box work by build_support_2. Idle's PC was read only. Nothing in `software\` was touched and the app was not restarted.
Every number is tagged. **VERIFIED** means measured or read on the box this afternoon. **ASSUMED** means an estimate, or Build's figure that I did not re-measure.
Probe files are in `roadmap/s5_surf_1010/verify_1600/`.

## LOCKED: Idle "yes to all" (3 Oct 2026, 16:55 BST)

| ID | Decision | Status |
|---|---|---|
| D-S5c-1 | Bit-exact SoA cascade layout (two lines per f64x2), in all three staging paths, keeping the per-sample flush | **LOCKED** |
| D-S5c-2 | t19 shared-off re-based to a same-session paired A/B median on the PC: a80209 against the new wasm, 12 alternating rounds, with a **2.40 ms hard ceiling**. Shared-on keeps the **2.133 ms** absolute gate. `BUDGET_MS` is unchanged. | **LOCKED** |
| D-S5c-3 | Render's FDN inject uses Play's fitted surface filters (the same coefficients as the Play blob), so t18 returns to about −72 dB. The Render tail moves ≤0.05 dB; Build reports the actual delta. | **LOCKED** |
| D-S5c-4 | The early-parity gate (≤0.3 dB) is narrowed to two sets: the **tail** (80 ms+) of default, face-A HS+6 and all-faces HS+6, and the **full-mix 0–80 ms** of default (shaped − flat) and face-A HS+6. The all-faces HS+6 full-mix early figure, and the early-bus-only rows, are **reported, not gated**. | **LOCKED** |
| Goldens | Regenerate from the shipped wasm. GOLDEN_META's sha fields must name the files that produced the bytes, and its reason string names D-S5c-1…4. | **LOCKED** |
| Not taken | (c) K≤2 on the diffuse lane, (d) K_max, line skipping, the shared diffuse cascade, scatter (S5 item 2), smear (item 3) | not in this fix-up |

Box preview of the narrowed D-S5c-4 gates, on the default client body with the current 9b7cdf (`verify_1600/parity_cases.json`, VERIFIED):

| Case | Window | Value | Result |
|---|---|---|---|
| Tail 80 ms+, default | tail | 0.020 dB | pass |
| Tail 80 ms+, face-A HS+6 | tail | 0.008 dB | pass |
| Tail 80 ms+, all faces | tail | 0.035 dB | pass |
| Default, full mix | 0–80 ms | 0.080 dB | pass |
| Face-A HS+6, full mix | 0–80 ms | 0.104 dB | pass |
| All faces, full mix | 0–80 ms | 0.795 dB | reported only |
| Default, early bus only | 0–80 ms | 0.112 dB | reported only |
| Face-A HS+6, early bus only | 0–80 ms | **0.38 dB** | reported only |
| All faces, early bus only | 0–80 ms | 0.419 dB | reported only |

The face-A early-bus-only row would fail a 0.3 gate, which is why the gate is on the full mix, as in Build's metric. Build's own scene values may differ (ASSUMED).

## 0. Short version

- **S5 is sound-correct.**
  - Hashes match. Flat cards and `reaktor_parity` are bit-exact against a80209.
  - The default tail moved by the expected amount, within 0.03 dB.
- **The PC CPU rise is S5's own cost, not drift.**
  - On the box, the shipped cascade costs **+11.8 %** against a80209 (VERIFIED, paired, 12 rounds). That is about twice the +5–6 % my morning prototype measured.
  - +11.8 % on top of the pre-S5 PC numbers predicts 2.34–2.42 ms. The PC measured 2.30–2.32 ms. (ASSUMED transfer from box to PC.)
- **No option that keeps the sound clears 2.133 ms on the PC with shared tail off.**
  - Removing every cascade section on the box still leaves −7.6 %, so the PC would be about 2.13 ms (ASSUMED). The PC was already 2.09–2.16 ms before S5.
- **Recommendation:**
  1. A bit-exact layout fix-up (SoA), worth −3.2 % on the box (VERIFIED).
  2. Re-base t19 to a same-session paired A/B on the PC.
  3. Keep the 2.133 ms absolute gate on shared-on.
  4. Do **not** trade sound for 2–4 % with K≤2 or a shared diffuse cascade: neither clears the gate.
  5. t18 and the all-faces early parity each need a small decision of their own (§4).

## 1. Verification on the box (i)

| Check | Result | Tag |
|---|---|---|
| wasm sha1 | 9b7cdf2490be0bdc40c7b3543df6fb6993ed2a49 | VERIFIED |
| `engine/live_stereo.c` sha1 | 6bf150623fb2d3d9c8d9523fe4dac90d6af9728b | VERIFIED |
| WORKLET_VER | 46 (`live_fdn.js:19`) | VERIFIED |
| GOLDEN_META.json | Its sha fields name 9b7cdf / 6bf150. Per HANDOVER, the 4 Play goldens and `render_std_unlocked_byp` were written at 15:10 from wasm 8bed0080de08, and the sha fields were edited afterwards. So META does not record which wasm produced the audio. | VERIFIED (file); producer per HANDOVER, ASSUMED |
| t03 on Build's goldens | max-abs 0 on all 4 (`last_results.json`, 15:28, 9b7cdf). Not re-run on the box. | ASSUMED (Build's run) |
| Flat cards, new vs old (1600 tree + 9b7cdf vs 1010 tree + a80209), absorb = card mean, EQ 0 | Play mix/fdn/early max-abs **0**. Render mix/fdn/early max-abs **0**. | VERIFIED |
| `reaktor_parity` = on, new vs old | Play mix/fdn max-abs **0**. Render mix/fdn max-abs **0**. | VERIFIED |
| Render early bus, new vs old (default and all-faces HS+6) | max-abs **0**. S5 did not change Render early; it was already face-coloured. | VERIFIED |
| Default third-octave tail delta (FDN bus, 80 ms+, new − old) | Play and Render match each other within **0.022 dB** max. Render is within **0.032 dB** of this morning's prototype-A expectation, Play within **0.025 dB** (row below). | VERIFIED |
| All-faces HS+6 tail, Play vs Render | Within **0.051 dB** max | VERIFIED |
| t18 on the box | **−42.9 / −42.5 dB** (Build: −42.8 / −42.4) | VERIFIED |
| t19 scene Play, new vs old | null −28.7 dB (the colour change is expected) | VERIFIED |

Default tail delta (dB, FDN bus, 80 ms+, new − old; VERIFIED). Columns are 125 Hz to 16 kHz in third octaves:

```
Hz       125   160   200   250   315   400   500   630   800   1k    1k25  1k6   2k    2k5   3k15  4k    5k    6k3   8k    10k   12k5  16k
expect  +.39  +.11  +.53  -.00  +.44  +.22  +.19  +.00  +.22  +.05  +.12  +.01  +.02  -.07  -.18  -.21  -.27  -.33  -.37  -.28  -.14  -.07
Render  +.386 +.100 +.533 -.007 +.437 +.220 +.222 +.005 +.214 +.047 +.106 +.010 +.013 -.064 -.181 -.210 -.268 -.328 -.369 -.282 -.142 -.074
Play    +.366 +.122 +.537 -.002 +.439 +.211 +.215 +.003 +.218 +.046 +.098 +.011 +.017 -.062 -.178 -.208 -.285 -.343 -.352 -.277 -.160 -.080
```

## 2. Why the PC is at about 2.30 ms (ii)

**Box paired CPU A/B.** t19 scene, shared tail off, per-block medians. Files: `verify_1600/bench_ab_*.json`.

| Comparison | Median ms | Paired median | Tag |
|---|---|---|---|
| a80209 (1010 tree) vs 9b7cdf (1600 tree), 12 rounds | 1.871 → 2.103 | **+11.8 %** | VERIFIED |
| 9b7cdf with the cascade blob removed (S5 code, no cascade) | 1.901 | +1.8 % vs a80209 | VERIFIED |
| Same pair rebuilt on the box from each tree's C, 4 runs of 8 rounds | | +11.6 to +14.0 % | VERIFIED |
| Shared tail on, 6 rounds: a80209 vs 9b7cdf | 1.463 → 1.698 | +14.6 % | VERIFIED |

**Where the cost sits.** Box-built variants of the shipped C, paired against the box-built shipped C (8 rounds each, VERIFIED):

| Variant | Paired median | Note |
|---|---|---|
| Diffuse lane K≤2 (truncation, CPU only) | −2.2 % | |
| Both lanes K≤2 | −3.5 % | |
| Diffuse lane off | −4.3 % | |
| Both lanes K = 0, per-line loop still running | −7.6 % | |
| Pre-S5 (A_reb) | −10.4 to −12.3 % | |
| No per-sample denormal flush | −0.7 % | Not bit-exact, max-abs 4.5e-13 |
| Scalar instead of f64x2 | −0.3 % | |
| Scalar and no flush | −2.3 % | |
| K = 4 unrolled | +0.3 % | |
| K = 4 unrolled with K_MAX 4 | −1.6 % | |
| **SoA lines-across f64x2 (prototype, split radiation path)** | **−3.2 %** | Bit-exact on t19, max-abs 0 |

So the S5 cost splits roughly into three parts (box, ASSUMED split from the rows above):
- about 2 % for non-cascade S5 code;
- about 3 % for the per-line loop overhead, which stays even with zero sections;
- about 7–8 % for the sections themselves (4 per lane × 2 lanes × 2 banks).

My morning prototype (+5–6 %) used a compile-time K = 4 with no flush. It was not the shipped code.

**PC.**
- Pre-S5 PC t19 medians were 2.089 / 2.116 / 2.131 (S7 quiet runs, 2 Oct 20:28–20:42 BST). The shared-tail-build means were 2.09–2.16 (ASSUMED, Build's numbers in HANDOVER).
- × 1.118 gives **2.34–2.42 ms** predicted. The PC measured **2.30–2.32 ms** (ASSUMED, Build's runs).
- The measured value is at or below the prediction. So S5's own cost accounts for the whole rise, and no extra drift is needed to explain it (ASSUMED: the box ratio carries over to the PC).
- Build did not run a same-session paired PC A/B, so this is not proven on the PC.
- The gate was already marginal before S5: 2.09–2.16 against 2.133. Even a zero-cost S5 would go red on some PC runs.

**To pass 2.133 from 2.31 the PC needs about −7.7 %** (ASSUMED arithmetic). The best box case that keeps the cascade sound (SoA, −3.2 %) gives about 2.24 ms (ASSUMED).

## 3. Options (iii)

**How the sound costs were measured.** In the box Render model (1600 tree, `verify_1600/render_ir_opt.py`): the FDN-bus tail, 80 ms+, third-octave, max |Δ| from 125 Hz to 16 kHz, against the exact face chain. Four cards: default / all-faces HS+6 / carpet floor / user extreme. VERIFIED in the model. Play is ASSUMED to track Render as the shipped fit does (Play−Render tail ≤0.022 dB, VERIFIED).
- The shipped fit itself costs **0.018 / 0.050 / 0.021 / 0.043 dB** on the tail (VERIFIED).

**How the PC estimates were made.** ≈ 2.31 × (1 + box %) (ASSUMED).

| Option | Sound change | CPU (box, paired) | PC est. | Clears 2.133? |
|---|---|---|---|---|
| **(c) K≤2 on the diffuse lane** | Radiation scenes only: the diffuse lane is not used when the source is omni, so 0 dB on the default omni card (VERIFIED in code: `live_stereo.c` ~2452–2493). Radiation-scene tail: **0.136 / 0.186 / 0.416 / 1.70 dB**. Per-line inject error up to 1.57 / 1.86 / 4.11 / 10.6 dB (VERIFIED, model). | −2.2 % (VERIFIED) | ~2.26 (ASSUMED) | No |
| **(d) K_max = 2, both lanes** | Tail as (c), on every scene. Play early colour per image line up to **1.57 dB** default, 4.11 carpet, 10.6 extreme (VERIFIED, model; fit_k.json says 1.571 / 4.108 / 13.1 at K = 2). | −3.5 % (VERIFIED) | ~2.23 (ASSUMED) | No |
| (d′) K_max = 3 | Tail **0.136 / 0.188 / 0.241 / 0.63 dB**. Per-line up to 1.58 / 1.87 / 4.15 / 10.6 dB with the shipped one-start K3 fitter (VERIFIED, model). fit_k.json says 1.081 at K = 3 with more starts (VERIFIED, file). | Not measured. Between K2 and K4, about −1.7 % (ASSUMED) | ~2.27 (ASSUMED) | No |
| Skip lines whose shape is within tolerance | 0 dB | **0 %** on the default cards: every shaped line is K = 4 and nothing is skipped (Build's fallback (a) result, ASSUMED; my default fit has 31 of 32 lines shaped, VERIFIED) | 2.31 | No |
| Once-per-block | Coefficients are already static per block. The filter must run per sample, or the sound changes. The only per-block piece is the denormal flush: max-abs 4.5e-13 (VERIFIED) | −0.7 % (VERIFIED) | ~2.29 (ASSUMED) | No |
| Shared-bus position: one K = 4 cascade per source on the diffuse inject | Radiation scenes only. Tail **0.27 / 1.52 / 0.96 / 1.13 dB** (VERIFIED, model, inject-energy-weighted mean) | About the diffuse-lane-off figure, −4.3 % (ASSUMED, from VERIFIED −4.3 %) | ~2.21 (ASSUMED) | No |
| **SoA cascade layout (new; lines across f64x2)** | **0 dB, bit-exact** (VERIFIED on the t19 IR) | **−3.2 %** (VERIFIED, prototype covers only the two-source radiation path) | ~2.24 (ASSUMED) | No, but free |
| **Re-base t19 to a same-session paired A/B median** | 0 dB | Unchanged. It makes S5's cost explicit: +11.8 % on the box (VERIFIED) | n/a | Changes the gate |
| **Gate on shared-on only** | 0 dB at the default, because shared tail stays off by default (`app_server.py:86`, VERIFIED). The budget is only guaranteed when "Shared tail (lighter CPU)" is ticked, which moves T60 by up to +0.38 s at 250 Hz (def_2) and +0.33 s at 1 kHz (big_2) (VERIFIED from `shared_tail_proof.json` P4). | PC shared-on 1.84 ms (ASSUMED, Build) | 1.84 | Yes |

Cut S5 or other combinations:
- Removing all sections and leaving the loop gives −7.6 % (VERIFIED), PC about 2.13 ms (ASSUMED). That is borderline, and it removes D-UI26's sound.
- SoA + per-block flush + diffuse K≤2 might reach about −6 % (ASSUMED, not measured together), PC about 2.17 ms. That still does not clear the gate and it costs radiation-scene tail colour.

## 4. Do t18 and the early parity need their own decisions?

**t18 (−42.8 dB): yes, a small one.** The cause is proven on the box:
- Render with Play's fitted cascade nulls Play at **−71.8 / −71.8 dB** (VERIFIED; S7 was −71.9).
- Render exact vs Render-with-fit is −42.9 / −42.5 dB (VERIFIED).
- So the networks are still identical. The whole residual is the fitted vs exact face chain.

Choices:
- **(t18-a)** Render uses the same fitted coefficients on its inject. t18 returns to about −72 dB, and the Render tail moves by ≤0.018 / 0.050 / 0.021 / 0.043 dB (VERIFIED, model).
- **(t18-b)** Keep Render exact and re-scope the −60 target to "Render with Play's fit". The −30 gate is already met.

I recommend (t18-a): one source of truth, and the change is under 0.05 dB.

**All-faces HS+6 early parity (0.957 against the 0.3 gate): yes, re-scope it.**
- The cause is structural. Render early is the full geometric image set; Play early is 32 FDN-timed taps. The cascade is not at fault.
- Build's per-line error is ≤0.166 dB and the tail of the same case is 0.080 (ASSUMED, Build).
- My box cross-check on the default client body, "HS+6 move" Play minus Render: full mix **0.574 dB** at 10 kHz, early bus 0.435, tail 0.035 (VERIFIED, `parity_hs6_all.json`). It is a different scene from Build's, so the numbers differ, but the story is the same.
- Recommendation: gate per-line fit ≤0.25 dB and tail move ≤0.1 dB, and record the full-mix early gap as a known Play-early limit. Closing it would need more Play early taps, which is a CPU decision of its own.

## 5. Recommendation (adopted in full: LOCKED table above)

1. **Fix-up 1 (no sound change):**
   - Port the SoA lines-across cascade to all three staging paths: two-source radiation, one-source radiation, and no radiation.
   - Keep the per-sample flush, so the result stays bit-exact.
   - Expected about −3 % (VERIFIED on the box for the t19 path).
2. **Measure before deciding further.** Build runs a same-session paired PC A/B: a80209 vs the fix-up wasm, t19 shared off and on, 12 alternating rounds, median. This confirms the +12 % on the PC.
3. **Gate:**
   - Re-base t19 shared-off to the paired method. Report the delta vs a80209 and the absolute median, with a hard ceiling. I suggest 0.9 × 2.667 = 2.40 ms (ASSUMED proposal; Idle to choose).
   - Keep 2.133 ms absolute on shared-on, which passes at 1.84 (ASSUMED, Build).
   - Remember that scatter and smear (S5 items 2–3) are not started and also need budget.
4. **Do not take (c), (d) or the shared diffuse cascade now.** They save 2–4 %, do not clear the gate, and cost up to 0.4 dB (carpet) or 1.7 dB (extreme) of radiation-scene tail colour, or up to 1.6–10 dB of per-image early colour.
5. **t18:** (t18-a). **Parity:** re-scope as in §4.
6. **Goldens:** regenerate from the shipped wasm and record the true producing hash in GOLDEN_META.json.

## 6. Fix-up prompt for the S5 Build window (paste-ready, high effort; LOCKED 16:55 BST; not started)

**Short pointer for Idle to paste:**

```
S5 fix-up (same window, high effort). Idle locked D-S5c-1…4 ("yes to all", 3 Oct 16:55 BST). Open
handoff_build_support_2\roadmap\s5_surf_1010\S5_CPU_DECISION.md and do §6 "Full fix-up prompt" exactly:
the four decisions plus the goldens, all gates in §6, then stop. No scatter, no smear, no other changes.
```

### Full fix-up prompt

You are in the S5 Build window. Effort: high. Idle locked D-S5c-1…4 (the LOCKED table at the top of this file). Do these, in order, and nothing else.

Box references, read only, in `handoff_build_support_2\roadmap\s5_surf_1010\verify_1600\`:
- `wasm\live_stereo_var3.c` (`-DSURF_SOA`): the SoA prototype, split radiation path only.
- `bench_ab.py`, `bench_blocks_1600.js`: the paired bench. Each variant has its own tree; `msgFrom` forwards `surf_cascade` and `shared_tail`.
- `pre_s5_a80209\static\{js\fdn_worklet.js, wasm\live_stereo.wasm}`: the pre-S5 pair (sha1 e7b9b53eb8c6 / a80209d2e69c).
  - The t19 params differ only by `surf_cascade` and `surf_fit`, which the old worklet ignores.
- `render_ir_opt.py` (`OPT=fit`), `t18_probe.json`: the t18 proof.
- `parity_cases.json`: the box preview of the D-S5c-4 gates.

**1. D-S5c-1: SoA cascade (bit-exact).**
- Lay the SURF cascades out lines-across: coefficients and states as `[lane][section][coef][line]`, two lines per f64x2, sections in the outer loop.
- Do this in all three staging paths: two-source radiation, one-source radiation, and no radiation.
- Pad lines shorter than the per-lane K max with identity sections (b0 = 1, the rest 0).
- Keep the per-sample `ls_flush`. Keep a scalar fallback.
- Keep state across a coefficient update, as now.
- **Gate:** max-abs **0** against 9b7cdf, 1.0 s, on each of:
  - t19 two-source;
  - one-source talking_head;
  - shaped omni default;
  - flat cards;
  - `reaktor_parity`;
  - shared tail on.

**2. D-S5c-3: Render uses Play's fitted surface filters.**
- In `render_pipeline._scale_inject_reflect`, replace the exact `_surf_rel_stages` chain with the `fit_line_cascade` coefficients that `_play_surf_cascade` packs for Play.
- Use the same fit, the same K, and the same f32 rounding.
- Render early is not changed.
- **Gates:**
  - t18 ≤ **−60 dB**. The box prototype gives −71.8 / −71.8.
  - Flat cards and `reaktor_parity` Render: max-abs 0 against now.
  - Render early: max-abs 0 against now.
  - Render tail: report the actual third-octave delta against now (FDN bus, 80 ms+, 125 Hz–16 kHz) on default, all-faces HS+6, carpet floor and user extreme. The box model gives 0.018 / 0.050 / 0.021 / 0.043 dB. **Stop and report** if any band moves more than **0.10 dB** on the default or all-faces case.

**3. D-S5c-4: narrowed parity gate.** The test is |ΔPlay − ΔRender| ≤ **0.3 dB**, third-octave 125 Hz–16 kHz, L/R mean.
- **Gated:**
  - tail 80 ms+ on default (shaped − flat), face-A HS+6 and all-faces HS+6 (each case − default);
  - full-mix 0–80 ms on default (shaped − flat) and face-A HS+6.
- **Reported, not gated:**
  - all-faces HS+6 full-mix 0–80 ms;
  - every early-bus-only row.
- Update the harness and pytest names to match. Do not loosen any other gate.

**4. D-S5c-2: t19 re-based.**
- t19 shared off is a same-session paired A/B on this PC: the pre-S5 pair (a80209 with its own worklet) against the new wasm with the current tree.
  - t19 scene, 12 alternating rounds in ABBA order, `bench 4 10`, per-block medians.
  - **Gate:** the median of the new wasm's per-round medians ≤ **2.40 ms**.
  - Report the paired median % and every round. The box expectation is about +8–9 % (ASSUMED: +11.8 % ship minus 3.2 % SoA).
- t19 shared on is an absolute gate: median ≤ **2.133 ms**. Build's last figure was 1.84.
- Keep `BUDGET_MS`.
- Silence-late stays within its current 1.3× rule.
- Close other apps, and do not run S-UI work during the bench.

**5. Goldens.**
- Only after gates 1–4 pass, regenerate the Play and Render goldens from the **shipped** wasm and tree.
- GOLDEN_META.json:
  - sha fields name the exact wasm, C, worklet, `render_pipeline` and `fdn` that produced the bytes;
  - `when` is the regeneration time;
  - reason string: `S5 fix-up D-S5c-1 SoA bit-exact, D-S5c-2 t19 paired A/B 2.40 ms ceiling, D-S5c-3 Render uses Play's fitted surface filters, D-S5c-4 parity gate narrowed (Idle 3 Oct 16:55 BST)`.
- Report the max-abs of each golden against the 15:10 files. Play should be 0, because SoA is bit-exact. Render moves with D-S5c-3.

**6. Ship.**
- Bump `WORKLET_VER` to 47.
- Report the new wasm sha1 and C sha1.
- Add a HANDOVER section with every number from gates 1–5, tagged VERIFIED (measured here) or ASSUMED.
- Run the full harness, pytest and selfcheck, and report the counts.

**Stop rule:**
- Do only items 1–6.
- Do **not** start scatter (S5 item 2) or smear (item 3).
- Do not apply (c), (d), line skipping or a shared cascade.
- Do not change `g`, the per-line loss, the shared-tail logic, the desk, or any UI.
- If a gate fails, stop at that item, keep the tree at the last passing state, and report. Do not loosen a gate.
- A bare "continue" does not start anything new.

## 7. Files (box: `roadmap/s5_surf_1010/verify_1600/`)

- **Tree comparison:** `gen_irs.py`, `compare.py`, `compare_1600.json` (old vs new IRs), `parity_hs6_all.json`.
- **Benches:** `bench_blocks_1600.js` (forwards `surf_cascade` and `shared_tail`), `bench_ab.py`, `bench_ab_1615_off.json` (12 rounds, shipped), `bench_ab_1619/1632/1641/1647_off.json` (variants, 8 rounds), `bench_ab_1620_on.json` (shared on, 6 rounds).
- **Sound of the options:** `render_ir_opt.py`, `options_sound.py`, `options_sound_*.json`.
- **t18:** `t18_probe.py`, `t18_probe.json`.
- **Pre-S5 bench pair:** `pre_s5_a80209/static/js/fdn_worklet.js` and `pre_s5_a80209/static/wasm/live_stereo.wasm`, for Build's paired A/B.
- **Parity preview:** `parity_cases.py`, `parity_cases.json`.
- **Variant sources:** `wasm/live_stereo_kcap.c`, `wasm/live_stereo_var.c`, `wasm/live_stereo_var2.c`, `wasm/live_stereo_var3.c`. These are box research copies, not shipped.
