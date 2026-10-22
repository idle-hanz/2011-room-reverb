# Outline — full plan of the book

> Change note 2026-10-20: added Ch. 13 (per-room k, T20 ruler, BLOOM design, Character plan) to Part II.

> Draft 2026-10-05, updated after the plain-language pass the same day. Front piece: `HOW_TO_READ.md` (for non-engineers). Status key: **DONE** = written from shipped work and sources (still a draft); **PARTIAL** = written, but a large part waits on locked sessions; **STUB** = a page under 400 words that holds the idea; **PLANNED** = no file yet.

## Front matter

| File | Status |
|---|---|
| `HOW_TO_READ.md` — start here if you are not an engineer | DONE (draft) |
| `README.md` — map, tags, how the book grows | DONE (draft) |

Every DONE chapter (1–8) now carries "In plain English" boxes after its dense sections; Ch. 2 has §2.0 (whole picture) and §2.7 (Surfaces preview); Ch. 5 has §5.0 (corridors) and §5.6a (why filters must be inside the loop); Ch. 6 has §6.0 (bouncing ball, tuned sponges), "Plain first" notes on all eight steps and §6.5a (summary table).

## Part I — What it is

| # | Chapter | Status | Grows after |
|---|---|---|---|
| 1 | Purpose and history (2011 Reaktor → web/wasm) | DONE | Idle's own history notes (none on the box yet) |
| 2 | Signal flow (source → early → FDN → mics → out; Play/Render; Flat vs Surfaces/Natural) | DONE | T4, SL2/SL3, SL7a/b |
| 3 | Play versus Render | DONE | SL3, J2 C migration |
| 4 | Decisions and gates | DONE | every locked decision |

## Part II — How it works

| # | Chapter | Status | Grows after |
|---|---|---|---|
| 5 | Early field and FDN tail (Smooth, Movement, EQ split) | DONE for build 51; Smooth/Movement PARTIAL | T4 (Smooth), T11 (Movement), P-D7 |
| 6 | **Surfaces, panels and auto-treat** (key chapter) | PARTIAL: prototype facts DONE, shipped behaviour waiting | SL1, SL2, SL3, SL4, SL5, SL6, SL7a/b |
| 7 | Microphones and the mix desk | DONE for build 51 | T1, T2, T3, T3b, T4b, T5, T7–T9, SL7b |
| 8 | Testing, goldens and parity | DONE | each golden change; SL7a parity suite |
| 13 | Per-room decay, T20 ruler, BLOOM and Character (`13_room_character_and_bloom.md`) | PARTIAL: per-room k and ruler DONE; BLOOM designed, retry pending; Character PLANNED | BLOOM retry, Movement in Render, Character session |
| — | Air and humidity (ISO 9613-1, the air shelf, no air on the FDN return) | PLANNED (facts scattered in Ch. 2, 5, 8) | SL7a Natural mode |
| — | Source radiation (J1: talking head, trumpet, cabinets; SRC_RAD) | PLANNED | none scheduled; facts in BIG_JOBS |
| — | Binaural in depth (SADIE II, IC-matched tail, mirror table) | PLANNED (summary in Ch. 7) | S6 / J12 binaural gaps |
| — | Two sources and the shared tail (mirror symmetry, D-MIX-J) | PLANNED | — |
| — | Structure mining and 2011 parity (how the Reaktor patch was reverse-read) | PLANNED | sources to be gathered |
| — | CPU budget (2.667 ms block, ABBA method, what each feature costs) | PLANNED (method in Ch. 8) | SL3, T11 |
| — | Output strip and limiter (D-AUD-3, 24-bit Render, Render length) | PLANNED | S-AUDIT HANDOVER mirrored |

## Part III — Where it could go

| # | Chapter | Status |
|---|---|---|
| 9 | Non-rectangular rooms | STUB, expanded with plain-English vision (PLANNED) |
| 10 | One shared room in Studio One (incl. partitioned convolution) | STUB, expanded with plain-English vision (PLANNED) |
| 11 | Variants and a reverb designer (code export, 3-D delay, cut-down room, game/film binaural) | STUB, expanded with plain-English vision (PLANNED) |
| 12 | Handing the technology to Ben Supper | STUB, expanded with plain-English vision (PLANNED) |

## Appendices

| # | Appendix | Status |
|---|---|---|
| 99 | Glossary (every term in Ch. 1–8, everyday + precise) | DONE (draft) |
| — | Decision index (every D-, K-, H- id with chapter links) | PLANNED |
| — | Source index (which file proves which claim) | PLANNED |
| — | Figure list | PLANNED |
