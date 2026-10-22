# CARPET PASSIVITY DIAG — 2026-10-19 (read-only)

Scope: why `software/tests/test_s5_surf_tail.py::test_passivity_carpet_ls` missed ±3% after the PHYSDEFAULT flip (phys_ceiling default on). Nothing under `software/`, the harness or tests was edited. Scratch scripts and raw output: `%TEMP%\carpet_diag\` (`targets.py/.txt`, `measure.py/.txt`, `livedict2.py/.txt`). All numbers below are VERIFIED on this PC with `software\.venv\Scripts\python.exe`, on the current (post-PHYSDEFAULT-Step-1) tree.

## Verdict

**The test's assumption has stopped being true. This is not a bug.** The physics path is doing what it was designed to do: it sets the in-loop decay from the room's materials. The test's "flat" reference is a *different room*: every face is set to the card's 7-band mean, 0.119 at all frequencies. The carpet scene keeps five faces at 0.08 at 500 Hz and puts 0.14 on the floor. At 500 Hz the carpet room therefore absorbs less than the reference, so it rings longer. From 1 kHz up it absorbs far more, so it rings much shorter (that would have failed next if the loop hadn't stopped at 500 Hz). Confidence: **high**.

## 1. What the test asserts, and why

- Scene: the client default body (`s4_verify_1140/client_body_1140.json`), boot room 6 × 3 × 8 m, `decay_mode` "flat" (Surfaces decay off), colour BYPASS, FDN only (direct 0, early 0), **decay_lock on, dial 8 s**. "loud" = floor (face E) set to CARPET `[0.02 0.06 0.14 0.37 0.60 0.65 0.70]` at 125 Hz–8 kHz, **plus every face low shelf +12 dB** ("ls" = low shelf). Reference = `_flat(body)`, which is the *default* body (no carpet) with each card set to its own 7-band mean (0.119) and its EQ zeroed. Play only, 20 s, `colour_on` False.
- Asserts: finite output; the 2-second level steps fall monotonically; the 18–19 s level is ≤ −150 dB (no runaway); left-channel T30 at 500/1k/2k/4k within ±3% of the flat reference.
- Intent (S5_PROMPT_D-UI26.md item 6): "Add a case: carpet floor + all faces LS +12 dB + max Decay, with no runaway over 20 s. **The cascade is outside the loop, so T60 is unchanged; assert T30 within ±3 % against flat.**" It proves that the S5 per-line face-colour cascade, which only colours the inject, cannot change the decay. The ±3% only means something when the lock pins the in-loop decay to the dial whatever the materials are. That was the dial path when S5 was written. HANDOVER line 314 numbers (0.9818/0.9945/1.0010/1.0019) were dial-path.
- So yes: **the T30 gate was only ever meant for the dial path.** The no-runaway half is still valid on both paths.

## 2. Band table (left-channel T30, the test's own `analyze.t60_bands`, 20 s Play)

| Band | Phys ON carpet | Phys ON flat | ON ratio | Phys OFF carpet | Phys OFF flat | OFF ratio |
|---|---|---|---|---|---|---|
| 125 Hz | 4.812 | 3.781 | 1.2727 | 5.916 | 6.431 | 0.9199 |
| 250 Hz | 6.735 | 5.185 | 1.2989 | 7.360 | 7.469 | 0.9854 |
| 500 Hz | 6.938 | 6.281 | **1.1046** | 7.903 | 7.908 | 0.9994 |
| 1 kHz | 5.139 | 6.119 | **0.8400** | 7.945 | 7.967 | 0.9973 |
| 2 kHz | 3.284 | 5.054 | **0.6497** | 7.965 | 8.044 | 0.9901 |
| 4 kHz | 2.243 | 3.775 | **0.5943** | 8.002 | 8.021 | 0.9977 |

- The ON 500 Hz row reproduces Build's 6.938 / 6.281 / 1.1046 exactly.
- OFF (explicit `phys_ceiling: false`) passes every gated band, worst 0.9901. No-runaway passes in all six runs (monotone; 18–19 s level −214/−229/−197 dB on, −186/−184/−185 off).
- Side note, not gated: 125 Hz is about 8% short for carpet+LS on the **dial** path too (0.92 against flat *and* against default). That predates PHYSDEFAULT and is probably the +12 dB low shelf interacting with the 125 Hz band measurement. Low priority.

Physics ON, carpet room versus the real default room (same walls, untreated floor): 125 0.902, 250 0.974, **500 0.861**, 1k 0.756, 2k 0.692, 4k 0.749. Carpet is shorter in every band, as it should be.

## 3. Cause, traced

Path: the scene has `decay_mode` "flat", so `_live_surf_pack` → `_ceiling_spec` → `phys_ceiling_pack(..., surfaces_on=False)`. The non-Surfaces branch gives every line `rates = 60 / T_eff(f)`, log-interpolated from the octave row `phys_ceiling_row`. T_eff = `room_target` (arau_scatter, air on, humidity 0.35) on cards copied as `clip(k·card_alpha, 0.01, 0.99) + s·bass(f)`, with k = 0.152005 (dial 8, solved on the boot room) and s = 0.106194.

Physics targets (s), from `targets.txt`:

| Hz | default | carpet (= loud; LS +12 is ignored) | flat ref | carpet/flat target |
|---|---|---|---|---|
| 63 | 4.111 | 4.111 | 3.273 | 1.256 |
| 125 | 4.906 | 4.906 | 3.758 | 1.306 |
| 250 | 6.619 | 6.619 | 4.686 | 1.413 |
| 500 | 9.089 | 7.824 | 6.429 | **1.217** |
| 1k | 6.911 | 4.620 | 6.002 | 0.770 |
| 2k | 4.509 | 2.928 | 5.089 | 0.575 |
| 4k | 2.617 | 1.954 | 3.230 | 0.605 |

Area-weighted raw alpha at 500 Hz (floor/ceiling 48 m² each, walls 2×18 + 2×24, total 180 m²): carpet room (132·0.08 + 48·0.14)/180 = **0.096**; flat ref = **0.119**. The flat reference absorbs about 24% more at 500 Hz, so its T is shorter. At 1 kHz: carpet (132·0.10 + 48·0.37)/180 = 0.172 against 0.119, so carpet is much shorter. The measured ratios follow the target ratios: 1.105 against 1.217 at 500 Hz, 0.840 against 0.770 at 1 kHz. The fit and the octave-band measurement smooth the sharp 500 Hz peak.

Candidates checked:
- **Double-counting / cascade normalising against the dial: NO.** The S5 cascade (`surf_cascade`, 1986 values, carpet only) colours the inject outside the loop. `decay_mode` flat means `make_spec` Surfaces rates are not used. The loop decay is 60/T_eff alone. The low shelf +12 dB gives the same T_eff as carpet alone (`room_target` uses alpha only; in-loop EQ counts cuts only).
- **Cascade normalised to a flat reference that no longer matches: NO.** The flat body has no cascade (length 0). Its loop is also physics-driven, from its own 0.119 cards.
- **Carpet alpha at 500 Hz lower than flat's: on the floor it is higher (0.14 against 0.119). The *room average* is lower (0.096 against 0.119), because `_flat` also raises the five untouched faces from 0.08 to 0.119 at 500 Hz. THIS IS THE CAUSE.** Note that `_flat` flattens the default body, not the carpet body.
- **Guard fallback: NO.** The live dict for both scenes has `surf_on` 1, `surf_refused` None, max loop −0.0416 dB (carpet) / −0.0494 dB (flat), keep [1,1,1]. Measured carpet T at 125/250 tracks target (4.81/4.91, 6.74/6.62).
- **ROOMTONE: NO.** Same body on both sides, and the targets alone explain the sign and size.
- Bass: k·alpha clips to ALPHA_MIN 0.01 at 125 Hz for both 0.05 and 0.02, so default and carpet have identical bass targets.

Related observation, not the cause: at dial 8 the measured T sits about 11% under target at the 500 Hz peak (default 8.056 against 9.089) and about 11–15% over at 4 kHz (default 2.996 against 2.617, carpet 2.243 against 1.954). This matches F9_DIAG's "dials 4 and 8" item (plain-decay swap-in at the top end) and the peak smoothing. It belongs to that fix, not this one.

## 4. Is the physics result physically right?

Yes. A room with five faces at 0.08 and a 0.14 floor at 500 Hz has less total absorption than a room where every face is 0.119. A real room like that rings longer at 500 Hz and much shorter from 1 kHz up. Against the real reference (the same room with its untreated floor), carpet shortens every band from 250 Hz up, by 14% at 500 Hz and 24–31% at 1–2 kHz. That is what real carpet does. The test's "T unchanged" premise was true only while the lock pinned T to the dial. On the physics path materials set T by design.

## 5. Fix options, ranked

**(a) RECOMMENDED. Test-only, no sound change.**
1. In `test_passivity_carpet_ls` (~line 470), add `"phys_ceiling": False` to `body.update({...})`. `loud` (deep copy) and `flat` (`_flat(body)`) both inherit it. Update the docstring: "Dial path (phys_ceiling false): the S5 cascade is outside the loop, so the lock holds T30 within ±3% of flat." Expected result from this diag: 0.9994 / 0.9973 / 0.9901 / 0.9977 at 500/1k/2k/4k, no runaway.
2. Add `test_passivity_carpet_ls_physics` (key absent = physics on): same loud scene, and the reference is the **unflattened default body** (`body`, not `_flat`). Assert finite output, monotone levels, 18–19 s ≤ −150 dB, and carpet T30 ≤ 1.03 × default T30 at 500/1k/2k/4k (carpet must not lengthen any of them). Measured: 0.861 / 0.756 / 0.692 / 0.749. Print, but don't gate, the measured ratio against `phys_ceiling_row` target ratio (0.861/0.669/0.649/0.747), because the 1 kHz step is smoothed by about 13%. Cost is about 55 s of Play (carpet ~43 s, default ~12 s).
- No pins, goldens, wasm, WORKLET_VER or CPU change. The PHYSDEFAULT prompt's rule 5 already names explicit false as the repair after this report.

**(b) Code fix: not recommended.** Pinning carpet to the flat reference on the physics path would undo the physics path, which exists so that materials set the decay. No code defect was found in `phys_ceiling_pack`, `ceiling_card_copy`, `k_for_dial`, the cascade or the guards. Any such change would alter the default sound and move play_std_lock18_* and the live MD5s again.

**(c) Other.** Changing the reference to `_flat(loud)` doesn't fix the gate either: targets differ by 1.74/1.08/0.77/0.74. The dial-8 peak/top-end error is F9's "dials 4 and 8" item, already queued.

**Listening:** option (a) changes no audio. Nothing here goes beyond the approved physics flip. One thing worth Idle knowing, and it's part of that flip: on the physics path a carpet floor now audibly shortens the tail (about −14% at 500 Hz and −25–30% at 1–2 kHz at dial 8), where on the dial path it only coloured it.
