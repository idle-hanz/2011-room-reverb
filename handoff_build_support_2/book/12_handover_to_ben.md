# Chapter 12 — Handing the technology to Ben Supper

> **Status: STUB, expanded 2026-10-05 — PLANNED.** No handoff has been arranged in any source file; this is Idle's stated wish (5 Oct 2026).

**Chapter purpose.** Idle would like to hand this technology to his friend Ben Supper, who now makes synths and might build something with it. This page lists what a handoff pack would need, so the book grows toward it. It does not speak for Ben.

**Sources:** the book brief (`/tmp/book_brief.md`: "Ben Supper (supperware.net, Focusrite VRM inventor)"); the parent agent's web look-up (Focusrite VRM around 2010, later ROLI, his own head tracker and synths — ASSUMED, not re-checked here); licence files listed below.

> **In plain English.** Idle wants this technology to have a life beyond his own project, and Ben, who built Focusrite's headphone room simulation (VRM) and now makes synths, is the person he has in mind. A handover only works if Ben can understand the system without the hundreds of chat messages behind it. That is the main reason this book exists: it is the handover document in the making. The more of it that is written from built, tested code, the easier the handover.

## Why Ben (ASSUMED, from the brief)

VRM already combined measured monitors, an artificial room and HRTF convolution for headphones. This engine speaks the same language: sources, surfaces, mics and binaural.

## What a handoff pack needs (proposal, ASSUMED)

1. **This book**, with Chapters 6 (Surfaces and auto-treat) and 8 (tests) written from shipped code, not plans.
2. **One C core** (J2) with build instructions, goldens and the Flat (2011) parity suite.
3. **The locked-decision record** (DECISIONS_LOCKED files) so he knows what was a choice and what was physics.
4. **Licences.** Data in the app carries its own terms (VERIFIED, `BIG_JOBS_ROADMAP_2026-10-01.md` and the vendored `LICENSES/` folder): SADIE II HRTFs Apache-2.0; TH Köln KU100 data CC BY-SA 3.0 (share-alike for derived data files); TU Berlin source-radiation sets are excluded by the loader (`_reject_tu()`). The mic dataset (Franco et al., Zenodo 10.5281/zenodo.4633508) and BRAS material terms need checking before redistribution (Open).
5. **Ownership and licence of Idle's own code** — not stated anywhere (Open; Idle's decision).

## A possible order of events (PLANNED, plain English)

*A suggestion, not a decision; Idle and Ben decide.*

1. **Finish the roadmap** to SL7b, so the default sound is the one Idle wants to hand over.
2. **Bring the book up to date** with Surfaces, auto-treat and the tests written from shipped code.
3. **An informal look:** send Ben this book plus a few A/B renders and ask what interests him (a synth's built-in room? a binaural tool? the shared-room plug-in?).
4. **Decide what is handed over:** the whole engine, a single C core, or the knowledge only; and under what licence (Idle's choice).
5. **Make the pack:** code, tests, goldens, decision records, data licences and the book.

## What Ben would find most useful (ASSUMED)

The parts that are new rather than textbook: how the 2011 mirror echoes feed the corridors one-to-one; Surfaces-in-the-loop with directional lines, calibration and auto-treat; the Play/Render parity method; and the test discipline that keeps the 2011 sound reproducible.

## Open / not yet built

No date, scope or licence choice. Revisit after SL7b.
