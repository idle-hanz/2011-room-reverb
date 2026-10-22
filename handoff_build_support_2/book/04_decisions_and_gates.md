# Chapter 4 — Decisions and gates

> **Status: DONE (draft 2026-10-05).** Register of how decisions are made and checked, with the decisions locked up to 4 Oct 2026 20:41 BST. Tags copied from `roadmap/DECISIONS_LOCKED_2026-10-04.md` and `DECISIONS_LOCKED_2026-09-28.md` where present.

**Chapter purpose.** This project only works because nothing changes the sound without Idle knowing. This chapter explains the machinery that guarantees that: how a decision is proposed, tagged, locked and numbered; what a "gate" is and which gates every session must pass; which ideas were tried and rejected (so nobody rediscovers them); and which decisions are still open. The full current run order stays in `NEXT_SESSION_PLAN.md`; this chapter only explains the rules behind it.

---

## 4.1 How a decision is made

1. **Research on the box.** A question is researched, prototyped and measured on a copy of the software. The report gives options with a recommendation in bold, and says for each whether it changes the sound and the goldens (VERIFIED pattern, e.g. `roadmap/sound_tricks/SURFACES_IN_LOOP.md` §9: "Decisions for Idle (every sound change; recommendation in bold)").
2. **Listening.** Sound changes come with A/B audio, loudness-matched, with a listening checklist (VERIFIED, e.g. `roadmap/sound_tricks/surfaces_ab/LISTENING_CHECKLIST.md`, `roadmap/sound_tricks/ab/`).
3. **Idle locks it.** A lock is written with the time and Idle's words where available, e.g. "Idle accepted all 14 recommendations from the 16:32 research report at **16:43 BST, 4 Oct 2026**", and the Surfaces lock at 20:37 after "sounds good, certainly a lot better than flat" (VERIFIED, `roadmap/DECISIONS_LOCKED_2026-10-04.md`).
4. **A session lands it.** Each locked decision names the session that will merge it and its golden impact. "Nothing below is merged yet." (VERIFIED, same file, line 5.)
5. **HANDOVER block.** The first Thursday session pastes the HANDOVER block from the lock file into `software\docs\HANDOVER.md`, so the decisions travel with the code (VERIFIED, `START_HERE.md` step 1).

### The two tags

- **VERIFIED** = "measured or tested on the box (build 51 copy)" or "measured by a script/test in this folder".
- **ASSUMED** = "judgement" (VERIFIED definitions, DECISIONS_LOCKED 2026-10-04 line 6 and 2026-09-28 line 7).

Some reports add finer labels (for example "Build-reported", "Computed, not rendered" in EQ_PLAN §8, or "FORUM" in the Studio One design). This book keeps them when quoting.

> **In plain English.** Every sound change follows the same path: the research machine tries it on a copy and measures it; Idle gets level-matched A/B audio and a checklist; Idle says yes or no, and the yes is written down with the time and his words; a named Build session later puts it into the program. Every claim is marked **VERIFIED** (measured or read in a file) or **ASSUMED** (a judgement), so you always know how solid it is.

## 4.2 Decision families (numbering)

| Family | Meaning | Example | Source |
|---|---|---|---|
| K1–K4, 5–7 | 28 Sep engine decisions, implemented and tested on the box tree | K1 one yaw convention flip `YAW_X_SIGN = +1` | `DECISIONS_LOCKED_2026-09-28.md` |
| D1–D17 | Earlier engine decisions (2 Oct, BIG_JOBS §6), e.g. D3/D3b z⁻¹ in both, D11–D17 Solo/Mute rules | D16 Solo keeps every image touching the face | BIG_JOBS §6; HANDOVER S4b |
| D18–D24 | 4 Oct sound/engine | D20 ORTF centre mic off by default | DECISIONS_LOCKED 2026-10-04 |
| D-UI1–D-UI38 | UI decisions (some change sound, e.g. D-UI26, D-UI30) | D-UI37 Mirror / Linked / Split control | same; BIG_JOBS §0.0 |
| D-SL1–D-SL10 | Surfaces in the loop and the single default switch | D-SL5 auto-treat suggests rows | same |
| ST-1–ST-10 | Sound tricks (ST-1, ST-2 locked; ST-3–ST-10 open) | ST-1 natural decay on by default | same; SOUND_TRICKS |
| D-EQ, D-RES, D-DFF, D-INT | EQ plan decisions | D-DFF locked as the Smooth switch | EQ_PLAN §6 |
| D-NR1–D-NR8 | Non-rectangular rooms (all open) | D-NR3 FDN delays frozen per preset | NONRECT_RESEARCH §6 |
| N, U, R, L, B, P, Q | Thursday list item ids: needs-decision, Idle's UI notes, ready, later, audit bugs, polish, questions | N18 → D20 | THURSDAY_LIST; UI_AUDIT |

Numbers are never reused: "D-UI27–31 and D1–D17 were already used, so these take **D18–D24** … and **D-UI32–D-UI38**" (VERIFIED, DECISIONS_LOCKED 2026-10-04 line 4).

> **In plain English.** Decisions get short labels so they can be referred to precisely: K for the 28 September engine decisions, D for engine and sound decisions, D-UI for screen decisions, D-SL for Surfaces, ST for sound tricks, D-NR for non-rectangular rooms, and so on. A number is never reused, so "D20" always means the same thing.

## 4.3 Locked but not merged (as of 5 Oct 2026)

All of these are LOCKED and land on or after Thursday 8 Oct (VERIFIED, DECISIONS_LOCKED 2026-10-04; NEXT_SESSION_PLAN).

| Decision | In one line | Session | Main golden |
|---|---|---|---|
| D18 | MS presets decode at unity, −3 dB trim on M and S (gain 0.708) | T3b | MS refs only |
| D19 | MS direct sound uses the pattern spikes, Render + Play | T3b | MS refs only |
| D20 | ORTF = centre mic off by default; "ORTF + C" preset keeps today's sound | T4b | YES |
| D21 | Re-measure Play's small room on the PC, then accept/widen or fix (report first) | P-D7 | none |
| D22 | "Physical" realism options opt-in; 2011 stays default | later | NO |
| D23 | Gate the tank after the tail dies (−96 dB); low priority | later | NO |
| D24 | Shared velvet-noise smear, default off, measure CPU first | later | NO |
| D-UI29, D-UI31 | MS presets a/b/c (default b); L/R desk buttons with phase on every strip | T3, T2 | NO (T3 adds new MS tests) |
| D-UI30 | U87 Ai Cardioid on L, C and R instead of SM57 | SL7b (gated; T6 merged) | YES |
| D-UI32–34 | Surfaces / Polar / Space redesigns | later | NO |
| D-UI35–37 | Room size on Room only; "On stand"/"Room mic" + solo-in-place; Mirror/Linked/Split + wall drag "stop" | T10, T2, T7/T8 | NO |
| D-UI38 (amended) | U87 default only after Idle's written OK on the SL7a final A/B | SL7b | YES |
| Smooth (D-DFF) | Diffuser gain cap 0.7, default ON, decay-corrected | T4 | YES |
| Movement | Delay modulation knob, default 0 | T11 | NO (new Movement refs) |
| D-SL1–9 | Surfaces in the loop (Chapter 6) | SL1–SL6 | NO until SL7b |
| ST-1, ST-2, N11/D4 | Natural decay in the loop; cut loss folded; frequency-dependent decay becomes default | SL7a, SL7b | YES in SL7b |
| D-SL10 | One re-recording session switches Surfaces + natural decay + U87; Flat (2011) frozen as a parity test | SL7a, SL7b | YES in SL7b only |

> **In plain English.** This table is the list of things Idle has already approved that are not in the program yet. The right-hand column says whether each one will change the reference recordings ("goldens"). Most do not. The ones that do (ORTF without the centre mic, Smooth, and the final default switch to Surfaces with U87 mics) are deliberate sound changes and each happens in a session of its own.

## 4.4 Gates: what every session must prove

A **gate** is a measurable condition a session must meet before its work counts. Gates are written into each prompt with a **stop rule**: if a gate cannot be met, the session ships the safe variant or reverts, and reports (VERIFIED pattern, e.g. `roadmap/eq_plan/EQ1a_PROMPT.md` "Stop rule").

**Rules for every session** (VERIFIED, `NEXT_SESSION_PLAN.md` "Rules"; THURSDAY_LIST §5):
- One prompt = one Build session in a new window.
- Work above the **cut line** first and commit; go below only if the suite is green with time left.
- "A stop condition ends the session cleanly with a report, never a half-merge."
- "A session that changes goldens changes nothing else."
- End with the full suite green, the Render golden hash recorded in HANDOVER, and a synced snapshot.

**Standing numeric gates** (VERIFIED, quoted from the prompts and HANDOVER):

| Gate | Threshold | Where it comes from |
|---|---|---|
| Main Render golden | bit-exact unless the session is a declared golden session | THURSDAY_LIST §5 "Goldens column" |
| Feature off | max-abs 0 against the pre-session tree, Render and Play | EQ1a G1; SL2/SL3 "Flat bit-exact" |
| t18 FDN-only Play–Render null | ≤ −60 dB, target −71.8 dB | EQ1a G6 |
| `test_mirror_exact` | ≤ −120 dB | EQ1a G6; HANDOVER D-MIX-J |
| t19 CPU (PC, paired) | shared-off ≤ 2.40 ms, shared-on ≤ 2.133 ms | EQ1a G3; HANDOVER S5 fix-up |
| Decay | Smooth: octave T30 within ±5 % of Smooth off; mid T30 within ±5 % of the dial | EQ1a G2 |
| Play T30 vs dial | ±8 % (phase test P0.2) | `3_phase_acceptance_tests/README.md` |
| Surfaces | default room ≥ 16/23 ⅓-octaves within ±10 % after auto-treat | SURFACES_IN_LOOP §10 S-SL6 |
| Listening | Idle's written OK on the A/B for any default switch | D-UI38, D-SL10 |

Chapter 8 explains the test suites behind these numbers.

> **In plain English.** A **gate** is a pass/fail test a session must meet before its work counts, like an MOT for the software. If a session cannot pass, it must stop cleanly, ship the safe version or undo the change, and report; it may never leave half a change in place. The standing gates check that the reference sound is unchanged unless the session was allowed to change it, that new features switched off change nothing, that Play and Render still agree, that the processing still fits the time budget, that decay times are accurate, and that any change to the default sound has Idle's written OK.

## 4.5 Tried and rejected (do not repeat)

| Idea | Why rejected | Source |
|---|---|---|
| FWHT stage rotation against metallic ringing | Named peaks moved only 0–4 dB, peakiness unchanged (7.21 → 7.27 / 7.12 dB); "Idle listened: no audible difference" | EQ_PLAN §4e |
| F5 same-sample loop in Play | Same parity as z⁻¹ in both, but +18.5 % Play CPU, PC estimate 2.43 ms > 2.133 ms gate | `research_f5_allpass/REPORT.md` §0 |
| Six ways of building the Direct sound from the FDN | Each listed as REJECTED (hash, clamps, silent buses) | HANDOVER "Failed attempts (do not repeat)" |
| A 32×32 matrix multiply per sample in the audio thread | It was blowing the audio thread; replaced by one-sample feedback | HANDOVER "Same-sample mix" |
| The `0.68/√32` loop cap | "Do not put that cap back" | HANDOVER "Loop" |
| Uniquifying delays | "Do not uniquify delays" (it is a lock; co-prime nudges conflict with it) | HANDOVER; EQ_PLAN §4b |
| Choosing the "loudest 32" reflections at the mic | Not rejected outright, but "No change recommended without Idle's call": delays would jump with pattern/yaw and mirror invariance and parity goldens would break | THURSDAY_LIST U9 |
| A stricter "2× everywhere" guard on the Surfaces line filters | Over-triggered: lines fell back and HF ran +100–250 % long | SURFACES_IN_LOOP §7 |
| Raw directional decay with s′ = 0.15 | Tails +10–27 % long and a double slope | SURFACES_IN_LOOP §6 |

> **In plain English.** These ideas were tried, measured and turned down, with the reason written down so nobody spends time on them again. Examples: rotating the shuffle pattern made no audible difference; a more exact loop in Play cost too much processing; making every delay length unique conflicts with a 2011 lock; and too strict a safety check on the Surfaces filters made the treble ring far too long.

## 4.6 Still open (for Idle)

**Before SL4–SL6** (VERIFIED, `NEXT_SESSION_PLAN.md`; details in `roadmap/prebuild/sl/README.md` "Findings"):
1. Helmholtz Q: the physical model gives about 1.5–2, against the ASSUMED 3.
2. D-SL3: keep the per-axis cuts below 30 Hz (treated plan 16/23) or drop them all (15/23).
3. The SL4 mild double slope in the untreated plaster room: directional or room average.
4. Treatment also colours the early reflections in Surfaces mode.

**Other open items** (VERIFIED as open in THURSDAY_LIST §2 and DECISIONS_LOCKED_2026-09-28 "Still open"): S-OUT Auto level (N2) and master headroom (N4); resonance control (N5); D-INT 44.1 kHz interpolation (N6); keeping face EQ when a material is picked (N8); C migration order (N12); licence of the TU-Berlin source presets before any public release (N13); confirm the 1.8 s decay by ear; whether to trim direct/early (whole mix +1.61 dB); the K2 distance unit after the 2011 captures; ST-3–ST-10; D-NR1–8; Q2–Q4, Q6 from the UI audit.

> **In plain English.** These are the questions waiting for Idle. The four Surfaces questions come up before sessions SL4–SL6; the rest are smaller items or later ideas. None of them blocks Thursday's first sessions.

## Open / gaps

- The full text of D1–D17 and D-UI1–D-UI28 is spread over BIG_JOBS §6 and the UI wish-list report; a single decision index (appendix) is PLANNED for a later update of this book.
