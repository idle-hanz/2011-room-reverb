# Ideas backlog: everything not built yet (2026-10-19)

Read-only audit, written 19 Oct 2026 at about 08:05 BST. Nothing in `software\` or any other file was changed; this is the only new file.
Checked against: `HANDOVER.md` (Current pin 2026-10-18), `roadmap\BUILD_RUN_LOG.md`, `OPEN_FAULTS_2026-10-10.md` and `-18.md`, every `DECISION_*.md`, `THURSDAY_LIST.md`, `AUDIT_2026-10-17.md`, `thursday_prompts\` (incl. PHYSDEFAULT and BLOOM), `nonrect\`, `sound_tricks\SOUND_TRICKS.md`, `prebuild\sl\README.md`, `mic_character\`, `bloom\`, `research_ui_wishlist\REPORT.md`, `ui_audit_1004\UI_AUDIT.md`, `book\` (STATUS, ch 4, 9-12), `demos\`, `Idle Hanz ideas 02-10-26.docx`, `TWO_SOURCES.md`, and the project memory notes.

**Status words:** *idea* (talked about, nothing written) / *researched* (a research file exists) / *prompt written* (a Build prompt is ready) / *partly built* (some of it is in the tree) / *parked* (deliberately put aside) / *landed* or *superseded* (kept here only so it isn't chased again).
**Order:** 1 = do soon, 2 = after the queue, 3 = later, 4 = long-term. ⚠ = looks forgotten (mentioned, then never followed up).

---

## 0. The current queue (in this order)

| # | Item | What it is | Status | Files | Blocking |
|---|---|---|---|---|---|
| Q1 | **PHYSDEFAULT** | The "Physical ceiling" tick box starts ticked, so the physics decay is the default everywhere. No sound change to the physics path itself. | Prompt written; Step 0 review not run | `thursday_prompts\PHYSDEFAULT_RUN_2026-10-19.md` | Step 0 review. Note for Step 0: the prompt says the box is on the "Room page" but the HANDOVER AMBIENCE pin says the Physical ceiling box is on the **Mix tab**; check which. It also runs the acceptance suite, which settles fault F11, and re-measures F9 and F12. |
| Q2 | **BLOOM** (Parts 0-2) | The "virtual compressor" on the reverb tail: Predelay, then Amount / Threshold / Attack / Release with the five presets (Natural, Glue, Room Crush, Nuke, Swell; Swell Long and Talkback optional). Direct and early untouched. | Landed 2026-10-22. Play Neve is 1x and Play Room Crush colour is 1x. Render stays at the retry-3 factors. No page panel yet. | `thursday_prompts\BLOOM_RUN_2026-10-18.md`, `DECISION_BLOOM_2026-10-18.md`, `bloom\COMPRESSOR_RESEARCH.md`, `bloom\compressor_presets.json`, `bloom\spice\` | Landed |
| Q3 | **Off-axis tail colour** (D-OFFAXIS item 1) | Give each mic its measured "whole-room" tail colour (big mics darker, small mics more open) and put back its on-axis presence peaks. Behind a switch, off by default. | Built 2026-10-23, default off. Listen wavs in `roadmap\offaxis_listen\`. No Mix checkbox in that run. On-axis restore waits. | `thursday_prompts\BACKLOG_C_OFFAXIS_RUN.md`, `DECISION_OFFAXIS_QUEUE_2026-10-18.md`, `mic_character\MIC_CHARACTER_RESEARCH.md`, `mic_character_params.json`, `measured_third_octave.csv`, `verify_models.py` | Bloom has landed. Bloom's gain must sit before the per-bus colour |
| Q4 | **Colour module** (D-OFFAXIS item 2) | Optional transformer + valve / solid-state "iron" on the wet returns, one level-matched Drive knob and a Type picker. Off and bit-exact by default. | Researched; queued as optional | same as Q3 | Q3, and Idle's listen to Q3 |

---

## 1. Room shapes & geometry

| # | Item | What it is (plain words) | Status | Files | Blocking | Order |
|---|---|---|---|---|---|---|
| 1.1 | **Non-rectangular rooms** | Studio-shaped room presets that still scale with W/L/H: splayed control room (RFZ), LEDE, non-parallel live room, hexagon booth, gable-ceiling booth, L-shaped live room. Reflections are found as a tree, one branch per wall, and checked so only real echoes are kept. The Box stays the default and stays bit-exact. | **Stage 1 landed 2026-10-23.** Render only. Key `room_shape`. Absent or box stayed the shoebox, bit-exact. Presets splay, lede, live. Play stays the shoebox. 15 ms fades, the L-shape, and the N-face Surfaces page are later. Prompt was `thursday_prompts\BACKLOG_D_ROOMS_RUN.md`. | `roadmap\nonrect\NONRECT_RESEARCH.md`; prototype `nonrect\proto\ism_proto.py`, `brute_check.py`, `ism2d.py`, `make_diagrams.py`, `results.json`; diagrams `nonrect\diagrams\D1-D3`; one-page brief `roadmap\NONRECT_ROOMS_BRIEF.md`; research note `research\R16_space_nonrect_drawings.md`; book `book\09_nonrectangular_rooms.md` (stub); toy code `software\engine\polygonal_stub.py` (not wired); older notes `/workspace/non-cubic-rooms.md` on the box (9 Sep) | **Idle's 8 decisions D-NR1-D-NR8** (see section 6.1). Book ch 9 says "after SL7b"; that gate is now out of date (see 2.4). | 2 |
| 1.2 | Reflection switching fades (part of 1.1) | In odd-shaped rooms, echoes appear and vanish as a mic moves (up to about 30-39 per metre in the booths), which clicks. Fix: fade each echo in/out over about 15 ms and keep its slot stable. | Researched (measured in the prototype) | `NONRECT_RESEARCH.md` §5 "Glitches" | D-NR5; only needed for Play (stage 3) | 2 (with 1.1 stage 3) |
| 1.3 | Edge diffraction / beam tree / scattering delay network (part of 1.1 stage 5) | Smoother "round the corner" sound for the L-shape, and a different tank design (SDN). Research only. | Researched; SDN recommended parked (D-NR8) | `NONRECT_RESEARCH.md` §3, §5 | D-NR7, D-NR8 | 4 |
| 1.4 | **Wall / corner / ceiling drag (T8b) + canvas scaling (P1)** | Drag the walls on the floor plan to resize the room, instead of only sliders (Idle's U4). | **Partly built**: floor walls, corners, and the ceiling call `drag_model.js` (2026-10-23, backlog B). Snap law unchanged. Canvas scaling (P1) is not done. | `thursday_prompts\T08b_wall_drag_NOTES_2026-10-09.md` (must-fix list), `THURSDAY_LIST.md` U4, `prebuild\t7_t8_drag\README.md` | A full prompt + review | 2 |
| 1.5 | ⚠ **Reflection selection "loudest 32"** (U9) | Today the 32 echoes feeding the tank are a fixed table; an option is to pick the loudest 32 at each mic. Pros/cons were written up for Idle; he never answered. | Researched; info only | `THURSDAY_LIST.md` U9, `research\R11_reflection_selection.md` | Idle's call (it breaks parity goldens and mirror tests) | 3 |
| 1.6 | Scatter and smear (S5 items 2-3, S6 Play half, D24 velvet smear) | Rough walls smear each echo, so the early sound is denser (Hall echo density is very low today). | Parked (prompt in the old roadmap needs a rebase); locked "later, default off, CPU first" | `THURSDAY_LIST.md` L1, R4; `research\R12_scatter_smear_cpu.md`; `BIG_JOBS_ROADMAP_2026-10-01.md` §5 | CPU headroom (now better: cube 1.74 ms vs 2.40) and Idle | 3 |
| 1.7 | Realism fixes S8 (L2) | Pre-echo at t=0, missing back-wall image, speed of sound from temperature, direct-to-reverb calibration; optional physical direct level (ST-4 / ST-5, D22 opt-in). | Prompt in old roadmap; decision D22 "opt-in, later" | `THURSDAY_LIST.md` L2, N9; `sound_tricks\SOUND_TRICKS.md` ST-4, ST-5 | D22 / ST-4 listen | 3 |

## 2. Sound / DSP features

| # | Item | What it is | Status | Files | Blocking | Order |
|---|---|---|---|---|---|---|
| 2.1 | **SL4 directional decay + calibration** | Each tank line decays according to the walls it hits (D-SL2), plus one T20 calibration pass (D-SL4). | Prompt written + prebuilt code; "do not start on a bare continue" | `thursday_prompts\SL4_directional_calibration.md`, `prebuild\sl\README.md` | Decisions 6.3-6.5; needs re-checking against the physics path | 2 |
| 2.2 | SL5 treatment rows | Panels per wall: porous + air gap, membrane, Helmholtz, room shell; real "plaster + parquet" library. | **Landed 2026-10-23.** Stage 5. Shell on entering Surfaces. Library set only. Default cards unchanged. Helmholtz formula kept (Q 3). | `SL5_treatment_rows.md`, `software\engine\surf_panels.py` | done | 3 |
| 2.3 | SL6 auto-treat | Suggests up to 4 tuned panels to hit the target decay; EBU preset pass/fail. | Stopped 2026-10-24. Box plan matches. `/api/auto_treat` suggests and does not write the scene. Button stays hidden (`RR_SL_STAGE` 5). Gate 16/23. Start 13/23. One `surf_loop.py` fix scored 12/23 and was reverted. D-SL3: keep cuts below 30 Hz. | `SL6_auto_treat.md` | SL5 landed | 3 |
| 2.4 | ⚠ **SL7a / SL7b "one default switch"** | Locked 4 Oct: one re-record switching Surfaces + natural (air) decay + **U87 mics** + real materials on together, gated on Idle's written OK on a final A/B. | Prompts written; never run. **Partly superseded**: AMBIENCE + PHYSDEFAULT now make a physics decay the default by a different route. | `SL7a_default_switch_prep.md`, `SL7b_default_switch.md`, `DECISIONS_LOCKED_2026-10-04.md` (D-SL10, ST-1, ST-2, N11) | Needs a re-scope after PHYSDEFAULT: what is left of SL7 now that the physics ceiling is default? | 2 (re-scope) |
| 2.5 | **Movement (EQ-1b, T11b)** | Slow tail delay modulation (less metallic ring). | **Landed 2026-10-23.** Knob visible, default 0. `MOVEMENT_FORCED_OFF = False`. Shared-off at 100 was 1.876 ms, under 2.40. Curve unchanged. | `software\render_pipeline.py`, `software\static\index.html` | Do not retune the curve. | 2 |
| 2.6 | Room-tone cuts (ROOMTONE) and resonance control (N5) | Shallow cuts at the room's own resonances inside the loop. ROOMTONE's harmonic cascade is in the tree (it stopped on CPU, then SMALLDECAY's tank skip fixed CPU). N5's wider resonance control (Jot cuts, Mäkivirta target, Decay view) was never built. | Partly built | `ROOMTONE_RUN_2026-10-15.md`, `roomtone\depth_report.json`, `eq_plan\EQ_PLAN.md` §3, `eq_plan\RESEARCH_EQ_MODES_METALLIC.md` | Idle heard no difference from ROOMTONE: keep it? (6.9) | 3 |
| 2.7 | S-OUT: Auto level + Output EQ + master headroom | Something that keeps the overall volume stable so the mix faders act like balance (Idle's 2 Oct note), plus a post-mix EQ (low shelf / peak / high shelf) and a fixed headroom trim. | Researched; prompt in `research_ui_wishlist\REPORT.md` §7 "S-OUT" (needs a rebase) | `REPORT.md` §3, §7; `THURSDAY_LIST.md` N2-N4 | Auto level (D-UI11) was never answered | 2 |
| 2.8 | D-INT: 44.1 kHz interpolation (N6) | Play's interpolation loses top end at 44.1 kHz; round delays to whole samples instead. | Researched | `THURSDAY_LIST.md` N6 | Idle decision | 3 |
| 2.9 | Tank gating (D23 / N17) | Stop running a muted tank once its tail has died. | **Partly landed**: SMALLDECAY skips the muted centre tank. General gating not built. | `THURSDAY_LIST.md` N17, `research\R14_play_cpu_tank_gating.md` | Low priority | 4 |
| 2.10 | Pre-delay control (ST-6) and wet ducking (ST-9) | — | **Superseded by Bloom** (Predelay is Bloom Part 1; ducking is Bloom's job) | `SOUND_TRICKS.md` | — | — |
| 2.11 | ⚠ CR2 accuracy gate as a standing test (ST-7) | Keep the CR2 measured-room comparison as a permanent test. No sound change. | Idea (accepted "yes" in SOUND_TRICKS, never scheduled) | `SOUND_TRICKS.md` ST-7, `sl2_loop\measure_cr2.json` | none | 3 |
| 2.12 | Source getting louder as it approaches the stand mics | Makeup currently cancels most of the change (closer = softer). D-PROX added a floor for sources near a *mic*; the *source-approach* question was never answered. Limiter still hits 4.08 dB at 0.3 m. | Open decision | `OPEN_FAULTS_2026-10-10.md`, `DECISION_MAKEUP_FREEZE_2026-10-10.md`, `srcdist\measure_srcdist.json` | Idle (6.8) | 2 |
| 2.13 | Proximity effect / min-distance floor | Bass lift and level floor for sources under 0.5 m from a mic. | **Landed** (PROX, 2026-10-13). Fig-8 values are theory only. | `DECISION_PROXIMITY_2026-10-12.md`, `prox\listen\` | — | — |
| 2.14 | Dead `mic_proximity` knob | A UI slider reaches `render()` but is never used (`render_pipeline.py` ~1685). | Leftover | `AUDIT_2026-10-17.md` §B | Wire or remove | 3 |
| 2.15 | Known Play/Render differences | Makeup `g` split (~0.5-0.8 dB with a room mic), Render-early per-axis cut missing in Play, centre early is a plain sum, early tap rounding, t13 early parity xfail (+3 dB), shared-tail coherence gate (P5) fails. | Documented and left on purpose | `AUDIT_2026-10-17.md` §B; HANDOVER FIX-B/PROX notes; `research_shared_fdn\` | — | 4 |
| 2.16 | Lean convolution mode (L6) | Convolve a rendered IR for many stacked instances (cheap plug-in mode). | Idea | `THURSDAY_LIST.md` L6, book ch 11 | Plug-in work | 4 |
| 2.17 | C migration (L4 / N12) | One C core for Play, Render and a plug-in. | Idea / old prompt | `THURSDAY_LIST.md` L4, N12; `C_MIGRATION_PLAN.md` (old) | Idle: before or after features | 4 |

## 3. Mics & colour

| # | Item | What it is | Status | Files | Blocking | Order |
|---|---|---|---|---|---|---|
| 3.1 | **U87 Ai as the default mics** (D-UI38) | Idle asked on 4 Oct for Neumann cardioids instead of SM57s. Landed 2026-10-23: a missing id is Neumann U87 Ai cardioid on L, C and R. Explicit SM57 stays Shure SM57. | Landed 2026-10-23. Listens in `roadmap/u87_listen/`. | `thursday_prompts\T05_u87_ab_render.md`, `research\R05_T5_T6_u87.md` | — | — |
| 3.2 | Off-axis tail colour | see Q3 | Queued | | | Q3 |
| 3.3 | Colour module | see Q4 | Queued | | | Q4 |
| 3.4 | Height-aware mic colour | Use 3-D polar data (e.g. DirPat) so mic colour changes with height/elevation. | Researched (rank 3); not queued | `MIC_CHARACTER_RESEARCH.md`, `DECISION_OFFAXIS_QUEUE_2026-10-18.md` "Not queued"; `mic_fitter_polar3d.tar.gz` on the Desktop | Needs a 3-D data source | 3 |
| 3.5 | ⚠ Multi-pattern measured presets | Let the pattern be dialled while staying in Measured mode (wishlist item 2b-c). | Idea | `research_ui_wishlist\REPORT.md` item 2b | Mic data | 3 |
| 3.6 | ⚠ AB omni / MS omni-mid fall back to "User defined" (audit Q3) | Measured omnis exist (DPA 4006, C414, U87, NT2-A) but those setups switch Colour away from Measured. | Open question, never answered | `ui_audit_1004\UI_AUDIT.md` Q3 | Idle | 3 |
| 3.7 | "Heavy curtain" material (audit Q4) | Keep the only curtain material? | Open question | `UI_AUDIT.md` Q4 | Idle | 4 |
| 3.8 | `apply_capsule_colour` dead code | Defined, no callers (`early_field.py` 1706). | Still dead. Q3 did not call it. | `DECISION_OFFAXIS_QUEUE` | Q3 | Q3 |
| 3.9 | Self-noise, separate transient model, Jiles-Atherton hysteresis | — | **Rejected** by the mic research ("not worth building") | `MIC_CHARACTER_RESEARCH.md` | — | — |
| 3.10 | Binaural gaps (head views, HRTF polar, rate notice) | Part of the old S6 session. | Parked | `THURSDAY_LIST.md` R4; `test_binaural_play_and_gaps.py` xfails | CPU, scatter | 3 |

## 4. Dynamics / Bloom

| # | Item | What it is | Status | Files | Blocking | Order |
|---|---|---|---|---|---|---|
| 4.1 | Bloom Parts 0-2 | see Q2 | Prompt written | | | Q2 |
| 4.2 | **Sustain (Bloom Part 3)** | While you're quiet, the room's decay stretches a bit, then settles back. Hard cap so it can never run away. | Decided in principle; explicitly **not built** in the Bloom run | `DECISION_BLOOM_2026-10-18.md`, `BLOOM_RUN` "Part 3" | Bloom landing; its own prompt | 2 |
| 4.3 | Swell Long and Talkback presets | Fairchild position 6 (very slow) and the SSL Listen Mic style. | Optional inside Bloom (built only if CPU fits) | `BLOOM_RUN` Part 2, `compressor_presets.json` | CPU gate | Q2 |
| 4.4 | Preset-driven Predelay | Each preset's suggested predelay (`bloom_defaults.predelay_ms`) is noted but not applied. | Idle's call later | `BLOOM_RUN` Part 2 | Idle | 3 |
| 4.5 | "Natural" name clash | The Mix page already has a "Natural" lock button; the Bloom preset is also "Natural". Step 0 is to suggest a new name. | Open | `BLOOM_RUN` Step 0 | Bloom Step 0 | Q2 |
| 4.6 | Research gaps | 1176 level curve (SPICE levels came out wrong) and the Distressor (no public schematic) are not modelled; a few values are marked estimate. | Researched with gaps | `bloom\COMPRESSOR_RESEARCH.md`, `bloom\spice\` | Data | 4 |

## 5. UI

| # | Item | What it is | Status | Files | Blocking | Order |
|---|---|---|---|---|---|---|
| 5.1 | T9b Mic-tab clean-up | B10 overlapping drag targets, B11 Combined labels, polish P2, P4, P10. | Listed, not started | `UI_AUDIT.md`, `OPEN_FAULTS_2026-10-10.md` queue | A prompt | 2 |
| 5.2 | Wall drag (T8b) | see 1.4 | | | | 2 |
| 5.3 | Surfaces / Polar / Space redesigns (D-UI32/33/34) | Locked "later"; mockups exist. Surfaces partly done via SL1's Room result panel. | Partly built | `prebuild\mockups\`, `research\R16`, `R17` | — | 3 |
| 5.4 | ⚠ **Polar "At speakers" view** (wishlist 6) | Show the polar pattern actually arriving at each speaker, not just each mic. Idle asked for it on 2 Oct. No "At speakers" code found in `static\js`. | Researched; **not built** | `research_ui_wishlist\REPORT.md` item 6, mock `m7_polar.png` | — | 3 |
| 5.5 | ⚠ **Save / load scenes, undo / redo, autosave** (L7) | Nothing persists; a reload loses everything. | Idea, never scheduled | `THURSDAY_LIST.md` L7 (AUDIT B1) | "do not start on a bare continue" | 2 |
| 5.6 | Master output meter + clip LED, numeric pan readouts (L8) | | Idea (pan readouts landed in T1) | `THURSDAY_LIST.md` L8 | pairs with S-OUT | 3 |
| 5.7 | Move "Advanced / Structure locks" off every tab (L9) | T10 kept `#panelAdvanced` on every tab. | Idea | `THURSDAY_LIST.md` L9 | — | 3 |
| 5.8 | Plain-words Polar banner (L10) | | Idea | `THURSDAY_LIST.md` L10 | — | 4 |
| 5.9 | Jagged top of the 3D polar stack (B12) | 8k/16k sheets render spiky. | Bug, needs investigation | `UI_AUDIT.md` B12 | — | 3 |
| 5.10 | Pattern controls placement conflict (audit Q6), Mic plane horizontal + "Tilt to source" (D-UI8 / N15, status unknown) | | Open questions | `UI_AUDIT.md` Q6, `THURSDAY_LIST.md` N15 | Idle | 3 |
| 5.11 | Speakers vs picture L/R can feel inverted | Parked in memory notes: "do not flip 3D to chase it". | Parked | project memory "Still parked" | — | 4 |
| 5.12 | Favicon 404 | `/static/favicon.svg` is linked but missing. | Tiny | HANDOVER FIX-A note | — | 4 |
| 5.13 | Idle's 2 Oct wishlist (radiation colours red→violet, mic graphs moving wrong way, link/mirror/3 mics, mixer, knobs, head control, 3D polar lean, bigger Source diagrams, Feedback vs Decay, Air 1-pole, Lattice/Paths zoom and merge, Mix box, Colour tab, Air on Surfaces) | | **Mostly landed** through S-UI1, S-UI2, S-MIX, T1-T10 (not re-checked one by one in the code). Leftovers: Auto level (2.7), Colour tab = post-EQ only (2.7), "At speakers" (5.4). | `Idle Hanz ideas 02-10-26.docx`, `research_ui_wishlist\REPORT.md` | — | — |

## 6. Open decisions awaiting Idle

| # | Decision | Options / recommendation | Where | Unblocks |
|---|---|---|---|---|
| 6.1 | **D-NR1-D-NR8 (non-rectangular rooms)** | 1 which presets first (rec: splayed control room, LEDE, non-parallel live room); 2 how the 32 echoes are picked (rec: per-order quota, by geometry only); 3 tank delays (rec: frozen per preset and source, from the stand); 4 Render-only first, Play later (rec: yes); 5 echo fade time (proposal 15 ms); 6 map new walls onto A-F, or a full N-wall Surfaces UI; 7 do the non-convex L-shape at all; 8 park the scattering-delay-network idea as research (rec: yes) | `nonrect\NONRECT_RESEARCH.md` §6 | 1.1 |
| 6.2 | Helmholtz Q | Physical model gives Q about 1-2 and a resonance 5-10 % lower, against the assumed Q 3. SL5 kept the formula (Q 3). Changes auto-treat plans, not goldens. | `prebuild\sl\README.md` finding 1; book ch 4, ch 6 | Idle, before any formula change |
| 6.3 | D-SL3: keep the per-axis cuts below 30 Hz? | Keep below 30 Hz (16/23 bands in target) or drop them all (15/23). The live code keeps below 30 Hz (`KEEP_CUT_BELOW_HZ` 30). | `prebuild\sl\README.md` finding 4; `SL6_auto_treat.md` | SL4-SL6 |
| 6.4 | SL4 double slope | Decided 2026-10-23: ship directional. PC EDT/T30 is still more than 0.15 below Flat at 2 kHz, 4 kHz and 8 kHz (xfail). A/B 3 and 4 stay ≤ 1 dB against room average. s′ stays 0.5. | `prebuild\sl\README.md` finding 5; `software\proof\sl4_directional_results.json` | done |
| 6.5 | Treatment also colours the early reflections in Surfaces mode | Render already folds treated octave alpha into the early cards and the injection. Flat stays on the posted cards. Left as-is in SL5. | `prebuild\sl\README.md` finding 3 | Idle, accept or not |
| 6.6 | Auto-treat when the target is longer than the room | It can only shorten a room, so it fits the bass shape only and leaves length to the decay lock. (I could not find a file using the word "brightening"; the nearest written items are this one and finding 2, "face-EQ boosts don't count, only cuts".) | `prebuild\sl\README.md` findings 2, 7 | SL6 |
| 6.7 | Speed of sound 343 vs 340 | Audio delays use 340; mode readouts, the physics target and the proximity shelf use 343. Unify, or keep as a 2011 lock. | book `STATUS.md` gaps; HANDOVER engine locks; memory "Engine locks" | consistency |
| 6.8 | Source approaching the stand mics: should it get louder? | Today makeup cancels it (closer is slightly softer). | `OPEN_FAULTS_2026-10-10.md` | 2.12 |
| 6.9 | Keep ROOMTONE at all? | Idle heard no difference. | `AUDIT_2026-10-17.md` A2 | 2.6 |
| 6.10 | S-OUT Auto level (D-UI11 / N2) and master headroom (N4) | Rec: Auto level on by default with an Off chip. | `THURSDAY_LIST.md` N2, N4 | 2.7 |
| 6.11 | D-INT (N6), face EQ kept when a material is picked (N8), C migration order (N12) | | `THURSDAY_LIST.md` | 2.8, 2.17 |
| 6.12 | ⚠ **TU-Berlin source presets private, BYU public (N13)** | Must be answered **before anything is shared publicly** (Ben, idlehanz.com). | `THURSDAY_LIST.md` N13 | 8.x |
| 6.13 | ⚠ Old 28 Sep leftovers (N16) | Confirm the 1.8 s decay by ear; trim direct/early (+1.61 dB); the K2 distance unit after 2011 captures. | `THURSDAY_LIST.md` N16, L3 | — |
| 6.14 | What may a preset chip touch? (fault F5) | Rule needed: should a chip ever move mics / room spots? | `OPEN_FAULTS_2026-10-10.md` F5 | F5 |
| 6.15 | Reflection selection (U9), audit Q3 / Q4 / Q6, direct level ST-4 / D22 | | sections 1, 3, 5 | — |
| 6.16 | Re-scope SL7a/SL7b after PHYSDEFAULT | What remains of the "one default switch" (Surfaces default? real materials?) now that the physics decay is default. U87 default landed 2026-10-23 (D-UI38). | 2.4 | 2.4 |
| 6.17 | Bloom: preset-driven Predelay; new name for the "Natural" preset | | 4.4, 4.5 | Bloom |

## 7. Open faults

| # | Fault | Status | Files | Next |
|---|---|---|---|---|
| F4 | Hall preset chip jumps in level when clicked | Not investigated (since 10 Oct) | `OPEN_FAULTS_2026-10-10.md` | Read-only look: makeup step with no ramp, or real level change? |
| F5 | Mics don't keep their position when a preset chip is clicked | Not investigated | same | Read-only look + rule (6.14) |
| F8 | T14 FDN level drifted −27.18 → −24.78 dB before SRCDIST, cause unknown | Not investigated | same | Read-only |
| F9 | Physics path decays ~20 % long from 500 Hz up, ~12 % short at 125 Hz | Closed 2026-10-19 (F9 NOTES). Measurement artefact. Ruler fixed. No sound change | `OPEN_FAULTS_2026-10-18.md` | Done |
| F10 | `test_a4_binaural_hides_dead_rows` | Known flake. The 400 ms wait before reading `#micHeroMeta` loses the race. One FULL miss on 2026-10-23, then two passes. Do not chase. | `software\tests\test_s_audit_ui.py` | Leave the wait |
| F11 | Five acceptance-suite failures since CLEANUP | Open; PHYSDEFAULT's gates now run that suite before and after and report each | same | After PHYSDEFAULT: decide test-stale vs code-stale (`p0_5` matters for every new default key) |
| F12 | 4.5×6×2.8: 926 Hz 1.366 s, 1623 Hz 1.172 s, longest 800 Hz–4 kHz band 1.552 s at 800 Hz | Open. The ~3.8 s figure was the hypot ruler | same | Report only |
| — | F9_DIAG option 2: fold ROOMTONE into the physics fit | Backlog for Idle. Not scheduled. Small rooms measure 12–20 % short at 125–500 Hz | `F9_DIAG_2026-10-19.md` | Listen before any lock |
| — | F9_DIAG option 3: dial 4 / 8 guard fallbacks | Backlog for Idle. Not scheduled. A few lines fall back to identity at dial 4 and 8 | same | Prototype before any lock |
| T11b | Movement forced off on CPU | Landed 2026-10-23. Knob live, default 0. Shared-off 100 was 1.876 ms | see 2.5 | Done |
| D7 / P-D7 | ⚠ Small-room Play 1 kHz decays −8.5 % vs dial; the PC re-measure (D21) **never ran** (only "REVIEW_T5_PD7 started" in the log, empty err file) | Open since 4 Oct | `thursday_prompts\P_D7_play_remeasure.md`, `research\R13_D5_D7.md` | Note: SMALLDECAY / PHYSDEFAULT change what "the dial" means for small rooms, so redo the question rather than the old command |
| — | 3×4×2.5 guitar clipping | **Resolved for listening**: AMBIENCE used the cleaned guitar and the limiter stayed off on every file | `ambience\listen\` | — |
| — | Roughly once-per-second Play click | Parked in memory notes (not the 1 s delay cap, not live-param zipper) | project memory | Re-check if Idle still hears it |
| — | Test hygiene | Many September xfail "not landed" probes hide real state; `*_draft.py` test copies; full suite ~30 min (a quick tier would help) | `AUDIT_2026-10-17.md` §D | Triage session (S) |
| — | Dead / legacy code | `tweak_app.py` stub panels, `fdn.py` 16-bit wav writer (L12), `loop_mix` unused, `polygonal_stub.py`, `fdn_stub` | `AUDIT_2026-10-17.md` §B | Tidy or label (S) |

## 8. Docs & sharing

| # | Item | What it is | Status | Files | Order |
|---|---|---|---|---|---|
| 8.1 | **Book update pass + PDF rebuild** | Chapters 1-8 drafted on 5 Oct; nothing yet about T7-PLACE, TLAW 1/r, SL1-3, SRCDIST, PROX, ROOMTONE, SMALLDECAY, AMBIENCE, PHYSDEFAULT, Bloom. Ch 6 half done; ch 9-12 stubs; `STATUS.md` dated 5 Oct. | Partly built, 2 weeks stale | `handoff_build_support_2\book\` (STATUS.md has the trigger table) | 2 |
| 8.2 | Handover to Ben Supper | Ch 12 lists what a handoff pack needs (book + clean HANDOVER). | Stub | `book\12_handover_to_ben.md` | 3 |
| 8.3 | ⚠ **idlehanz.com listen page** | Public page `idlehanz.com/tools/room-reverb/` has three ~78 MB WAVs from late September, so it is **far behind** today's sound. Play/Render labels were never confirmed; GitHub warned about file size. A static live player (wasm in the visitor's browser) is possible; the full desk is not. | Built (Sept), stale | local clone `C:\Users\IdleHanz\Projects\idlehanz.github.io`; project memory `idlehanz-github-io` | 3 (after 6.12) |
| 8.4 | ⚠ **Virtual speakers = virtual omni mics demo** (Ben Supper idea) | Blind A/B/C test built 7 Oct with a stand-in room model; no record that Idle ever scored it. Likely a separate future app. | Prototype exists | `demos\virtual_speaker_mics\` (README, blind_X/Y/Z, `BLIND_KEY_dont_peek.txt`), `book\research\virtual_speaker_mics_RESEARCH.md`, book ch 11 | 3 |
| 8.5 | Studio One plug-in / one shared room for many tracks | Each track a source in one room; design study exists. | Researched (design only) | `book\10_studio_one_shared_room.md`, `/workspace/build_support/research/studio_one_plugin/DESIGN.md` (box) | 4 |
| 8.6 | Reverb designer export / variants (3D delay, simple room, binaural) | | Researched (book ch 11) | `book\11_variants_and_export.md` | 4 |
| 8.7 | Stale entry docs | `START_HERE.md` and `NEXT_SESSION_PLAN.md` frozen at 9 Oct; HANDOVER is ~150 KB with many superseded pins and old "1/r² VERIFIED" lines; decision index appendix planned for the book. | Stale | `handoff_build_support_2\`, `HANDOVER.md` | 2 (small) |
| 8.8 | ⚠ Listening backlog (L13) | EQ-plan guitar before/after files and the S-AUDIT heights pairs were never listened to. Probably obsolete now. | Idle task | `eq_plan\measure\guitar\`, `research_ui_wishlist\s_audit\heights_research\` | 4 (or delete) |
| 8.9 | ⚠ Idle's site URL for the design language (L12) | Asked for once on 4 Oct, never given. | Idea | `THURSDAY_LIST.md` L12 | 4 |
| 8.10 | 2011 captures in Reaktor (L3) | 60-90 min Idle task; settles loop timing, two-stage tail, K2 unit. | Idle task | `build_support/research/reference_2011/CAPTURE_GUIDE.md` | 4 |

---

## 9. Looks forgotten (mentioned, never followed up)
1. **U87 default mics** (3.1): landed 2026-10-23 (D-UI38). Listens in `roadmap/u87_listen/`.
2. **Save / load scenes, undo, autosave** (5.5): nothing is kept across a reload.
3. **Movement re-bench** (2.5): the CPU problem that parked it may be gone.
4. **P-D7 small-room re-measure** (F-D7): never run.
5. **Polar "At speakers" view** (5.4): asked for 2 Oct, not in the code.
6. **SL7 re-scope** (2.4 / 6.16): the plan still says "one default switch", but defaults are now being switched one by one.
7. **Virtual-speaker demo** never scored (8.4); **idlehanz.com page** two months behind (8.3); **TU-Berlin licence question** must come before either (6.12).
8. Smaller: reflection selection U9 (1.5), CR2 standing gate (2.11), multi-pattern presets (3.5), audit Q3/Q4/Q6, listening backlog (8.8), site URL (8.9), N16 leftovers.

## 10. Suggested order after the queue (PHYSDEFAULT → BLOOM → off-axis tail colour → Colour module)
1. **F9** closed 2026-10-19 (F9 NOTES). The +20% / −12% row was the hypot ruler, not a section-fit bias. Proper boot T20 is within about 1% from 125 Hz to 2 kHz. No sound change.
2. **F4 + F5 preset-chip investigation** (read-only, one session) and Idle's rule for what a chip may touch: these are bugs Idle reported himself on 10 Oct.
3. **Movement re-bench** with the tank skip in place; if it fits under 2.40 ms, a small session to un-force it and listen.
4. **Non-rectangular rooms stage 1** (Render-only, three convex presets, Box bit-exact) once Idle answers D-NR1-D-NR8. Stage 2 is A/B renders for him.
5. **Defaults re-scope**: one review that decides what is left of SL4-SL7b. The U87 default landed 2026-10-23 (D-UI38).
Then: Sustain (Bloom Part 3), save/load scenes, T8b wall drag + T9b, S-OUT auto level, book update pass.

## Count
99 rows in total: 4 queue items, 7 room-geometry, 17 sound/DSP, 10 mics/colour, 6 dynamics, 13 UI, 17 open decisions, 15 fault rows, 10 docs/sharing. About 11 of those rows are landed / superseded / rejected and are kept only so nobody chases them again. The two added rows are F9_DIAG options 2 and 3. F9 itself is closed.

| 98 | Return-EQ in the Colour module (2026-10-19, Idle) | Model the curve SHAPES only (Pultec EQP-1A boost/cut interaction, MEQ-5, 1073 shelves/HPF, Helios 69, Massive Passive) from the UAD plugins via the pedalboard rig in C:\Users\IdleHanz\uad_measure (measure magnitude/phase vs knob). Use as an optional tail/return EQ inside the Colour module (after the off-axis tail colour). Not a full EQ plugin. | Parked: do with Colour module | roadmap\bloom\uad\, mic_character\ |
| 99 | Per-room k for physics decay (2026-10-19, Idle) | The dial sets the 500 Hz / 1 kHz mean T60 in every room with physics on; physics shapes only lows and highs. Fixes F14 (hall at dial 8 rang about 37 s). Re-baselines `test_s4b_long_decay_no_runaway` as a slope check and the line-0 comb limit to about 0.23. Open: solve on actual cards (default) or default walls; UI for unreachable dials. | Landed 2026-10-20. Hall dial 8 mid went from about 36 s at 500 Hz to about 8.3 s. Boot k unchanged. Open questions still open: solve on actual cards (this is what shipped) or default walls; the page does not show the max reachable dial. | roadmap\DECISION_PER_ROOM_K_2026-10-19.md, thursday_prompts\PERROOMK_RUN_2026-10-19.md |

## 2026-10-20: Character control, digital to analogue / room to chamber (PARKED, wanted)
Idle wants one Character control on the main page that moves between a clean, natural placement room and a warm, lush, analogue reverb chamber. Idle turned down a 2011-to-Natural dial. It would drive three places at once: Surfaces (harder, smoother walls, with the high frequencies dying away more slowly at the chamber end), the engine (tail density, and Movement, which is now the Room knob, default 0), and the amount of BLOOM. Each part can still be set by hand. Status: not started, after BLOOM.

## 2026-10-22: D-NR1-D-NR8 answered (Idle)
D-NR1-5 and D-NR8: take the recommendations. D-NR7: no L-shape (parked). D-NR6: a full Surfaces page showing every wall, with left and right walls mirrored (not a mapping onto A-F). Stage 1 of non-rectangular rooms (1.1) is unblocked.

## 2026-10-22: Play vs Render quality (Idle)
Play is a rough preview and must fit 2.40 ms; it may use lower BLOOM/preamp oversampling. Render is extra high quality with no CPU ceiling: heavier oversampling and anti-aliasing belong there. Follow-up idea: in Render, chase the UAD alias levels with higher oversampling.

## 2026-10-22: BLOOM landed, two leftovers
The page has no Bloom panel, so browser Play stays bloom-off until something posts the keys. `pack_room.js` already emits sections 10–12.
610-A at 0 dBFS has a known 9 kHz spike (untrimmed H1 into the flux cubic). It stays 8x. Do not fix it in a Bloom run.

2026-10-22 process review, not investigated: full pytest deletes the pinned 86 MB render stamp `software\renders\out_20261013_115900.wav`; backups should leave `software\renders\*.wav` out.

2026-10-22: Mix page Bloom panel landed, default off. `HANDOVER.md` still says there is no Bloom panel and still says `app.js?v=64`.
2026-10-22: Bloom pre-drive slider stops at 12 dB. The engine reads `pre_drive_db` with no clamp.
2026-10-22: `listen_report.json` records Room Crush amount 100 and glue_colour false. It does not record bloom_colour, so the panel posts the engine default false.

- 2026-10-22 ROUTING (Idle): Neve/610-A preamps go on the mics (or at least before the compressors); the room mic can take a different compressor from the mic array; studio-style routing with per-bus inserts (array bus, room-mic bus, master) and the preamp before the comp on each. This is an audio-law change, so it gets its own run.
- 2026-10-22 ROUTING DECISION (Idle): full routing with all three buses (array, room mic, master), each with preamp then comp. R1 is Render only plus the panel; R2 is Play, lean within 2.40 ms. The default scene stays bit-exact.
- 2026-10-22: the Routing panel does not post predelay, attack, release, bloom colour, or glue colour. A saved scene keeps the master preset and amount only.
- 2026-10-22: routing inserts run only on the 32-line driven FDN path.
- 2026-10-22: a strip with both a preamp and a compressor is two bloom_dsp calls, preamp then compressor. Bloom's own call runs the compressor then the preamp. The old panel never posted both.
- 2026-10-22: the routing listen (room bus 610-A at 6 dB) shows the known 9 kHz spike, 15.6 dB above the 7–11 kHz median. Not fixed. Needs Idle's OK.
- 2026-10-23 FAULT (Idle): the routing listen sounds very distorted, as if the gain is too high, and in the app the Routing panel inserts don't sound plugged in. Diagnose before any fix.
- 2026-10-23: routing listen guitar (first 3 s) crest 0.26 dB, 93% of samples over 0.95. Bloom room_crush.wav crest 24.9 dB, limiter samples 0. Next run is ROUTING_BRICK_RUN.md (one render, six peaks). Do not chase the 9 kHz spike in that run.
- 2026-10-23: Routing panel in Play posts the master strip only, and a comp with Amount still 0 posts nothing. Array and room are Render only (R2). Waiting on which strip Idle moved.
- 2026-10-23 FAULT B (Idle): in Play, both the Array/Room strips and the Master strip sound unplugged. Array/Room in Play is expected until R2; the Master strip in Play is a real fault (suspect Amount 0 posts no keys, or the master keys not reaching the worklet). Wiring fix per rule 18, as its own run after the brick.
- 2026-10-23 BRICK STOP: room bus after the 610 preamp peaked 301186 from 0.246 (+122 dB). Array after the fold stayed 0.647. Limiter cut 92.8 dB. A 0.246 probe with the flux coefficient at 0 peaked 5.23, so the cubic is the blow-up. No trim. Next run is ROUTING_MASTER_PLAY_RUN.md. Flux trim waits on Idle.
- 2026-10-23 CAUSE A: the routing distortion is the 610-A flux cubic in the room-bus preamp (0.246 to 301186, +122 dB); with phi_c 0 the peak is 5.23, still about +26 dB hot. CAUSE B: choosing a Master comp preset leaves Amount at 0, so nothing posts (fix in ROUTING_MASTER_PLAY_RUN.md). The 610-A fix awaits Idle's OK.
- 2026-10-23: Master comp menu from Off onto a preset with Amount 0 now sets Amount to 100 (`armMaster`). A stored Amount 0 still posts nothing. Array and room unchanged. `app.js?v=67`, `routing_scene.js?v=2`.
- 2026-10-23 DECISION (Idle): leave the 610-A as is for now; no flux or trim fix, and runs must not touch it. Avoid 610-A in listens.
- 2026-10-23 FAULT (Idle): the Master strip is still silent in Play after the arm fix. Likely cause: bindRouting onRoute in app.js calls syncUI() but never scheduleLiveParams(), so routing changes never reach the live engine (other controls call both). Wiring fix, rule 18.
- 2026-10-23 Idle: routing preamps and compressors are shelved. Preamps distort badly and the compressors don't sound nice. Leave the code as is, default off, and no runs touch it until Idle asks.
- 2026-10-23 BACKLOG B: floor wall, corner, and ceiling drag call the existing `drag_model.js` functions. Save/load was already landed. Mic-tab B10/B11 (T9b) was not this run. `room_editor.js?v=20`.
- 2026-10-24: no-impulse S1P2 designer and `render()` disagree on the R bus for the same auto-treat scene (9.95 with 1 guard, against 10.22 with 0). Not chased.
- 2026-10-24: `live_fdn.js` `pushParams` does not copy `offaxis_tail`, so a Play message omits section 14. The wasm applies the 45 floats when they are on the message. Fixed 2026-10-24: `pushParams` copies the 45 floats. The tail test posts that message.
