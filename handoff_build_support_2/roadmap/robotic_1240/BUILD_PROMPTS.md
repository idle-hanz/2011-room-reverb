# Paste-ready Build prompts (2 Oct 2026, 15:20 BST; S4b final merges our diagnosis with Grok Build's 14:3x fix plan)

> **2 Oct 17:30: S4b final is done and verified (roadmap §0.0). The current Shared tail, S7 and S5 prompts are in `BIG_JOBS_ROADMAP_2026-10-01.md` §5 ("Next prompts, in order"). §2 and §3 below are the 15:20 drafts; use the roadmap versions.**

Order: **1. S4b final** (paste first; about 35 % usage, ASSUMED) → **2. Shared tail option** (new prompt; about 30–40 %) → **3. S5** (new window).
These replace the 12:25 "S4 fix-up" message and the 14:05 "S4b combined fix-up". Idle confirms decisions D12 and D14–D17 (list at the end of prompt 1) before pasting. Each decision has a recommendation, and the prompt is written with the recommended answers.

---

## 1. S4b final (paste first)

> Hi Build. This is the final S4b plan. It merges your read-only report and fix plan with the box diagnosis. Where the two disagree, the box measurement wins, and the reason is given. Evidence is in `handoff_build_support_2\roadmap\robotic_1240\`. The proof tests are in `3_phase_acceptance_tests\tests\test_s4b_tail_solo_runaway.py` (10 tests; on 11:40, 2 pass and 8 xfail).
>
> **Why your plan changes**
> - **The robotic sound in Idle's file is the default room, not the hall.**
>   - His file (`Desktop\tmpvf2xxu9a.wav`) is the `/api/render` preview of `software\renders\out.wav`. So it is **Render** at 44.1 kHz.
>   - The scene is the default room 6 × 3 × 8 m, ORTF, decay 1.8 s, FDN only. The page faders keep direct and early at −inf.
>   - The 11:40 Render IR nulls his file to **−64 dB** (other scenes give −7 to −20 dB).
>   - The buzz is a comb on the 103.5 Hz harmonics (comb index 11.1 dB), with autocorrelation peaks at 9.67 / 19.34 ms.
>   - Your fix plan has no fix for this comb, so it is item 3 below.
> - **Your Fix 2, the diffusion cap: the box data says no** (D14).
>   - The small hall Dffs are real (big room median |Dffs| 0.044, Hall preset 0.23). But capping the scale makes the decay longer; it does not make the tail denser.
>   - Hall preset: T30 goes 2.81 s → 3.48 s at median 0.36 → 5.78 s at 0.52 → 11.1 s at 0.72, while echo density at 0.2–0.4 s stays 0.18–0.20.
>   - The sparseness comes from the long delays (89–687 ms).
> - **Your Fix 3, solo: Solo/Mute must not touch the tail at all**, so the FDN inject is never gated (item 2).
>   - The −12 dB far-capsule trim is not needed. Early-only Solo A already gives L−R +9.1 dB in Play and +23.8 dB in Render with D11.
> - **Your Fix 1, the passivity guard: use the exact C restore below instead, and keep your grid check as the test.**
>   - Python cannot fix the DC inside float32 storage. On the hall X axis, 1 + a1 + a2 ≈ 1.3e-7, which is about one float32 step of b2. So rounding alone moves the DC by up to ±50 %; that is how today's 1.5 arises.
>   - Scaling the whole numerator down by 1/1.518 cuts that axis by 3.6 dB on every pass.
>   - "44.1 k is a no-op" is also not true. The default room's Z axis at 44.1 kHz has float32 DC 1.0065. At decay 20 s the 11:40 tail stalls at −88 dB and then rises by 0.2 dB/s.
>
> **Order:**
> 0 backup → 1 runaway → 2 Solo/Mute early-only (incl. D11, D12, D15, D16, D17) → 3 column signs (the comb) → 4 binaural skip-centre → 5 docs → 6 proofs and CPU.
>
> Keep items 1, 2 and 4 bit-exact at defaults. Item 3 is the only intended sound change at defaults.
>
> **0. Backup.** There is no git repo. Before editing, zip `software\` to `software_backup_2026-10-02_preS4b.zip` next to it (or `git init` and commit). Then list the backup path.
>
> **1. Long-decay runaway (Play): exact DC restore**
> - **Where:** `software\engine\live_stereo.c`, `load_core_body`, right after `pb0..pa2` are read for bank b.
> - **How:** add one line, in double:
>   ```c
>   if (on) st->pb2[b] = 1.0 + st->pa1[b] + st->pa2[b] - st->pb0[b] - st->pb1[b];
>   ```
>   - Cut-only peaking has unity DC gain by design; this restores it from the float32-stored coefficients.
>   - No Python change. It covers both rates, stereo and binaural, because they all use the same load path.
>   - Render is float64 and already fine.
>   - Prototype: `fixwasm\fix.c` (`fix_vs_ship.diff`).
> - **Done when:**
>   - Your passivity check, as a test: from the posted float32 blob coefficients with the restored b2, max|H| ≤ 1 + 1e-9 on a 0 Hz–Nyquist grid (include 0 Hz and 0.01–20 Hz finely). Check every axis and bank in the default room, the 57 × 34.2 × 97 m hall and the Hall preset, at 44.1 and 48 kHz. Box: hall X at 48 k goes 1.518 → 1.0; default Z at 44.1 k goes 1.0065 → 1.0.
>   - Default room at 48 kHz is bit-exact to 11:40 (1 and 2 sources, decay 1.8 s and 8 s).
>   - At 44.1 kHz the default room changes near DC only. Print the max diff.
>   - The runaway tests pass: hall decay 8 s with 2 sources, and binaural hall at 4 s and 8 s. Box: −202 / −287 (float floor) / −211 dB at 18–20 s.
>   - Also print a 20 s Play IR at 44.1 kHz, default room, decay 20 s: it must fall every 2 s (11:40: stalls at −88 dB).
>
> **2. Solo/Mute act on the early reflections only, plus audition**
> - **Where:**
>   - Play: `live_fdn_params` (render_pipeline.py ~1571), the SURF blob section, and `live_stereo.c` early reads (~1442, ~1450, ~1486).
>   - Render: `render()` (~1062), `_inject_levels` and `render_early_ir`.
>   - UI: the Surfaces tab and `heardMix`.
> - **How:**
>   - (a) **Tail untouched.** Compute the FDN inject, Dffs and makeup from the **un-gated** surfaces in both Play and Render. That means no `tap_reflect_gain` zeroing of `line->inj`, no `tap_dff` zeroing, and no "drop the direct from the FDN inject".
>     - Pass the effective (solo/mute) surfaces only to the early field.
>     - Today Solo A zeroes the inject on 30/32 lines and Dffs on 22/32; Mute-all zeroes all 32 Dffs. The tail drops 2.5 dB and narrows.
>   - (b) **Play early gate.** Add a SURF section (v0): `early_gate[3 buses][32]` for bank A, and the same for bank B (use bank B's own taps).
>     - A gate is 0 when the line's image is silenced under the co-hit policy D16, and 1 otherwise.
>     - Multiply the early-lane reads `ev`/`evB` by the gate before `eaBlk`/`ebBlk` and the `early` sum, at all three read sites.
>     - Section length 0 means no Solo/Mute: skip the multiply, so this stays bit-exact.
>     - `xin` and `LANE_FDN` stay un-gated. Fix the C comment at ~834 ("gates already in inject and Dffs").
>   - (c) **D16, co-hit policy (recommended).**
>     - **Solo X keeps every image that touches X.** Today Solo A keeps only (−1,0,0) plus the direct; with this it keeps all 10 nx<0 images.
>     - **Mute X drops every image that touches X.**
>     - Use the same rule in Play (gates) and Render (`render_early_ir`).
>   - (d) **D15, audition while soloed.**
>     - The direct line n=(0,0,0) gets early gate 0 whenever any face is soloed. In Render, skip the n=(0,0,0) term in `render_early_ir` while soloed. Mute alone keeps the direct.
>     - The FDN inject keeps the direct line.
>     - No capsule gain trim: no `mic_gain_r*=0.25` or `mic_gain_l*=0.25`.
>   - (e) **D11, Render Mute drops the face.** In `render_early_ir`, after `hit = surfaces_hit_by_n(...)`, skip the image when it is silenced under D16.
>     - Box: Mute A −1.99 dB, Mute E −2.46 dB, Mute-all −24.3 dB, Solo E −7.09 dB.
>   - (f) **D12, Solo auto-listens to Early.** While a face is soloed, the Mix plays Early only, using the Mix tab's existing Early solo:
>     - early at 0 dB if its fader is at −inf;
>     - direct, FDN and Host dry muted.
>     - Solo off restores the previous Mix exactly. Saves never store the temporary Mix. Mute alone does not change the Mix.
>     - Hint line on the Surfaces tab: "Solo: listening to early reflections only."
>   - (g) **D17, hint.** When D is soloed, add: "Back wall (−Z): Play's 32 images have no first-order back-wall image." Don't change the image set in S4b.
>     - Today LIVE_32 has no nz<0 image, and D's only images (0,1,2) and (0,0,2) also hit B.
> - **Done when:**
>   - FDN-only Play and Render with Solo A, or Mute A–F, equal no Solo/Mute: ≤ 1e-6 × peak (Play) and ≤ 1e-5 × peak (Render). The posted inject and Dffs are unchanged.
>   - Centred early-only: Solo A L−R ≥ +6 dB and Solo C ≤ −6 dB, in Play and Render.
>   - In `test_s4_followups.py`, remove the two xfail marks. Under mute-all, Render early is ≤ −20 dB and the FDN is unchanged.
>   - Print early-only levels and ILDs for Solo A/B/C/D/E/F in Play and Render (D16 on).
>
> **3. The comb (Idle's robotic tail): column signs in the loop matrix**
> - **Where:**
>   - Play: `live_stereo.c` `fwht32` (used by the feedback path and `DIFFUSE_FN(diffuse32, …)`).
>   - Render: `fdn.py`, where `FDN.__init__` sets `self.H`, and `diffuser_output_mix`.
> - **Why:**
>   - Each bus sums its 32 line outputs with weight +1. For a Sylvester Hadamard, 1ᵀH = 32·e0ᵀ, so the whole output re-enters the loop only through line 0. Line 0 is image (0,2,0) at 19.34 ms, which makes the comb.
>   - Line delays equal the image distances. The direct line (60 % of the inject) adds 9.67 ms.
>   - VERIFIED by perturbation: moving line 0 or the direct line moves the peaks.
> - **How:**
>   - Use the feedback matrix **H·D**, with D = diag(d) and the fixed table:
>     `d = [1,-1,-1,-1,-1,-1,1,-1,-1,1,-1,1,1,1,1,1,-1,1,1,1,-1,1,1,1,-1,1,1,1,-1,1,1,1]`
>     (also in `real\out_signs.json`).
>     - H·D is still a ±1 Hadamard (orthogonal, the same passivity, the selfcheck ρ test holds).
>     - Its rows are no longer parallel to the all-ones output.
>     - d is invariant under the mirror line map (b0 b4)(b1 b3), so symmetric scenes stay exactly mono and the mirror null stays exact.
>   - Play: multiply the 32 inputs by d_k at the top of `fwht32`. You may fold d_k into an existing per-line multiply if the result nulls the prototype to ≤ 1e-6 × peak.
>   - Render: `H * d[None, :]` for n = 32, in `self.H` and in `diffuser_output_mix`. Add a helper such as `loop_hadamard(n, parity)` and leave `unscaled_hadamard_matrix` pure.
>   - n = 8 and n = 16 are unchanged.
>   - Under `reaktor_parity`, keep plain H (bit-exact 2011, and the Hall button turns parity on). The Hall preset has no line-0 comb (ac peak 0.16).
>   - Binaural uses H·D too: its comb also drops (ac max 0.27/0.30 → 0.13/0.10, octaves within 3.3 dB).
>   - Prototypes: `fixwasm\csign.c` (`csign_vs_fix.diff`, `-DPEAK_DC_FIX -DCSIGN`), and the Render monkeypatch `real\mod_exp.py` with `EXP=csign`.
> - **Why not output signs** (the 14:05 plan, `osign.c`): they also break the funnel, but they change the first pass.
>   - The tail level rises: Render +3.2 dB, the big room +7.5 dB on guitar.
>   - The tone changes: the big room octaves move +10 dB / −7 dB.
>   - The comb index on Idle's guitar is 5.1 dB (column signs: 4.5 dB).
>   - Combining both is worse (Render ac 0.33/0.48).
> - **Box results for column signs vs 11:40:**
>   - Play default FDN-only: ac at 19.36 ms 0.43/0.37 → 0.15/0.18 (also the 2–60 ms max). T20 1.749 → 1.753 s; RMS −0.08 dB; octaves 63 Hz–8 kHz within ±1.3 dB.
>   - Default all-on: T20 1.392 → 1.345 s; octaves within 1 dB.
>   - Big room: T20 1.616 → 1.602 s; octaves within 0.2 dB except −3.9 dB at 63 Hz.
>   - Render 48 k: comb index 12.7/10.6 → 4.6/4.8 dB; ac max 0.41/0.42 → 0.24/0.24; T20 1.774 → 1.77 s; level −0.3 dB; octaves −1.3…+1.6 dB.
>   - Render 44.1 k: 10.9/10.6 → 4.5/4.5 dB.
>   - Idle's guitar (Render): comb index 11.1 → 4.5 dB, +1.2 dB raw.
>   - Symmetric scene max|L−R| = 0.0; mirror null 0.0.
>   - A/B on his guitar, level-matched:
>     - `real\ab_real\R1_render_default_fdn_only__{A_today,C_fix_column_signs}.wav`
>     - `real\ab_real\P1_play_default_fdn_only__{A_today,C_fix_column_signs_plus_DC}.wav`
>     - hall: `hall_b\ab_wav\*__D_column_signs.wav`
> - **Level:** no makeup change. Print the tail RMS at defaults before and after (Play, Render, binaural); each must be within ±1 dB.
> - A residual broad lag peak remains on Render R at 44.1 k (ac 0.37 at 19.34 ms; the comb index is fixed). The 9.67 ms direct-line echo is gone (ac −0.10), so D13 is closed: keep the direct line in the FDN.
>
> **4. Binaural: skip the empty centre bus** (bit-exact). Follow `2011 Room Reverb\research_shared_fdn\BUILD_BRIEF.md` Part 1:
> - `cEmpty = micG[C]==0 && every C line inj==0 && injB==0`.
> - When `cEmpty`, skip `bus_sample(C)` and bus C's mix, colour FIRs and IC collect.
> - When C comes back, zero its rings and line filter states.
> - Reference: `research_shared_fdn\proto\live_stereo_shared.c` with `-DSKIP_EMPTY_C` (−14 to −26 % binaural CPU on the box).
>
> **5. Docs.**
> - `2011 Room Reverb\HANDOVER.md` (27 Sep) is stale:
>   - **ORTF:** lines 92 and 154 say ORTF ±55° aims the capsules inward. Since K1 (28 Sep, `early_field.py` `YAW_X_SIGN = +1`), L −55° / R +55° aim **outward**. Rewrite both lines and drop the "source on the left is stronger in the right capsule" advice.
>   - **FDN gain:** lines 75, 166, 179, 211 and 222 state `Out = In × (1/32) × Gain` / `g = Gain/N` as the live rule. Say that this is the `reaktor_parity` / lock-off rule only. With Decay lock on (the default), the loop mix runs at g = 1/√32 ≈ 0.177 (a lossless mix), and the per-line `line_t60` loss on each delay read sets the decay. The decay-lock `g_decay` (about 0.158) is used only for the makeup gain. (Corrected 2 Oct 16:30: an earlier version of this line said the loop runs at 0.158.) Line 67's "pack's cure" (mix exactly 1/√N plus a delay-proportional loss per read) is what is live now, so say it landed.
>   - **Positive Dffs:** line 73 says positive Dffs can grow in the one-sample loop. For g ≤ 1/√N the loop is passive at any |Dffs| < 1, of either sign (`research_f5_allpass/REPORT.md` §2). Say it is stable.
>   - Add the S4b changes: the DC restore, Solo/Mute early-only, H·D column signs (plain H under parity), D11/D12/D15–D17.
> - Don't edit the box handoff files.
>
> **6. Proofs, goldens and CPU**
> - `test_s4b_tail_solo_runaway.py`: all 10 pass, so remove its xfail marks.
>   - The Render comb test now uses the comb index (≤ 6 dB per channel) plus ac max ≤ 0.40.
>   - The Play comb test keeps ac at 19.36 ms ≤ 0.20 and ≤ 0.30 over 2–60 ms.
> - `test_s4_followups` 4/4.
> - Brief P2: binaural default at 1 and 2 sources and binaural big, colour on and off, diff 0.0 **before item 3**.
> - Goldens:
>   - After items 1, 2 and 4, t01–t05 are bit-exact. Check this before item 3.
>   - After item 3, show t01–t05 failing only on the tail, then `--regen-golden --reason "S4b column signs H*D"`.
>   - `reaktor_parity` stays bit-exact to 11:40 throughout.
> - Your tests, selfcheck and phase `--slow` are green except the old small_lock08.
> - **CPU on the PC:**
>   - t19 three times, printing the ms. It must stay **≤ 2.133 ms** (it was 2.048–2.052). The column signs are 32 sign flips per `fwht32` call; fold them if t19 gets close.
>   - Binaural block min ms before and after item 4; it must be lower.
> - Rebuild the wasm and bump WORKLET_VER.
> - Re-render Idle's scene (default room, FDN-only, 44.1 kHz) and compare with `real\ab_real\R1_render_default_fdn_only__C_fix_column_signs.wav`.
> - List every change at defaults:
>   - expected: the column-sign tail (comb gone, level within ±1 dB);
>   - near-DC only: the 44.1 k default room and the big room.
>
> **Out of scope:**
> - the diffusion-scale cap (D14 = no);
> - a −Z image or any image-set change;
> - capsule gain trims for Solo;
> - shared tail (next prompt);
> - scattering and density (S5/S6);
> - decorrelating the symmetric mono tail;
> - any change under `reaktor_parity`.
>
> **Decisions (Idle confirmed; this prompt assumes the recommended answers):**
> - **D12:** Solo auto-listens to Early (direct, FDN and Host dry muted; restored exactly on Solo off). **Yes.**
> - **D14:** Diffusion-scale cap for big rooms. **No.** In your band (median 0.35–0.70) it lengthens the Hall preset T30 from 2.8 s to 3.5–5.8 s with no density gain. In the big room with column signs, cap 18 gives density 0.26 → 0.21 and +8.5 dB on guitar. A/B: `hall_b\ab_wav_d14\`.
> - **D15:** While soloed: drop the direct line from the early field, **yes**; mute direct and Host dry via D12, **yes**; your −12 dB far-capsule trim, **no** (it is not physical, and the ILD is already +9.1 dB in Play and +23.8 dB in Render); drop the direct from the FDN inject, **no** (the tail stays untouched).
> - **D16:** Solo keeps co-hit images; Mute drops them. **Yes.**
> - **D17:** No first-order −Z image in Play's 32: add the hint now; any image-set change goes to a later session. **Hint only.**

---

## 2. Shared tail option (separate prompt, after S4b final is in)

> Hi Build. Next: the "Shared tail" Live option. Follow `2011 Room Reverb\research_shared_fdn\BUILD_BRIEF.md` **Part 2** and its proof tests P1 and P3–P10. P2, the skip-empty-centre, is already in from S4b final. Idle's choices:
> - **Live (Play) only.** Render and `reaktor_parity` are untouched.
> - **Default off.** Off is bit-exact to the S4b build in P1's 5 scenes, colour on and off.
> - **Stereo mic setups only.** It is ignored in binaural, so P8 is bit-exact to off.
> - Jitter **0.3 ms**, hash **seed 1**, computed at load.
> - The reference is `2011 Room Reverb\research_shared_fdn\proto\live_stereo_shared.c` with `-DSHARED_MODE=1 -DSHARED_JITTER_US=300 -DSHARED_JSEED=1`.
>
> How it fits with S4b final:
> - The shared loop's inject injS uses the un-gated inject (Solo/Mute never reaches the tail).
> - Bus C's early lane keeps C's own inject.
> - The SURF early gates apply to every bus's early read exactly as before.
> - The peaking DC fix stays in.
> - The S4b column signs live inside the loop matrix (H·D in `fwht32`), so the shared loop uses H·D too. The output taps stay all +1. d is mirror-invariant, so P7 stays bit-exact.
> - P1's "previous build" is the S4b final build, with column signs.
>
> Idle also keeps the exact mono tail in symmetric scenes. Do not decorrelate it: P7's mirror null ≤ −120 dB stays.
>
> UI: one checkbox, "Shared tail (lighter CPU)", in the Play/Live options, with the hint "Play only. One reverb network feeds all mics; ignored in binaural." It is greyed out in binaural.
>
> Proofs:
> - P1–P10 from the brief.
> - P9 now runs on the fixed engine: 30 s at decay 8 s in the default room **and the big room**, finite and falling.
> - `test_s4b_tail_solo_runaway` still green, plus a Solo A check with shared on: the tail is unchanged.
> - **CPU on the PC:**
>   - t19 with shared off (≤ 2.133 ms, unchanged);
>   - the default two-source Play block min ms with shared on, which must be ≥ 15 % below off (alternating rounds, min of 6);
>   - print all the ms.
> - Goldens unchanged.

---

## 3. S5 (new Build window, after the two prompts above)

> Hi Build. Plan: `2011 Room Reverb\handoff_build_support_2\BIG_JOBS_ROADMAP_2026-10-01.md`, session S5. S1–S4, S4b final and the shared-tail option are done. That covers Solo/Mute acting on the early field only (co-hit policy D16), the peaking DC restore, the H·D column signs that removed the line-0 comb, Render Mute dropping the face, the binaural skip-centre, and shared tail as a Live option that is off by default. Read the roadmap §0.0 and §5 first. Then:
>
> 1. **Play per-hit surface cascade (J8, `build_support\planning\BUILD_ROADMAP.md` §P4), on the early lane only.**
>    - Extend the SURF section, which today holds the S4b `early_gate`s, so Play early gets each image's serial per-hit wall EQ: the same `absorb[7]` cascade Render uses, in hit order. Flat cards must be a bit-exact bypass.
>    - The FDN inject keeps the broadband `tap_reflect_gain` from the **un-gated** surfaces (exactly as Render's `_scale_inject_reflect`), so the tail is unchanged.
>    - Play early uses the per-hit cascade *instead of* the broadband gain, so absorption is not counted twice.
>    - A muted or un-soloed face stays gate 0 on the early lane only.
>    - The FDN must stay untouched by Solo/Mute (`test_s4b_*` stays green).
>    - Keep the S4b column signs (H·D) in the loop, with plain H under `reaktor_parity`.
>    - With shared tail on, the cascade applies to each bus's early lane and never to the shared loop.
> 2. **Scattering Track C, Render half** (`handoff_surfaces_for_build\briefs\GROK_BUILD_BRIEF_Surfaces_scattering.md` §5.1).
>    - Scatter after air, per reflection, energy-preserving, feed-forward only, with no scatter in the FDN loop.
>    - Scatter 0 must be bit-identical.
>    - This is the route for the sparse Hall tail (D14 rejected the diffusion-scale cap: it lengthened T30 without adding density). Mean-removed echo density at 0.2–0.4 s is about 0.2 in the hall. That is long-standing, not new.
> 3. **Smear (`jitter_D`)** is still Render-only. Either add it to Play early with the cascade, or leave it and add one line to the Surfaces tab hint ("Smear: Render only"). Say which.
>
> Keep the locks:
> - ±1 Hadamard FDN (H·D counts: it is still ±1 Hadamard);
> - early images feed the FDN;
> - 1/r²;
> - serial per-hit cascade;
> - the two diffusion layers kept separate;
> - stage order source → air → surfaces → mic colour (→ scatter after air in Render);
> - direct air-free;
> - no air on the FDN return.
>
> Surface controls stay on the Surfaces tab only.
>
> Proofs:
> - `test_p4_play_render_early_null`, `test_p4_flat_cards_bit_exact_bypass`, `test_p4_cpu_budget`, `test_p5_scatter_zero_is_bit_identical`, `test_p5_scatter_after_air`, `test_p5_energy_and_feed_forward`, run_all t06.
> - `test_s4_followups`, `test_s4b_tail_solo_runaway`, `test_s3_source_b` and the shared-tail P1/P7/P8 still green.
> - Goldens unchanged at defaults.
>
> CPU is tight (t19 about 2.05 ms on the PC vs the 2.133 ms gate):
> - Measure t19 three times on the PC (shared tail off), once with shared tail on, and once in the big room (57 × 34.2 × 97 m, two directional sources + colour). Print the ms.
> - If the cascade pushes t19 (shared off) over 2.133 ms, stop and report before the scatter step.
>
> List anything that changes the sound at defaults instead of choosing it quietly.
