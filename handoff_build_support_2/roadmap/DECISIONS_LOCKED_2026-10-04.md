# DECISIONS LOCKED, 4 Oct 2026 (Idle): read this first

Idle accepted all 14 recommendations from the 16:32 research report at **16:43 BST, 4 Oct 2026**.
- Numbers: D-UI27–31 and D1–D17 were already used, so these take **D18–D24** (sound/engine) and **D-UI32–D-UI38** (UI).
- Nothing below is merged yet. Each one names the Thursday session that lands it (`thursday_prompts/`).
- The PC `software\` was **not** touched. Tags: **VERIFIED** = measured or tested on the box (build 51 copy); **ASSUMED** = judgement.

| # | Was | Decision (locked) | Session | Goldens |
|---|---|---|---|---|
| **D18** | Q2 (R03) | MS presets decode at **unity** (S:M = 1, virtual pair ±63°) with a **−3 dB trim on M and S** (M gain = S gain = 0.708). Old saved scenes keep their stored levels. `ms_presets.js` `LEVELS.unity_trim` (VERIFIED by unit test) | T3b | MS references only |
| **D19** | Q-MS-DIRECT (R18) | One source: when any strip folds with opposite signs into L and R (route s), the direct sound uses the pattern spikes (`direct_capsule_spikes`, hottest capsule = 1) in **Render and Play** (`buses[ch].direct_gain`). Other setups unchanged until D22. Box prototype: 3 strict xfails flip, selfcheck unchanged (VERIFIED) | T3b | MS references only; main golden NO |
| **D20** | N18 (R15) | **ORTF = C off by default**; new preset **"ORTF + C"** = today's sound (C at 0 dB, 477 fold). Old scenes keep their stored C | T4b | **YES (main golden)** |
| **D21** | D7 / N10 (R13) | **Re-measure Play on the PC first** (post-T4 tree, `--slow` small_lock08). If Play ≈ Render (≈ −4 % at 1 kHz): accept and widen the small-room tolerance. If Play is still ≈ −8 %: a live-tank bug, an M session later. Report to Idle before any change | P-D7 (PC step) | none (measure only) |
| **D22** | D5 / N9 (R13) | Realism ships as opt-in **"Physical"** options (1/r law, full first-order set, direct pattern for all setups); 2011 stays default | later (not Thursday) | NO by default |
| **D23** | N17 (R14) | Gate the tank after the tail dies (−96 dB), restart from zero with a ramp. **Low priority** | later | NO (must be bit-exact while the tail lives) |
| **D24** | D-SCATTER (R12) | Shared velvet-noise smear, Play = Render, **default off**; measure CPU first (~0.1 ms headroom) | later (S5/S6) | NO (off) |
| **D-UI32** | D-SURF1–4 (R17) | Surfaces: per-face tone = Colour per face; real materials only; Air moves into Surfaces; the decay dial keeps the tail | later redesign (mockup `prebuild/app_copy_files/mockups/surfaces.html`) | NO (UI) |
| **D-UI33** | D-POLAR1–2 (R17) | Polar: 2-D small multiples; C follows the desk | later redesign (`polar.html`) | NO |
| **D-UI34** | D-SPACE (R16) | Space: plan + heard/blocked mirror sources + paths + arrivals for angled rooms; lattice stays for rectangles | later redesign (`space.html`) | NO |
| **D-UI35** | D-ROOMSIZE (R09) | Room size on the Room tab only, plus a read-only chip elsewhere | T10 | NO |
| **D-UI36** | D-NAME / Solo (R02) | Array/Room → **"On stand" / "Room mic"**; mic-strip Solo = **solo-in-place** | T2 | NO |
| **D-UI37** | Q5 + D-DRAG (R07) | One **Mirror / Linked / Split** control (replaces the Split tick and yaw chips); wall drag uses **"stop"** (not push) | T7 (control), T8 (drag) | NO |
| **D-UI38** | D-UI30 gate (R05) | U87 becomes the default **only after Idle's written OK on the T5 A/B**. Confirms the D-UI30 condition | T6 (gated) | **YES** |

## Locked 4 Oct 2026, 20:37 BST: Surfaces in the loop (Idle listened: "sounds good, certainly a lot better than flat")
Source: `sound_tricks/SURFACES_IN_LOOP.md` §9 (recommendations accepted as written). Sessions are in `thursday_prompts/SL1–SL6, SL7a, SL7b`, after T11. Nothing is merged yet. SOUND_TRICKS ST-1–ST-10 stay **open**.

| # | Decision (locked) | Session | Goldens |
|---|---|---|---|
| **D-SL1** | Surfaces ships as an **opt-in** Decay mode (Flat (2011) stays default); it becomes the default only with the SL7b golden re-baseline | SL2–SL6; SL7b (gated) | NO until SL7b |
| **D-SL2** | **Directional** per-line decay (faces each image path hits), scattered share s′ ≥ 0.5; room average is the fallback | SL4 | NO |
| **D-SL3** | In Surfaces mode the 2011 per-axis in-loop cuts are **replaced** by materials/panels (the Play slot is reused); engine cuts stay only for 21–29 Hz modes | SL2, SL3 | NO |
| **D-SL4** | **One** Render calibration pass on T20 (clamp 0.6–1.6); Play uses the Render-designed coefficients | SL4 | NO |
| **D-SL5** | Auto-treat **suggests** editable rows; ≤ 4 tuned panels (shared with EQ_PLAN's 4); broadband axis-balanced | SL6 | NO |
| **D-SL6** | "Room shell" membrane row (30 % of walls, 90 Hz, Q 1, ASSUMED values) **on by default in Surfaces mode**, removable | SL5; default in SL7b | NO until SL7b |
| **D-SL7** | **S1P2 (3 biquads/line) everywhere**, Render = Play; GEQ revisited only if listening asks | SL2, SL3 | NO |
| **D-SL8** | **Real default materials** ("plaster + parquet", D-EQ / N7) together with D-SL6: library set in SL5, default switch in SL7b | SL5, SL7b (gated) | **YES in SL7b** |
| **D-SL9** | Auto-treat target = dial, plus an **"EBU control room"** preset with per-band pass/fail | SL6 | NO |

## Locked 4 Oct 2026, 20:40–20:41 BST: one default switch (Idle)
| # | Decision (locked) | Session | Goldens |
|---|---|---|---|
| **ST-1** | Natural decay (air) in the loop, **on by default** (the default Decay = Surfaces, which includes air), with "Flat (2011)" selectable; a "Natural (air)" mode (air only) is also selectable | SL7a (mode), SL7b (default) | YES in SL7b |
| **ST-2** | Fold the per-axis cut loss into the fit so the bass decays to the dial (Natural mode); in Surfaces mode D-SL3 already replaces the cuts | SL7a | NO (mode); YES via SL7b |
| **N11 / D4** | Frequency-dependent decay is the **default**; Flat (2011) is the option | SL7b | YES |
| **D-SL10** | **One** re-recording session switches Surfaces + natural decay + U87 at once. Flat (2011) stays a selectable mode, and its 2011 references are kept as a **separate frozen parity test** (`tests/refs_flat2011/`, bit-exact with a legacy profile). Split: SL7a prep (no golden change) + SL7b "Default switch" (gated, all-or-nothing) | SL7a, SL7b | YES in SL7b only |
| **D-UI30 / D-UI38 (amended)** | The U87 default switch moves from T6 into SL7b. The gate is now Idle's written OK on the **SL7a final A/B** (today / Natural+U87 / Surfaces+U87 / Surfaces+SM57). T5 stays as an early listen. **T6 is removed** from the run order | SL7b | YES |
| **D-SL1 (amended)** | Surfaces becomes the default in SL7b (was SL7) | SL7b | YES |

## HANDOVER block (Build pastes this into `software\docs\HANDOVER.md` in the first Thursday session)

```
### Decisions locked 4 Oct 2026 16:43 BST (Idle)
D18 MS unity decode, -3 dB on M and S (T3b). D19 MS direct uses pattern spikes, Render + Play (T3b).
D20 ORTF C off by default + "ORTF + C" preset, main golden regenerated (T4b). D21 D7: re-measure Play
on the PC, then accept/widen or fix (report first). D22 Physical realism opt-in (later). D23 tank gating
(later, low). D24 velvet smear default off (later). D-UI32 Surfaces, D-UI33 Polar, D-UI34 Space redesigns
(later, mockups in roadmap/prebuild/mockups). D-UI35 Room size on Room only + chip (T10). D-UI36 "On stand"/
"Room mic", mic solo-in-place (T2). D-UI37 Mirror/Linked/Split control (T7), wall drag "stop" (T8).
D-UI38 U87 default only after Idle's OK (amended 20:40: on the SL7a final A/B; T6 merged into SL7b).
Golden-changing sessions: T3b (MS refs only), T4 (EQ-1a), T4b (ORTF C off), SL7b (default switch; T6 merged). Each is its only change.
### Decisions locked 4 Oct 2026 20:37 BST (Idle): Surfaces in the loop
D-SL1 Surfaces = opt-in Decay mode, Flat (2011) default until SL7b. D-SL2 directional per-line decay, s' >= 0.5.
D-SL3 per-axis cuts replaced by materials/panels in Surfaces mode. D-SL4 one Render calibration pass on T20.
D-SL5 Auto-treat suggests rows (<= 4 tuned panels). D-SL6 room-shell row on in Surfaces mode. D-SL7 3 biquads
per line, Render = Play. D-SL8 real default materials (switch in SL7b). D-SL9 dial target + EBU preset.
Sessions SL1-SL6 keep the default golden bit-exact; SL7b (gated on Idle's OK; T6 merged) is the only golden change.
### Locked 4 Oct 2026 20:40-20:41 BST (Idle): one default switch
ST-1 natural decay (air) in the loop on by default; ST-2 cut loss folded into the fit (Natural mode); N11/D4 frequency-
dependent decay default. D-SL10: SL7a prep (Natural mode, frozen Flat 2011 parity suite tests/refs_flat2011, default
flags unflipped, final A/B; no golden change) + SL7b "Default switch" (Surfaces + natural decay + U87 in ONE re-record,
gated on Idle's written OK on the SL7a A/B, all-or-nothing). T6 merged into SL7b (D-UI30/D-UI38 amended).
Flat (2011) and Natural (air) stay selectable; the 2011 references stay as the Flat parity test.
```

---
## Answers locked by Idle, Fri 9 Oct 2026 09:10 BST (from the run-plan review)
- **D-FLAT-2026 (SL2/SL7a):** "Flat (2011)" = Surfaces hook off, same cards, **Smooth still on**, so it matches today's default golden (post-T4c, render sha1 7668100a...). Do not freeze the old build-51 flat proof (2d7bcb72..., Smooth off).
- **T10 / UI_AUDIT P15:** default each setup to its live mics. ORTF keeps C off (D20 stands). Never tick C on ORTF.
- **D21 amended (P-D7):** if Play is still about -8 % off Render in small rooms, report the numbers to Idle as a finding. Do not call it a live-tank bug automatically; Idle decides. (The -8 % was measured before Smooth went on.)
