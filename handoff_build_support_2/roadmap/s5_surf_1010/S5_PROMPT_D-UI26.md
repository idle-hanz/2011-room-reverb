# S5 prompt (D-UI26 = A, locked by Idle 3 Oct 09:22 BST). Written 3 Oct 10:10–11:08 BST on the box from `snapshot_2026-10-03_1010` (wasm sha1 a80209d2e69c)

This file replaces item 1 and the CPU/goldens paragraphs of the S5 prompt in `BIG_JOBS_ROADMAP_2026-10-01.md` §5. Items 2 (scatter, Render half) and 3 (Smear) are unchanged, and the roadmap §5 S5 block now points here. Evidence is in this folder. Unmarked numbers are VERIFIED box measurements; everything else is marked ASSUMED.

---

> Hi Build. Plan: `2011 Room Reverb\handoff_build_support_2\BIG_JOBS_ROADMAP_2026-10-01.md`, session S5, with the details in `handoff_build_support_2\roadmap\s5_surf_1010\S5_PROMPT_D-UI26.md`. Idle locked **D-UI26 = A** (3 Oct 09:22). The face colour (absorption shape + face EQ) must reach the **tail in both engines** and the **Play early field**, through a per-line feed-forward filter outside the loop. Read the roadmap §0.0 and §5 first. Then:
>
> **0. Parked CPU patch first (no sound change).**
> - Apply `roadmap\s5_surf_1010\f2\F2_cold_shared_fields_rebased_1010.patch` to `engine\live_stereo.c`. It rebases the 19:05 F1 + F2 patch (hoist `shC`; move the shared-tail doubles out of the hot `Line` struct) onto the current tree with the `g_csignTab` / CSIGN_DS fix.
> - Rebuild the wasm. Output must be bit-exact: the box shows max-abs 0.0 against the shipped a80209d2e69c on t19, default, parity, binaural and Hall, shared tail off and on (`f2\exact_1010.json`). Re-prove it on the PC with run_all t19 + the goldens.
> - The box CPU effect is neutral: −0.8 % on the paired median, +1.3 % on the paired mean, 12 rounds. Keep it anyway; it is the base the SURF cascade was measured on.
>
> **1. SURF v1: per-line face colour (replaces the old item 1, "FDN inject keeps the broadband gain, tail unchanged").**
> - **What gets filtered.**
>   - Line *i* of bank A takes tap *i* (as in Render's `_scale_inject_reflect`, `taps[i % n_t]`); its hit letters are `surfaces_hit_by_n(n)`.
>   - The target is H_i(f) = Π over hit letters X of [absorb peaking stages relative to the card mean, i.e. `_absorb_to_db(α_b) − _absorb_to_db(ᾱ_X)` at the 7 `absorb_hz`, Q 0.9] × [face X EQ: low shelf, peak, high shelf, the same RBJ forms as `surface_filter_stages`].
>   - The broadband mean stays in `tap_reflect_gain`, unchanged, so a flat-shaped card is exactly today's sound.
>   - Muted or not-soloed faces: the FDN inject stays **un-gated** (D11/D12/D16). Use the un-gated surfaces for H_i, exactly as for `tap_reflect_gain` today.
> - **Render (`render_pipeline.py`).**
>   - In `_scale_inject_reflect`, after the broadband gain, cascade the exact relative-absorb + EQ stages for that line's hit letters onto `inj[:, i]`.
>   - Pass `sr` in. The box prototype is `s5_surf_1010\protoA_root\software\render_pipeline.py`, function `_surf_rel_stages`; copy it, don't import it from there.
>   - Early taps keep today's exact per-hit cascade (`apply_surface_to_buffer`), so the Render early field is unchanged. The box proves this: early bus max-abs 0.0.
>   - Render is the reference. Play approximates it with a fit (next bullet).
> - **Fit (server, Python, one function shared by the packer and the tests, e.g. `surface_colour.fit_line_cascade`).**
>   - Fit each line's H_i to ≤ K biquads: section 1 low shelf, 2 high shelf, then K−2 peaks. Use least squares in dB on a log grid of 50 Hz–18 kHz.
>   - Pick per line the smallest K that reaches ≤ 0.25 dB max error, capped at `SURF_K_MAX = 6`.
>   - Drop sections within ±0.05 dB of identity. A line with no sections left is a bypass.
>   - Box fit errors (`fit\fit_k.json`, 92 distinct hit sets, max error in dB):
>
>     | Case | K = 2 | K = 3 | K = 4 | K = 6 |
>     |---|---|---|---|---|
>     | Default | 1.57 | 1.08 | **0.24** | 0.08 |
>     | Face A HS +6 | 1.57 | 1.08 | **0.24** | 0.08 |
>     | Carpet floor | 4.11 | 2.47 | 0.77 | 0.48 (p95 0.33) |
>     | Extreme user EQ (A peak +12 Q4, C LS −12, steep E absorb) | 13.1 | 6.6 | 6.5 (p95 3.2) | 1.3 (p95 1.0) |
>
>   - The exact chain is up to 28–30 biquads per line, which is too expensive for Play.
>   - Log a per-line fit residual and expose the worst residual in the selfcheck. If a line misses 0.25 dB at K_MAX, ship the best fit and list it. Don't silently clip.
> - **Play (`live_stereo.c`).**
>   - Grow SURF compatibly. Length 0 (no Solo/Mute) and 192 (S4b early gates only) must load bit-exact, as today.
>   - v1 = the 192 gate floats, then `[version=1, K_max]`, then per bank (A, B) × 32 lines: `k_i`, followed by k_i × 5 normalised coefficients (b0 b1 b2 a1 a2), padded to K_max.
>   - Any other length → no cascade (bit-exact).
>   - The packer omits the cascade block when every line is a bypass. At flat cards (absorb all equal on every card, EQ 0 dB), Play must therefore be **bit-exact** with today.
> - **Placement in Play.**
>   - Use one DF2T cascade per line per source in the per-sample staging block before the bus loop, so it is shared by the L, C and R buses (the hit set depends on the line, not on the bus).
>     - Filter the image input `srcSmp[i]` (early read + inject) and the diffuse input that feeds the FDN inject (`diffSmp` → per-line `diffArr[i]`) on the radiation path.
>     - On the no-radiation path, filter `x` once per line, because the early read and the inject share it.
>     - On the two-source path, bank B uses its own taps and its own hit letters (mirrored: A↔C swap from its image indices), with its own state.
>   - Keep it outside the loop, before the tints. Decay alone still sets T60. Do not touch the Hadamard loop, H·D / `g_csignTab`, the DC restore, or air.
>   - Solo/Mute: the SURF gate stays a ×0 on the early read only (D16). The cascade runs regardless of the gate, so un-muting does not click.
>   - With shared tail on, the cascade lives before each bus's early lane and before the shared inject. It is never inside the shared loop.
>   - `reaktor_parity` = on → no cascade, bit-exact with today. The 2011 Reaktor had no face shape on the wet; ASSUMED.
>   - Coefficient changes: the server re-fits when the Surfaces controls change. Keep the DF2T state across a coefficient update; do not reset it. ASSUMED click-free for a UI drag, so check by ear.
> - **Prototype for reference.** `s5_surf_1010\f2\SURF_proto.c` = F2 + identity cascades at K = 2/4/6. It is bit-exact against the shipped wasm (max-abs 0.0) and is used only to measure CPU. It covers the radiation path only.
>
> **2.** Scattering Track C, Render half: unchanged from the roadmap S5 item 2. **3.** Smear: unchanged from the roadmap S5 item 3.
>
> **CPU (stop rule).**
> - Box, t19 scene (talking head + trumpet, two sources, radiation on, shared tail off). Per-block medians, alternating rounds, three runs on 3 Oct BST: 10:26–10:34 (12 rounds), 10:46–10:54 (8 rounds) and 10:56–11:00 (8 rounds). Files: `f2\bench2_1032.json`, `bench2_1054.json`, `bench2_1100.json`.
>
>   | Variant | Block-median ms (per run) | Paired median vs ship | Mean ms (per run) | Paired mean vs ship |
>   |---|---|---|---|---|
>   | ship | 1.863 / 1.941 / 1.898 | | 1.908 / 2.038 / 2.035 | |
>   | F2 | 1.827 | −0.8 % | 1.884 | +1.3 % |
>   | K = 2 (both lanes) | 1.910 | +2.2 % | 1.995 | +6.5 % |
>   | **K = 4 (both lanes)** | 1.966 / 2.045 / 1.993 | **+6.2 / +5.9 / +5.3 %** | 2.025 / 2.149 / 2.071 | +9.0 / +5.7 / +4.9 % |
>   | K = 4 image + K = 2 diffuse | 1.969 | +3.7 % | 2.031 | +3.3 % |
>   | K = 6 (both lanes) | 2.099 | +8.7 % | 2.194 | +8.0 % |
>
> - Gate: 0.8 × 2.667 = **2.133 ms**. Box K = 4 is at 92–96 % of the gate.
> - PC, ASSUMED: the PC's last t19 was about 2.05 ms (roadmap §0, 5–10 % slower than the box). On top of that:
>   - K = 4 → about 2.16 ms (**over**);
>   - K4/D2 → about 2.13 ms (at the gate);
>   - K = 6 → about 2.23 ms.
> - The prototype is the worst case. It is scalar, runs every section on every line, and covers two sources with radiation.
> - Measure t19 on the PC: three times with shared tail off, once with shared tail on, and once in the big room. Print the median and the mean for each.
> - If the t19 median goes over 2.133 ms, try these in order and print each. (a) and (b) leave the sound as specified; (c) and (d) cut fit accuracy, which is a sound change, so they need Idle's OK:
>   - (a) per-line adaptive K, so sections within ±0.05 dB are dropped;
>   - (b) f64x2 SIMD over bank A/B;
>   - (c) **ask Idle first:** K ≤ 2 on the diffuse (inject-only) lane, keeping the image lane at K_max (box −1.5 % against K4/K4);
>   - (d) **ask Idle first:** K_max = 4.
>
>   If it is still over after (a) and (b), stop and report the numbers before the scatter step. Don't apply (c) or (d) on your own.
>
> **Acceptance tests (new, in `software\tests\test_s5_surf_tail.py`).** Compare Play and Render as per-engine deltas against the same engine with flat-shaped cards. The box shows an absolute Play-vs-Render early-bus offset of about +6 dB broadband that predates S5 (cause not checked; ASSUMED a bus-definition difference), so absolute early nulls are not the test.
> 1. **Play vs Render parity per face colour.**
>    - Cases: default absorb shape, face A HS +6, all faces HS +6, carpet floor, face A peak +6 dB Q 1 at 1 kHz.
>    - For each case, compute the third-octave Δ (case − flat) for early 0–80 ms and tail 80 ms+, 125 Hz–16 kHz.
>    - Pass: |ΔPlay − ΔRender| ≤ 0.3 dB per band (≤ 0.8 dB for carpet).
> 2. **The tail moves.**
>    - Face A HS +6 dB: the Render and Play tail (80 ms+) at 8–16 kHz is ≥ +0.3 dB. Box Render: +0.41/+0.53/+0.48/+0.52 at 8/10/12.5/16 kHz; today 0.00.
>    - All faces HS +6: ≥ +4 dB at 10–16 kHz. Box: +5.6/+6.0/+5.6.
> 3. **Flat is bit-exact.** Flat-shaped cards (all bands = the card mean, EQ 0) → Render and Play max-abs 0.0 against the pre-S5 tree (box Render prototype: 0.0).
> 4. **Parity is exact.** `reaktor_parity` on → Play and Render bit-exact against the pre-S5 tree.
> 5. **Mirror is exact.** The mirrored scene (source/mic mirrored in x, A↔C cards swapped) equals the original with L↔R swapped, to max-abs 0.0 in Play and ≤ −120 dB in Render, including two sources.
> 6. **Passivity.** `test_fdn_passivity`, `test_s4b_long_decay_no_runaway`, `test_s4b_tail_solo_runaway` and `test_s4_followups` stay green. Add a case: carpet floor + all faces LS +12 dB + max Decay, with no runaway over 20 s. The cascade is outside the loop, so T60 is unchanged; assert T30 within ±3 % against flat.
> 7. **SURF compatibility.** Lengths 0, 192 and a malformed v1 load bit-exact or bypass. Solo/Mute still gates the early field only, and the cascade does not change the D16 co-hit policy.
> 8. **Fit.** At default, every line's fit residual is ≤ 0.25 dB. The selfcheck prints the worst line.
> 9. Still green: run_all t13, t18, t15, t19 (CPU above), t06; `test_binaural_play_tail_coherence_matches_head` + `_ensemble`; the shared-tail P1/P7/P8; `test_locks` (update the SURF regex if needed and say so); and the old `test_p4_*` (rename `test_p4_play_render_early_null` to the Δ-based test 1).
>
> **Expected change at defaults.** Default client body, every card absorb .05 .06 .08 .10 .14 .18 .22, EQ flat. Third-octave dB, L/R mean.
>
> | Hz | 125 | 250 | 500 | 1k | 2k | 3.15k | 4k | 5k | 6.3k | 8k | 10k | 12.5k | 16k |
> |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
> | Tail 80 ms+ (Render FDN and mix; Play the same, ASSUMED, since Play − Render tail is 0.00 dB after S7) | +0.39 | 0.00 | +0.19 | +0.05 | +0.02 | −0.18 | −0.21 | −0.27 | −0.33 | −0.37 | −0.28 | −0.14 | −0.07 |
> | Play early 0–80 ms (Render early per-band vs mean-flattened; ASSUMED to equal the Play early change, fit ≤ 0.24 dB) | +0.26 | +0.15 | +0.23 | +0.03 | −0.10 | −0.26 | −0.33 | −0.35 | −0.40 | −0.39 | −0.31 | −0.18 | −0.07 |
> | Render early | 0 (unchanged) | | | | | | | | | | | | |
>
> - Full bands (100 Hz–16 kHz, including the ±0.5 dB low-frequency ripple from tail modes) are in `expect\expect_default.json`.
> - Guitar level, before RMS matching: the tail is +0.74 dB louder and the full mix +0.18 dB. With the carpet floor: tail +2.0 dB, mix +0.53 dB. The LF stops being absorbed at the card mean.
> - **These change the defaults**, so list them in HANDOVER.
>
> **Goldens.** Regenerate the Render **and** Play goldens with `--reason "D-UI26=A (S5): per-line face colour (absorb shape rel. to card mean + face EQ) on the FDN inject in both engines and on Play early; F2 cold-fields patch (bit-exact)"`, and record it in `GOLDEN_META.json`. Before regenerating, prove items 3 and 4 above (flat and parity bit-exact against the old goldens).
>
> **Listening.** Re-render Idle's default scene before and after, guitar dry estimate, level-matched, and add to `roadmap\s5_surf_1010\guitar\LISTENING_CHECKLIST.md` (the box Render-only pairs are already there). Add Play pairs recorded from the app if you can.
>
> Keep the locks:
> - ±1 Hadamard (H·D counts);
> - early images feed the FDN;
> - 1/r²;
> - serial per-hit cascade (Render exact; Play fitted per line, same serial product);
> - per-line colour;
> - the two diffusion layers kept separate;
> - stage order source → air → surfaces → mic colour;
> - direct path air-free;
> - no air on the FDN return;
> - Reaktor parity.
>
> Surface controls stay on the Surfaces tab. List anything else that changes the sound at defaults instead of choosing it quietly.

---

## Evidence in this folder (box, 3 Oct 2026 BST)
- `f2/`:
  - `make_variants.py`, `ship_1010.c`, `F1.c`/`F2.c`, `F2_cold_shared_fields_rebased_1010.patch`;
  - `exact_1010.py`/`.json` (F1/F2/rebuilt = 0.0);
  - `make_surf_proto.py`, `SURF_proto.c`, `exact_proto.py` (K 2/4/6 = 0.0);
  - `bench_surf.py` with `bench2_1032.json` (clean, 12 rounds, 10:26–10:34), `bench_run1_noisy.*` (10 rounds, 10:13–10:24, overlapped a probe; not used) and `bench2_1054.json` (K4/K6, 8 rounds; `fit_k.py` was running at nice 19 on another core), `bench2_1100.json` (K4 vs K4 image + K2 diffuse, `SURF_K4D2.wasm`, `exact_proto_k4d2.py` = 0.0).
- `expect/`: `expect_default.py`/`.json` (R0 = 1010 Render, RA = prototype A).
- `fit/`: `fit_k.py`/`.json`.
- `guitar/`: 12 WAVs, `guitar_ab.py`/`.json`, `LISTENING_CHECKLIST.md`.
- `protoA_root/software/`: a box-only copy of the 1010 software with prototype A in `render_pipeline.py`. **Do not copy it over the real tree.**
