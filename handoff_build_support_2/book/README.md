# The 2011 Room Reverb rebuild — the living technical book

**Status: draft, 2026-10-05 (plain-language pass added the same day).** Nothing in this book is finished. It describes build 51 (WORKLET_VER 51, after S-MIX, D-MIX-J and S-AUDIT) and marks everything after that as LOCKED-not-merged or PLANNED.

## Who it is for

Idle Hanz first: so the technology never runs away from the person who designed it. Ben Supper later: so someone who already thinks in auralisation can pick it up without the chat history.

## How to read it

- **Not an engineer? Start with `HOW_TO_READ.md`.** It gives a one-hour route (Ch. 2 §2.0 and §2.7, Ch. 5 §5.0 and §5.6a, Ch. 6 §6.0, §6.5a, §6.6) that is enough to understand how Surfaces will shape the sound.
- After every dense section of Chapters 1–8 there is an **"In plain English"** box; in Chapter 6 each design step opens with a **"Plain first"** note before any formula. Worked illustrations are labelled as such and computed in the book, never presented as project settings.

- Start with **Chapter 1** (why this exists) and **Chapter 2** (the signal path). Every later chapter hangs off Figure 2.2.
- **Chapter 6 (Surfaces, panels and auto-treat)** is the key chapter for the new technology. Read Chapter 5 first.
- **Chapter 8** explains why a "bit-exact" claim can be trusted.
- Every chapter opens with a one-paragraph purpose and its source paths, and every claim is tagged:
  - **VERIFIED**: read in code, a cited source, or measured, as cited.
  - **ASSUMED**: judgement, a source seen second-hand, or not re-checked.
  - **LOCKED, not merged**: Idle decided it; Build has not shipped it yet.
  - **PLANNED**: an idea or design, not in the app.
  - **DESIGNED** (Ch. 6): prototyped and pre-built on the box, not merged. **OPEN**: not decided or not known.
- Diagrams are mermaid (render in any mermaid viewer, VS Code, or GitHub). Where frequency matters, colours run red (low) to violet (high). Existing PNGs are copied into `figures/`; no plots were invented for this book.

## Chapters

| # | File | Status |
|---|---|---|
| 1 | `01_purpose_and_history.md` | DONE (draft) |
| 2 | `02_signal_flow.md` | DONE (draft) |
| 3 | `03_play_vs_render.md` | DONE (draft) |
| 4 | `04_decisions_and_gates.md` | DONE (draft) |
| 5 | `05_fdn_and_early.md` | DONE (draft); Smooth and Movement sections are plans |
| 6 | `06_surfaces_and_panels.md` | DONE as far as the prototypes go (with a plain-English walk-through, §6.0); the shipped behaviour arrives with SL1–SL7b |
| 7 | `07_mics_and_mixer.md` | DONE (draft) |
| 8 | `08_testing_and_goldens.md` | DONE (draft) |
| 9 | `09_nonrectangular_rooms.md` | STUB, expanded (PLANNED) |
| 10 | `10_studio_one_shared_room.md` | STUB, expanded (PLANNED) |
| 11 | `11_variants_and_export.md` | STUB, expanded (PLANNED) |
| 12 | `12_handover_to_ben.md` | STUB, expanded (PLANNED) |
| — | `99_glossary.md` | DONE (draft): every term in Ch. 1–8 |
| — | `HOW_TO_READ.md` | Front piece for non-engineers |

The full plan, including chapters not yet started, is in `00_outline.md`. How much is written and when it is updated is in `STATUS.md`.

## Relation to the roadmap

The book does not replace the roadmap. The run order is `../NEXT_SESSION_PLAN.md` (T1 → SL7b); the decisions are `../roadmap/DECISIONS_LOCKED_2026-10-04.md` and `../DECISIONS_LOCKED_2026-09-28.md`. Paths in this book are relative to the handoff folder (`build_support_2`) unless they start with `/workspace/` (box-only research).

## How it grows

A chapter is updated **after** a locked session ships and its HANDOVER is mirrored to the box, never ahead of the code. Each update moves claims from "LOCKED, not merged" to VERIFIED with the new source path, and records the date in `STATUS.md`.
