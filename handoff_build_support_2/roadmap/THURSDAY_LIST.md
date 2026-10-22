# Thursday fix list: 2011 Room Reverb (Build usage resets Thu 8 Oct 2026)

Compiled 4 Oct 2026, 12:05 BST, on the box; corrected at 12:10 BST (S-AUDIT closed, D-UI10/12 applied, fdn.py checked). Updated 14:20 BST: Idle's knob note (U1) and the UI audit pointer in §4. Updated 14:55 BST: Idle's 14:47 reply as U2–U10 in §4 (audit pointer no longer numbered). Updated 15:15 BST: D-UI29/30/31 locked (Idle 15:06) and the whole list sorted into Thursday Build sessions (§5). Updated 20:45 BST: D-SL1–9 locked (Idle 20:37) and Surfaces-in-the-loop sessions SL1–SL7 added after T11 (§5). Updated 20:50 BST: ST-1, ST-2, N11 and D-SL10 locked (Idle 20:40–20:41). There is now ONE default switch: SL7a prep + gated SL7b. T6 is merged into SL7b.

**Sources:**
- `BIG_JOBS_ROADMAP_2026-10-01.md` (box copy, 3 Oct 20:38)
- `research_ui_wishlist/REPORT.md` §7/§8
- `AUDIT_1852.md`
- `roadmap/eq_plan/EQ_PLAN.md` v3.2 and the EQ1a/EQ1b prompts
- `roadmap/s5_surf_1010/S5_CPU_DECISION.md`
- The HANDOVER S-AUDIT section (read on the PC at 10:45)
- The HANDOVER S-MIX section (box copy, 06:16)

**Gaps:** the PC was offline at 12:00, so `S_MIX_REPORT.md` was not read directly. RecallMemory is not available to this worker. Items that came only from memory topics may be missing; Idle can add them under "Idle's UI notes".

**Key:**
- Size: S ≤ ½ session, M ≈ 1 session, L = several sessions.
- Status: **ready prompt** / **needs decision** / **idea**.

**Done since 3 Oct (for reference):** S-MIX, D-MIX-J and **S-AUDIT, CLOSED**: A1–A12 + B1–B6 all landed (24-bit Render, Render length, the shared limiter, ramps, Mono-C, H-1 heights), wasm 6ebecc333b50, WORKLET_VER 51. B3 was answered: Idle accepted option A (D-AUD-3). The Render golden is `ebd77c3b599e80a037f4a3c552c93f6e37343d1b` (HANDOVER and GOLDEN_META). S-UI2 also applied D-UI10, D-UI12, D-UI19 and D-UI20.

**Locked 4 Oct 2026, 15:06 BST (Idle).** D-UI27 and D-UI28 were already used on 3 Oct (S-UI2), so these are the next free numbers:
- **D-UI29 (MS presets, U8):** ship (a) fig-8 S + omni M, (b) fig-8 S + cardioid M and (c) two back-to-back cardioids as S + omni/cardioid M. **Default MS = (b): U87 Ai Bidirect S + U87 Ai Cardioid M.** (d) one split-phased cardioid is dropped, or shown only as a labelled effect ("not MS"). This also answers audit Q1 (S auto-picks U87 Ai Bidirect).
- **D-UI30 (default mics, U3):** U87 Ai Cardioid on L, C and R instead of SM57. **An A/B render goes to Idle first** (session T5); the switch happens only after his OK (since 20:40: in SL7b, gated on the SL7a final A/B; T6 merged).
- **D-UI31 (mixer, U7):** the same L/R buttons with phase invert on every mic strip (truth table in U7). **L+R = "both" when the strip is the Mid of an MS pair**, otherwise L+R = pan under the locked linear law (D-UI4). Trim becomes a text box; the mic strips get Solo.


**Locked 4 Oct 2026, 16:43 BST (Idle accepted all 14 recommendations).** Full table and the HANDOVER block: `roadmap/DECISIONS_LOCKED_2026-10-04.md`.
- **D18 (Q2):** MS unity decode, −3 dB on M and S (T3b; MS references only).
- **D19 (Q-MS-DIRECT, R18):** MS direct uses the pattern spikes, Render + Play (T3b; MS references only; ORTF bit-exact, prototype VERIFIED).
- **D20 (N18):** ORTF C off by default + "ORTF + C" preset (T4b; **main golden YES**).
- **D21 (N10/D7):** re-measure Play on the PC after T4, then accept/widen or fix (P-D7; report first).
- **D22 (N9/D5):** "Physical" realism as opt-in options; 2011 default (later). **D23 (N17):** tank gating after the tail dies, low priority (later). **D24 (D-SCATTER):** velvet smear, default off, CPU first (later).
- **D-UI32/33/34:** Surfaces / Polar / Space redesigns as in R16/R17 and `prebuild/mockups` (later sessions). **D-UI35:** Room size on Room only + chip (T10). **D-UI36:** "On stand"/"Room mic", mic solo-in-place (T2). **D-UI37:** one Mirror/Linked/Split control (T7), wall drag "stop" (T8). **D-UI38:** U87 default only after Idle's OK on the T5 A/B (T6). *Amended 20:40: the gate is the SL7a final A/B, and the switch is in SL7b.*
**Locked 4 Oct 2026, 20:37 BST (Idle, after the SURFACES_IN_LOOP A/B: "sounds good, certainly a lot better than flat").** Full table: `roadmap/DECISIONS_LOCKED_2026-10-04.md`.
- **D-SL1–9:**
  - Surfaces is an opt-in Decay mode, and the default stays Flat (2011) until gated SL7 (D-SL1).
  - Directional per-line decay with s′ ≥ 0.5 (D-SL2).
  - The per-axis cuts are replaced by materials and panels in Surfaces mode (D-SL3).
  - One T20 calibration pass on Render (D-SL4).
  - Auto-treat suggests rows only (D-SL5).
  - The room-shell row is on in Surfaces mode (D-SL6).
  - 3 biquads per line, Render = Play (D-SL7).
  - Real default materials, switched in SL7 (D-SL8; this answers **N7** for Surfaces).
  - Dial target plus an EBU preset (D-SL9).
- Sessions SL1–SL6, SL7a and SL7b are in `roadmap/thursday_prompts/`.

**Locked 4 Oct 2026, 20:40–20:41 BST (Idle).** Full table: `roadmap/DECISIONS_LOCKED_2026-10-04.md`.
- **ST-1:** natural decay (air) in the loop, on by default.
- **ST-2:** the per-axis cut loss is folded into the fit (Natural mode).
- **N11/D4:** frequency-dependent decay is the default.
- **D-SL10:** **one** re-record switches Surfaces + natural decay + U87 together.
  - Flat (2011) and Natural (air) stay selectable.
  - The 2011 references become a frozen Flat parity test (`tests/refs_flat2011/`).
  - Split: **SL7a** prep (no golden change, produces the final A/B) and **SL7b** "Default switch" (gated on Idle's written OK on that A/B, all-or-nothing).
- **T6 is merged into SL7b** (D-UI30/D-UI38 amended). T5 stays as an early listen.
- ST-3–ST-10 stay open.

---

## 1. Ready to paste

| # | Item (plain words) | Status | Size | Depends on |
|---|---|---|---|---|
| R1 | **EQ-1a "Smooth":** cap the tail diffusers at 0.7 (default ON), with a decay correction so T30 stays within 5 %. Off = today, bit-exact. Prompt `roadmap/eq_plan/EQ1a_PROMPT.md` | **ready to paste now** (new window, high effort; LOCKED 4 Oct 10:13) | M | — (S-AUDIT is closed) |
| R2 | **EQ-1b "Movement":** a tail delay-modulation knob on the Room tab, default 0 (0 → mod10 at 50 % → mod15 at 100 %). Render runs the dry signal through the loop when Movement > 0. Prompt `EQ1b_PROMPT.md` | ready prompt (LOCKED) | M–L (Render-through-loop is the big part) | R1 landed (its baseline) |
| R4 | **S6 Scatter, Play half + binaural UI gaps** (J4 Play half, head views, HRTF polar, Floor rotate handle, rate notice). Roadmap §5 "S6" | ready prompt (needs rebasing on the post-S-AUDIT tree) | M | the S5 scatter Render half (B2 below) should land first; CPU headroom |

## 2. Needs a decision

| # | Item | Status | Size | Depends on |
|---|---|---|---|---|
| N2 | **S-OUT Auto level (D-UI11):** never formally answered. Recommendation: option A, on by default, with an Off chip. Prompt is in REPORT §7 "S-OUT" (needs a rebase) | needs decision | M | EQ-1a/1b (level moves) |
| N3 | **S-OUT Output EQ (D-UI24 = A, LOCKED):** low shelf / peak / high shelf (plus low/high cut, D-EQ) on a Mix-tab Output strip; flat = bit-exact. Builds with N2 | ready once N2 is answered | M (with N2) | N2 |
| N4 | **Master headroom:** the golden scene peaks at 1.142 and is now soft-limited (D-AUD-3 = A), and hot mixes hit the limiter. A fixed master trim (about −1.6 dB), or leave it to Auto level? | needs decision | S | N2 |
| N5 | **Resonance control:** in-loop cuts with dB ∝ delay (Jot), Mäkivirta target, at most 4 resonances (CPU), plus a Surfaces Decay view. D-RES-3/4: amount 50 %, Auto after an A/B, Q 1–8 | needs decision (main decisions 1/2/4 in EQ_PLAN §6) | L | R1, R2 (detect on the modulated tail) |
| N6 | **D-INT:** Play's linear interpolation loses HF at 44.1 kHz (10 kHz T60 about 0.63 s, computed). Recommendation: round delays to whole samples at the device rate | needs decision | S | R2 (touches the same reads) |
| N7 | **LOCKED D-SL8 (20:37): real "plaster + parquet" default, switched in gated SL7 with the golden re-baseline.** **Default materials (D-EQ):** real plaster/parquet instead of the "plaster-ish" 0.05 → 0.22 card. Changes the default sound | locked → SL5 (library) + SL7 (default) | S–M | SL5; Idle OK for SL7 |
| N8 | **Face EQ kept when picking a material:** today picking a material zeroes the EQ (`colour_surfaces.js` about 1079–1081) | needs decision (quiet behaviour change) | S | — |
| N9 | **LOCKED D22 (opt-in Physical, later).** **D5:** physical level law plus the full first-order image set as options, 2011 table stays default. Gates S8 (J11 realism) | needs decision | — | 2011 captures help |
| N10 | **LOCKED D21 (re-measure Play on the PC first: P-D7).** **D7 small room:** 1 kHz decays 0.732 s against 0.8 s (−8.5 %; the long-standing `--slow` fail). Accept, or treat it as a bug? | needs decision | S (if accepted) / M (if fixed) | — |
| N11 | **LOCKED 20:40 (with ST-1): frequency-dependent decay is the default, and Flat (2011) is the option.** **D4:** frequency-dependent decay default on, or the 2011 flat decay as default? | locked → SL7a (Natural mode) + SL7b (default) | S | Idle OK for SL7b |
| N12 | **D2:** C migration before or after the features? Roadmap order says after | needs decision | — | — |
| N13 | **D1:** keep the TU-Berlin source presets private and ship BYU publicly (recommended) | needs decision | S | before any public release |
| N14 | **Unconfirmed UI defaults (ASSUMED):** the Movement mapping (50 % = mod10 midpoint) and the Smooth switch placement (next to Decay on Room) | needs a quick yes | S | before or with R1/R2 |
| N15 | **D-UI8:** Mic plane horizontal with a "Tilt to source" chip (recommended yes). Status **unknown**. D-UI10 (Feedback merge) and D-UI12 (Air 1-pole parity-only) were applied in S-UI2 | needs decision / check | S | — |
| N16 | **Still open from 28 Sep:** confirm the 1.8 s decay by ear; trim direct/early (whole mix +1.61 dB); compensate air_lp 0; the K2 distance unit (after captures) | needs decision | S each | captures (K2) |
| N17 | **LOCKED D23 (gate after the tail dies, later).** **Play CPU with the FDN fader at 0:** 2.17 ms (+84 % vs 1.18 ms before S-AUDIT), because the tank keeps running to keep the tail for unmute. Still under 2.40. Options: keep; or skip the tank after the tail has died while muted (needs a re-prime rule) | needs decision | S | — |
| N18 | **LOCKED D20 (C off + "ORTF + C", session T4b, golden YES).** **AUDIT B6:** ORTF includes the C mic at 0 dB by default (the 2011 "477 fold"). Intended? | needs a quick yes/no | S | — |

## 3. Bigger later

| # | Item | Status | Size | Depends on |
|---|---|---|---|---|
| L1 | **Scatter (J4, Render half; t06 pending) and smear:** rough walls smear each reflection; the early field is too sparse (Hall echo density 0.02–0.09). S5 items 2–3, never started | ready-ish prompt in roadmap §5 S5 (needs a rebase) | L (1.5 sessions with S6) | CPU headroom (2.226 / 2.40 ms used); EQ CPU budget |
| L2 | **S8 realism fixes (J11):** t=0 pre-echo, optional physical 1/r law, missing back-wall image, c from temperature, DRR calibration | prompt in roadmap §5 "S8" | M | N9 (D5) |
| L3 | **2011 captures in Reaktor** (`build_support/research/reference_2011/CAPTURE_GUIDE.md`, 60–90 min): loop timing, two-stage tail, K2, J11 | Idle task | S (Idle's time) | — |
| L4 | **S9–S11 C migration (J2):** one C core for Play, Render and the plug-in (`C_MIGRATION_PLAN.md` §5) | prompt in roadmap §5 | L (3 × ~90 %) | N12 |
| L5 | **S12+ Studio One plug-in (J3):** a Source insert per track, one shared room | prompt in roadmap §5 | L (3+) | L4 |
| L6 | **Lean convolution plugin/Play mode (Idle's idea):** partitioned convolution of a rendered IR for many stacked instances. It can't carry Movement exactly (one IR snapshot), so options are no modulation or a few cross-faded IR variants | idea | M–L | R2, L4/L5 |
| L7 | **AUDIT B1:** save/load scenes, undo/redo and autosave (nothing persists today; a reload loses everything) | idea (not in S-AUDIT) | M | — |
| L8 | **AUDIT B2:** master output meter and clip LED on the Mix desk, plus numeric pan readouts | idea | S | pairs well with N2/N3 |
| L9 | **AUDIT B3:** move "Advanced / Structure locks" off every tab (to Space or a gear menu), per the only-relevant-controls rule | idea | S | — |
| L10 | **AUDIT B5:** plain-words Polar banner | idea | S | — |
| L11 | **Known open gates:** t13 early parity XFAIL (Play early about +3 dB vs Render: 32 taps vs the full set); P5 coherence miss | idea / research | M | — |
| L12 | **Small cleanups:** `engine/fdn.py` keeps its own 16-bit `write_wav_stereo` (HANDOVER S-AUDIT note). On the box copy it is used only by the dev scripts (the `fdn.py` CLI and `moving_room_demo.py`), not by the app, which writes 24-bit via `render_pipeline` since B1. So it is not moot, just low priority: switch it to 24-bit or drop the duplicate. Idle's site URL for the design language is still wanted | idea | S | — |
| L13 | **Listening backlog:** EQ-plan guitar before/after files (`roadmap/eq_plan/measure/guitar/`, never listened to) and the S-AUDIT heights pairs (`research_ui_wishlist/s_audit/heights_research/`) | Idle task | S | — |
| L14 | **Mic-tab drag issues (18 Sep):** that day's fixes are in SYNC (bigger hit radii, sticky selection, 5 px threshold). The S-AUDIT tour found no broken drag at 1600 px; heights (B6), 390 px (A2) and labels (A9) are fixed. Any leftover issue: Idle to list it below | check with Idle | S | — |
| L15 | **Air on Surfaces:** done in S-UI2 (the Air card is on Surfaces; D-UI12 moved the Air 1-pole to parity-only) | done | — | — |

---

## 4. Idle's UI notes

(Idle fills this in. Build order for everything below: §5.)

- **U1. "The pan and trim knobs are very hard to control" (Mix tab routing desk), Idle, 4 Oct.**
  - **Cause (VERIFIED, UI_AUDIT B1):** each knob is an invisible native slider stretched over a 32 px circle. The whole range sits in about 16 px (trim 1.5 dB per px, pan 12.5 % per px). Clicking jumps to the click point, and half the knob does nothing on click. There's no vertical drag, wheel, double-click reset, fine mode, centre/0 dB detent, or number readout. Only the keyboard arrows work.
  - **Fix (F-KNOB):**
    - Relative drag (up or right), 200 px for the full range: trim 0.12 dB/px, pan 0.01/px, width 0.24 dB/px.
    - Shift = ×0.1 fine. Double-click resets (0 dB, centre or the strip's default).
    - Wheel = one step (0.5 dB / 0.02 pan), and Shift = fine.
    - ±6 px sticky detent at 0 dB and at centre.
    - Value readout under each knob ("+1.5 dB", "L 35", "C"), with click-to-type.
    - 40 px knob with an `ns-resize` cursor, and dimmed when locked.
    - Keep the hidden input for keyboard and ARIA, and add a Playwright test.
    - The same pass fixes the Width needle (B2) and disables Pan on non-Pan routes (B8).
  - **Status:** ready to build, size S–M. No sound change. Overlaps the "numeric pan readouts" part of L8.
- **Audit pointer (was U2) — Full UI audit (4 Oct, build WORKLET_VER 51):** `ui_audit_1004/UI_AUDIT.md`. 13 bugs: B3/B4 MS classic shows "Custom" and has a cardioid S in Measured; B5 the Host strip is hidden at 1280 px; B6/B7 dead controls in Binaural and Mono centre; B9–B11 overlapping labels and drag targets. 21 polish items and 6 questions for Idle (Q1–Q4 change the sound).

### Idle's reply to the audit (4 Oct, 14:47 BST): notes U2 to U7, then MS presets (U8), reflections (U9), non-rect rooms (U10)

Paths are relative to `software/` in the app copy (`ui_audit_1004/app/software`, same build as the PC).

- **U2. "The right mic can't move on its own, it's tied to capsule space. Give an option to split L and R so 2-mic MS works and the other side becomes a free room mic."**
  - **What Split L/R does today (VERIFIED):** it only gives each side its own preset, pattern and HPF. The tooltip is "Own preset and pattern per side" (index.html ~650; app.js 1542 `splitOn`, 1700–1730, handler 2654–2672). It is refused in MS setups (the `msSetup()` check, app.js 2657). Unticking it copies L onto R ("Right now matches Left").
  - **Why R can't move (VERIFIED):** L and R positions are always symmetric about the stand through `space`. Dragging either capsule sets `space = 2·|x − mcx|` (mic_desk.js 1056–1062). Only C has its own offset (`centre_dz`). Per-side heights apply only when "Horizontally aligned" is off. The Mirror/Linked/Independent chips control yaw only (mic_desk.js 1006–1032; app.js 913–918).
  - **The existing room-mic route (VERIFIED):** the Mix Array/Room chips move a strip's capsule to ONE shared room spot (`room_x/room_z/room_y/room_yaw`, app.js 491–503, defaults app.js 92). The spot is typed in the Mic tab's `#roomFields` (app.js 715–738). It can't be dragged (no `room_x` in mic_desk.js or room_editor.js). Two strips set to Room sit on the same spot.
  - **Missing:** (1) a split that unlinks position and yaw, not just preset and pattern; (2) split in MS setups; (3) one room position per strip; (4) dragging the room mic; (5) one control instead of the separate Split tick plus the yaw link chips. The earlier plan was for Split to break one shared side mic into two and be merged with the L/R link. ASSUMED from memory notes; none of that is built.
  - **Fix:** replace the Split tick and the yaw chips with one L/R control: **Mirror | Linked | Split**. Split gives R its own preset, pattern, HPF, X/Z/height and yaw, draggable on the Room floor plan and the Mic top view. Store `room_x_l/_c/_r` etc. so each Room strip has its own spot; keep the `room_*` values as the migration default. Allow Split in MS so 2-mic MS = C (mid) + L (side) with R free as a room mic. Default stays Mirror, so the default sound and goldens are unchanged. **Size M.** This is also what the D-UI25 acceptance scenario (3 Oct: L = side, C = mid, R = independent room mic with its own position) needs; today R can't get its own position. Sessions T7–T8. Needs Playwright plus a parity check that Mirror is bit-exact.

- **U3. "Default mics should be Neumann cardioids, not SM57."** **LOCKED as D-UI30 (Idle 15:06): option A, after the A/B render (T5 → T6).** *(20:40: T6 merged into SL7b, the single default switch.)*
  - **Today (VERIFIED):** SM57 ×3 in app.js 97, app_server.py 636 / 1028–1030 / 1317–1319, render_pipeline.py 1351–1353. About 77 test references would need goldens regenerated.
  - **Measured Neumann presets in mic_fitter (VERIFIED):** U87 Ai Cardioid / Omni / Bidirect (Franco et al. dataset, Zenodo 10.5281/zenodo.4633508). **U87 Ai Cardioid is the only measured Neumann cardioid**; there is no KM184/KM 84. Other measured cardioids: AKG C414, Røde NT2-A, Schoeps CMC5-U (plus dynamics).
  - **Options:** (A) U87 Ai Cardioid ×3 (large diaphragm, what Idle asked for); (B) Schoeps CMC5-U Cardioid ×3 (small diaphragm, closer to classic ORTF practice, ASSUMED); (C) keep SM57.
  - **Recommendation: A**, with B in the preset list. Ship as one commit: new defaults plus regenerated goldens plus an A/B render for Idle before merge. **Size S** (code) + goldens.

- **U4. "Room tab: drag the walls on the diagram instead of only sliders."**
  - **Today (VERIFIED):** room_editor.js floor and elevation canvases only hit-test the mic, source and source B (plus heights, yaw and size handles). There are no wall handles; clicking empty floor moves the selected object.
  - **Fix:** an 8 px hit band on each wall and corner handles on the floor plan to drag W/L (the opposite wall stays put); the ceiling edge on the elevation for H. Live "6.20 m" label, Shift = 0.1 m snap, same limits as the sliders, clamp mic/source through `RoomMath.clampRoom`. Double-click a wall to type a value. Sound changes only as the sliders do. Do it after P1 (canvas scaling). **Size S–M.**

- **U5. "Sliders should accept typed values throughout."**
  - **Today (VERIFIED):** 47 range inputs in index.html. Only Source yaw/pitch/size (number twins) and the 7 faders (click the readout) accept typing; room_x/z/y/yaw, diffusion seed and lambda_ref are already number boxes.
  - **Needs typing (37 static + 14 per-face):** Room W, H, L; Mic space, stand X (mcx), stand Z (mcz), mic height (my), source height (sy), head yaw, capsule mm; patterns polar_side/l/r/c; mic_response_hz; decay_s; humidity, air_shelf, air_lp, structure diffusion, jitter; fdn_g; source balance; IR length; Mix trim ×7 (L, C, R, direct, FDN, early, dry), width ×3, pan ×3; Surfaces 7 absorb + 7 EQ per face (built in colour_surfaces.js 434/472).
  - **Fix:** one shared helper: click the value readout → inline text box; Enter applies, Esc cancels; clamp to min/max, round to step, accept units ("3.2 m", "-4 dB", "L30"); fires the same input/change events so undo and recall work. Covers U1's knob readouts too. **Size S–M**, no sound change.

- **U6. "Move the room size sliders off the Source page so the diagrams can be bigger."**
  - **Today (VERIFIED):** the Source sidebar holds Room size, Preview and Advanced; the source floor canvas is 472 px wide.
  - **Fix:** drop Room size from Source (it lives in Room); move the Preview/status line into the header so the Source sidebar can collapse; grow the Place & Face diagrams to about 700 px. **Size S**, no sound change.

- **U7. Mixer redesign: context L and R buttons instead of Pan/Centre/Both; pot with centre detent; no separate Ø; Trim as text; no solo on mic strips; what are Array and Room?** **LOCKED as D-UI31 (Idle 15:06): same buttons with phase on all strips; L+R = both for an MS Mid (session T2).**
  - **Routes today (VERIFIED, app.js `pair()` 442–457):** centre = [0.5a, 0.5a]; both = [a, a]; l = [a, 0]; r = [0, a]; s = [a, −a]; pan = locked 2011 linear law [a(1−t), a·t]. Phase (`phase_l/c/r` = ±1, Ø buttons, index.html 230 etc.) flips the whole strip. Width (dB) replaces Trim on route s (app.js 346–361). "Centre" equals pan-at-centre under the linear law.
  - **Truth table (proposed buttons → existing modes, no engine change):**

    | L button | R button | Route | Pot does |
    |---|---|---|---|
    | on | off | l (hard left) | nothing (greyed) |
    | off | on | r (hard right) | nothing |
    | on | on | pan (centre detent = today's centre) | balance, locked linear law |
    | on | inverted | s: +L, −R (MS side) | width |
    | inverted | on | s with Ø: −L, +R | width |
    | inverted | off / off, inverted | l or r with Ø | nothing |
    | inverted | inverted | pan with Ø | balance |
    | off | off | muted | — |

  - **Gap (VERIFIED):** "both" (unity into both sides, a = 1 each) has no button state, and M/S decoding needs it (MS classic sets C = both, `gain_exact_c = 1.5`, app.js 403–415). **Fix:** when a strip is the Mid of an MS pair, L+R = both; otherwise L+R = pan. A unity-at-centre balance law would add +6 dB at centre and change locked D-UI4, so that is a question for Idle, not a default.
  - **Phase per mic: recommend all three mics get the same L/R buttons including invert**, instead of split-phase on L, none on C, single invert on R. Examples: (1) room mic on the left: MS must then use C + R, so R needs the split (+L −R) state; (2) back-to-back cardioid MS needs L = s and R = s with Ø, so both sides need split and invert; (3) the desk's `ms_s` picker already lets S be L, C or R (index.html 209); (4) C needs invert to fix polarity on a spaced centre mic. One layout on every strip is also less to learn.
  - **Trim → text box** (uses U5 helper). **Mic-strip Solo (VERIFIED absent):** Solo exists only on the Direct/FDN/Early/Dry buses (index.html 285–314); add Solo to the L/C/R strips through the same solo logic. **Size M** total (UI only; the routes already exist).
  - **Array and Room, in plain words (VERIFIED app.js 491–503):** Array = this mic stays on the stand with the others. Room = this mic is unplugged from the stand and placed at the room-mic spot typed in the Mic tab (X, Z, height, yaw). Today all Room mics share that one spot (see U2).

- **U8. MS presets (Idle's Q1: "include all of them").** **LOCKED as D-UI29 (Idle 15:06): a, b, c; default b; d dropped or labelled an effect (session T3).**
  - **Real practice (VERIFIED, sources below):** classic MS uses a figure-8 Side with any Mid pattern; omni and cardioid Mids are both standard (Schoeps MS page; Sound On Sound "This Is Stereo! Part 4": omni Mid decodes to back-to-back cardioids). A Side made from two back-to-back cardioids, one phase-reversed, is documented (DPA Mic University). Double MS adds a rear cardioid (Schoeps Double MS). Sony MS mics built from 3 cardioid capsules: forum source only, ASSUMED.
  - **(a) fig-8 S + omni M:** real, VERIFIED. Measured: U87 Ai Bidirect + U87 Ai Omni (or C414/NT2-A/CMC5-U Bidirect; omni DPA 4006, C414/NT2-A/CMC5-U Omni).
  - **(b) fig-8 S + cardioid M:** real, VERIFIED, the most common. Measured: U87 Ai Bidirect + U87 Ai Cardioid (or Coles 4038 / Royer R-121 as S).
  - **(c) two back-to-back cardioids for S + omni/cardioid M:** real, VERIFIED. Desk: L = s, R = s with Ø, C = both; set `space` = 0 (capsules aren't truly coincident, so some HF error). Measured: 3× U87 Ai Cardioid, or CMC5-U Cardioid ×2 + any M.
  - **(d) one cardioid split-phased as S:** not an MS technique (ASSUMED, no source found). Maths: a cardioid = ½ omni + ½ fig-8, so S carries an anti-phase omni part. A front source comes out L:R = 1.5 : 0.5 (about 9.5 dB to one side) and partly cancels in mono. This is what MS classic in Measured accidentally does today (B3/B4).
  - **Recommendation:** default MS = (b) U87 Ai Bidirect + U87 Ai Cardioid; also ship (a) and (c). Leave (d) out, or label it an "effect, not MS" if Idle wants it. Fix B3/B4 at the same time. **Size S–M.**
  - Sources: schoeps.de/en/knowledge/knowledge-base/recording-techniques/ms-technique.html; soundonsound.com "This Is Stereo! Part 4"; uaudio.com/blogs/ua/mid-side-mic-recording; DPA Mic University, stereo recording techniques; schoeps.de/en/products/surround-3d/double-ms.html; AKG M-S technique manual (LOC PDF).

- **U9. How Space/early picks the 32 reflections that feed the 32-line Hadamard FDN (VERIFIED, info for Idle).**
  - **A fixed image-index table, not the loudest 32 at the mic.** `LIVE_32` (engine/early_field.py 257; `LIVE_32_REAKTOR` 295 under reaktor_parity; `BINAURAL_REAR32` 333 for binaural; other N via `enumerate_scaled_grid`, 465–560). `compute_taps` (1724) picks the table (1773–1784), then loops each image (1794+) and only computes gains per capsule from the pattern (pressure/gradient terms, 1821–1823).
  - **Patterns change gains only.** A reflection in a fig-8 null keeps its line; nothing is reordered or dropped. FDN line i delay = tap i distance (`fdn_delays_from_taps`, engine/fdn.py 785–814; `_tap_distance` 649); gains via `_tap_level` (700). Play uses the same `compute_taps` (render_pipeline.py 2029; Render 1433/1462); surface solo/mute only gates taps (`_early_gate_row` ~1925).
  - **If changed to "loudest 32 at the mic":** pro: no lines wasted on nulls, more early energy where the mic listens. Cons: the set changes as patterns or yaw move, so delays jump (needs crossfade or tank reset, else clicks); tail colour and T60 would shift with pattern; L/R/C could pick different sets; breaks mirror invariance (`test_mirror_exact`) and the reaktor_parity goldens. CPU is minor (sort ~343 candidates per parameter push; FDN cost unchanged). Middle option: keep the FDN on LIVE_32 and choose only the Play early taps by loudness. **No change recommended without Idle's call.**

- **U10. Idle wants to discuss non-rectangular rooms.** Brief: `roadmap/NONRECT_ROOMS_BRIEF.md` (research only, no implementation).

---

## 5. Thursday Build sessions (in order)

Sorted 4 Oct 2026, 15:15 BST; updated 16:55 BST after the 16:43 locks (T3b, T4b, P-D7 added). Prompts: `roadmap/thursday_prompts/` (run order in `PROMPTS_INDEX.md`: T1, T2, T3, T3b, T4, T4b, T5, P-D7, T7, T8, T9, T10, T11, then SL1–SL6, SL7a; SL7b when Idle OKs the SL7a final A/B. T6 is merged into SL7b). Each session is self-contained and must finish cleanly on its own.

**Rules for every session:**
- Start from the last synced tree.
- End with the full test suite green, the Render golden hash recorded in HANDOVER (unchanged, or changed with a GOLDEN_META reason) and a synced snapshot.
- Each session has a **cut line**. If Build usage runs short, stop at the last green state and drop the rest of the session. Never leave a feature half-wired.
- **Goldens column:** **NO** = the main Render golden `ebd77c3b…` must stay bit-exact. **YES** = the session regenerates goldens on purpose, and it is the only change in that session.

| # | Session | Items | Goldens | Size | Needs first | Cut line (minimum clean finish) |
|---|---|---|---|---|---|---|
| T1 | Knobs + typed values | U1 / F-KNOB (with B2 Width needle, B8 Pan greyed off-Pan); U5 shared click-to-type helper on the 37 static + 14 per-face sliders | NO | M | — | Knobs + helper on Mix first; other tabs only if time allows |
| T2 | Mixer L/R buttons (D-UI31) | U7 buttons with phase on all 3 strips (truth table U7, L+R = both for MS Mid), Ø buttons removed, Trim text box, mic-strip Solo, plain-words Array/Room tooltips; B5 (Host strip hidden at 1280 px), P5 (tooltips, "dB"), P6 (chip wrap) | NO (old scenes map 1:1 onto existing routes; null test per row) | M | T1 (helper) | Buttons + state mapping + tests; Solo and polish only if green |
| T3 | MS presets (D-UI29) | Presets a/b/c, default b = U87 Ai Bidirect + U87 Ai Cardioid; d dropped; fixes B3 ("Custom" flip) and B4 (cardioid S in Measured); Q1 closed. Keep `gain_exact_c = 1.5` here (`MS_LEVEL = "legacy"`); D18 unity −3 dB lands in T3b | MS preset references only (new MS null tests); main golden NO | S–M | T2 | Preset b + B3/B4; a and c can follow in T7 |
| T3b | MS sound (D18 + D19) | Unity Mid −3 dB on M and S; MS direct uses the pattern spikes in Render + Play (`prebuild/t3b_ms_sound`, prototype diff proven) | **MS references only** (main NO) | S–M | T3 | D19 (Render + Play together) first, then D18 |
| T4 | EQ-1a Smooth (R1) | Locked prompt `roadmap/eq_plan/EQ1a_PROMPT.md` as written (skip if it already ran before Thursday) | **YES** (default ON) | M | — | As per the prompt |
| T4b | ORTF C off (D20) | ORTF default without C; "ORTF + C" preset = today's sound (`prebuild/t4b_ortf_c`) | **YES** (main) | S–M | T4 | Whole session or nothing |
| T5 | U87 A/B render (box job, no Build usage; on the post-T4b tree) | SM57 ×3 vs U87 Ai Cardioid ×3 (CMC5-U Cardioid as a third reference), golden scene + guitar, loudness-matched, on the post-T4 tree. **Idle listens** (early listen; since 20:40 the switch gate is the SL7a final A/B) | NO (no code change) | S | T4 (so he hears the final tail) | — |
| P-D7 | Play small-room re-measure on the PC (D21) | `run_phase_tests.py --slow` small_lock08 on the post-T4 tree; report to Idle | NO (no code) | S | T4 | — |
| ~~T6~~ | **Merged into SL7b (20:40).** U87 default switch (D-UI30) | touch points moved to SL7a step 3 | — | — | — | do not run |
| T7 | Split L/R part 1: engine and state (U2) | Mirror / Linked / Split control (merges the Split tick and yaw chips, Q5/P3); in Split, R gets its own preset, pattern, HPF, position and yaw; Split allowed in MS; one room spot per strip (`room_*` as migration default); D-UI25 acceptance test (L = S, C = M, R = free room mic). MS presets a/c if T3 cut them | NO (Mirror bit-exact) | M | T2, T3 | Split state + server + tests; UI shows typed fields only |
| T8 | Split L/R part 2 + wall drag (U2, U4) | P1 canvas scaling first; drag R and Room mics on the Room floor plan and Mic top view; wall/corner drag for W/L, ceiling drag for H, with labels, snapping and double-click to type | NO | M | T1, T7 | Mic drag; wall drag only if green |
| T9 | Mic tab clean-up | B6 (Binaural dead controls), B7 (Mono centre L/R controls), B10 (overlapping drag targets), B11 (Combined labels), P2, P4, P10 | NO | S–M | T7 | Bugs before polish |
| T10 | Other tabs clean-up | U6 (Room size off Source, bigger diagrams), P14 (Room size on Room only, Advanced off every tab = L9), B9, B13, P7, P8, P11–P13, P15–P18 | NO | S–M | T8 | U6 + bugs before polish |
| T11 | EQ-1b Movement (R2) | Locked prompt `EQ1b_PROMPT.md` (rebased); default 0 | NO for the default scene (Movement 0); new Movement references | M–L | T4 | As per the prompt; the biggest one, so last |
| SL1 | Surfaces "Room result" model + readout (D-SL1–9) | Port `surf_target` (Eyring/Arau + scatter, α conversion, air); `/api/room_result`; the Room result panel per the T10/D-UI32 mockup `prebuild/app_copy_files/mockups/surfaces.html` (panel only if the redesign hasn't landed); Decay mode selector (greyed) | NO (read-only) | M | T11 (order), T10 | Model + API + tests; panel if green |
| SL2 | Surfaces mode in the Render loop | 3 biquads per line (S1P2) from the room target, DC–Nyquist stability guard, per-axis cuts replaced (D-SL3), `fdn.py` + `fdn_core.c` | NO (Flat default bit-exact null test; new Surfaces refs) | M–L | SL1 | Engine + tests; UI if green |
| SL3 | Surfaces mode in Play | per-line sections in `live_stereo.c` reuse the per-axis slot; ≤ +0.10 ms on t19 | NO (Flat Play bit-exact) | M–L | SL2 | Coefficients + Play-vs-Render test |
| SL4 | Directional decay + calibration (D-SL2, D-SL4) | per-line rates from each line's faces, s′ ≥ 0.5; one T20 calibration pass | NO (Surfaces only) | M | SL2 | Directional + tests; calibration if green |
| SL5 | Treatment rows (D-SL6, D-SL8) | porous + air gap, membrane, Helmholtz, room shell per face; "plaster + parquet" library set | NO (Surfaces only) | M–L | SL4 | Model + state + tests; UI list if green |
| SL6 | Auto-treat (D-SL5, D-SL9) | axis-balanced broadband + ≤ 4 tuned panels as suggested rows; EBU preset pass/fail; "Make it a panel" on EQ_PLAN rows < 300 Hz (if N5 landed) | NO (suggestions) | M | SL5 | Algorithm + API + tests; button if green |
| SL7a | Default switch prep (D-SL10, ST-1, ST-2) | Natural (air) mode with the cut loss folded (Render + Play); frozen Flat (2011) parity suite `tests/refs_flat2011/` + `legacy_2011_profile()`; `DEFAULT_SET` flags (2011 / 2026) left at 2011; U87 touch points; old scenes → Flat; final A/B (today / Natural+U87 / Surfaces+U87 / Surfaces+SM57); re-record dry run | NO (flags not flipped) | M–L | SL6 | Steps 1–3 + tests; A/B if green |
| SL7b | **Default switch** (gated) | `DEFAULT_SET = "2026"`: Surfaces (with air) + U87 Ai Cardioid + real materials + room shell; regenerate every reference once; GOLDEN_META "SL7b default switch"; Flat parity stays bit-exact | **YES** (everything default, once) | M | **Idle's written OK on the SL7a A/B** | Whole session or nothing |

**Not in Thursday's run (needs a decision, research or more Build time first):** R4 and L1 (S5/S6 scatter); N2–N18 (decisions; N2+N3+N4 become one S-OUT session once N2 is answered); B12 (jagged 3D stack, needs investigation); Q2–Q4 and Q6; L2–L15; U9 (reflection selection: info only, no change without Idle's call); U10 (non-rectangular rooms: discussion first, `roadmap/NONRECT_ROOMS_BRIEF.md`).

**Added 4 Oct, 16:30 BST:** paste prompts T1–T11 are in `roadmap/thursday_prompts/` (index `PROMPTS_INDEX.md`; since 16:43 no decision blocks a prompt, only T6 is gated on Idle's T5 OK; since 20:40 T6 is merged into SL7b, which is gated on the SL7a final A/B). Pre-built, tested modules and mockups are in `roadmap/prebuild/` (README per folder, exact integration lines). The research briefs are in `roadmap/research/INDEX.md`. New finding R18: the direct sound ignores the mic pattern with one source (MS direct sits 11.2 dB left).
