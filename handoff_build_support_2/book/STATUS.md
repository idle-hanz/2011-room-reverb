# Book status

> Change note 2026-10-20: Ch. 13 added (per-room k and the T20 ruler are built; BLOOM is designed with the retry pending; Character is planned). Update Ch. 13 after the BLOOM retry lands and after any Character or Movement session.

**Date:** 2026-10-05 (Mon). First draft in the morning; plain-language enrichment pass the same day.

## How much is written

- **Chapters 1–8** are drafted from build 51 and the box research, now about 25,000 words including the plain-English material (about 15,000 words of the original technical text plus about 10,000 of plain-language explanation, worked illustrations and analogies).
- **Front piece** `HOW_TO_READ.md` and a **DONE glossary** (`99_glossary.md`, about 3,700 words, every term in Ch. 1–8).
- **Chapters 9–12** are expanded stubs (about 500–800 words each): still PLANNED, with a plain-English picture of the end-state vision and no invented algorithms.
- **Honest estimate:** about 40–45 % of the eventual book, and close to all of what can be written truthfully today. Most of the rest depends on code that does not exist yet: Smooth (T4), Movement (T11), Surfaces in the loop (SL2/SL3), directional tails (SL4), treatment rows (SL5), auto-treat (SL6) and the default switch (SL7a/b).
- **Chapter 6**, the key chapter, is about half done: the design, the prototype numbers, the auto-treat logic and a full plain-English walk-through are written. How the shipped version behaves, sounds and tests cannot be written until SL2–SL6.
- **Readability target:** Idle should be able to read Ch. 2 (§2.0, §2.7) and Ch. 6 (§6.0, §6.5a, §6.6) alone and understand how Surfaces will shape the sound. This has not yet been checked with Idle.

## Update triggers (after the session ships and its HANDOVER is on the box)

| After | Update |
|---|---|
| T1, T2, T3, T3b, T4b | Ch. 7 (desk, MS, ORTF C off); Ch. 8 (golden change at T4b) |
| T4 (Smooth) | Ch. 5 §5.4 and its plain box, Ch. 2 figures, Ch. 8 golden chain |
| P-D7 | Ch. 5 small-room decay figures, Ch. 3 §3.3 |
| T7–T10 | Ch. 7 (Split, room spots, drag) |
| T11 (Movement) | Ch. 5 §5.5, Ch. 3 §3.5, Ch. 8 statistical gates |
| SL1 | Ch. 6 Room result readout |
| SL2 / SL3 | Ch. 6 core, Ch. 2 §2.5/§2.7, Ch. 3 (Surfaces in Render / Play) |
| SL4 | Ch. 6 directional tails and calibration |
| SL5 / SL6 | Ch. 6 treatment rows and auto-treat (the chapter Idle most needs) |
| SL7a / SL7b | Ch. 2, 6, 7, 8: Natural mode, Flat parity suite, new defaults, U87 |
| Each locked session | Ch. 4 decision table; glossary; plain-English boxes of any changed section |

## Known source gaps (to close before the next pass)

- The S-AUDIT HANDOVER section and current GOLDEN_META are on the PC only; the newest mirrored HANDOVER is `roadmap/eq_plan/src/HANDOVER.md` (through D-MIX-J).
- No written history of 2011 → Sep 2026 on the box (Ch. 1 is thin there).
- Surfaces fitter convergence is not specified in any source.
- Speed of sound: Surfaces prototype 343 m/s vs engine 340 m/s.
- The Smooth decay-correction cause and formula are not yet known (T4 computes them).

## Backup

The pre-enrichment versions of every chapter are at `/workspace/book_backup_pre_enrich_20261005/` on the box (outside the handoff folder).
