# Chapter 1 — Purpose and history

> **Status: DONE (draft 2026-10-05).** Covers what exists up to build 51 (S-AUDIT, 3–4 Oct 2026) plus the decisions locked on 4 Oct 2026. Nothing here describes unmerged work as finished.
> **Tags:** **VERIFIED** = read in a source file named next to the claim, or measured on the box/PC and recorded there. **ASSUMED** = judgement, a design choice, or something only reported second-hand.
> **Paths** are relative to the handoff folder (`build_support_2/` on the box, `handoff_build_support_2\` on the PC) unless they start with `/workspace/`.

**Chapter purpose.** This chapter says why the program exists, where it came from, and how the work has been organised so that the person who owns it — Idle Hanz — never loses sight of how it works. It is the chapter to read first and the one to hand to anyone new (for example Ben Supper, see Chapter 12). It sets out the one idea that runs through the whole book: there is a **2011 instrument** that must stay reproducible, and there are **modern upgrades** that are allowed to change the sound only when Idle has listened and said yes.

---

## 1.1 What the program is

The *2011 Room Reverb* is a rebuild of a room reverb that Idle built in Native Instruments Reaktor in 2011. The original ensemble files are `ensemble\2011-room-reverb.ens` and `ensemble\20 October 2011 room reverb.ens`, described as "the same 887 KB family", and they are never edited (VERIFIED, `roadmap/eq_plan/src/HANDOVER.md`, "What this project is").

The 2011 ensemble models a rectangular room in two parts that work together (VERIFIED, HANDOVER "2011 wet path (locked)"):

1. **Image sources.** The source is mirrored in the walls. Each mirror image is a reflection; its distance to the microphones gives a delay (`delay_ms = d / 340 × 1000`) and a level (`1/r²`).
2. **A feedback delay network (FDN).** 32 delay lines are mixed through an unscaled ±1 Hadamard matrix and fed back. In the 2011 design the first read of each line *is* one image: "First read at each image time **is** that image. Hadamard is mix/invert only." (VERIFIED, HANDOVER.)

The output is picked up by three microphones (left, centre, right), folded to stereo with the Mixer rule `L + 0.5·C`, `R + 0.5·C` — the "477 fold" (the rule is VERIFIED, HANDOVER hard-locks table, row "Mixer fold … VERIFIED (477)"; that 477 is the number of the Structure screenshot that proves it is ASSUMED from how the HANDOVER cites screenshots).

Today the program is a desktop application on Idle's PC (VERIFIED, HANDOVER "What this project is"):
- a **FastAPI** server (`software\app_server.py`, launched by `software\Launch Tweak App.bat`) serving a browser UI at `http://127.0.0.1:7860`, built with Canvas and Three.js;
- **Play live**: real-time audio in the browser. The page posts parameters to `/api/live_params`; an AudioWorklet runs `live_stereo`, a C engine compiled to WebAssembly;
- **Render**: an offline Python path (`render_pipeline.py`) that writes a WAV file (24-bit since S-AUDIT, VERIFIED `roadmap/THURSDAY_LIST.md`, "Done since 3 Oct").

The legacy Gradio app `tweak_app.py` is reference only (VERIFIED, HANDOVER).

The UI has seven tabs: Room, Source, Mic, Mix, Space, Surfaces, Polar (VERIFIED, `ui_audit_1004/UI_AUDIT.md` §D).

> **In plain English.** In 2011 Idle built a reverb in Reaktor (Native Instruments' modular sound-design software) that imagines a real rectangular room. It works out where the echoes off each wall would come from, by treating the walls as mirrors, and how late and how quiet each echo arrives (further away = later and quieter: twice the distance, a quarter of the level). It then feeds those echoes into a network of 32 recirculating delay lines that keeps them going and blends them into a smooth fading tail. Three virtual microphones listen and are mixed to stereo.
> Today the same idea runs as a program on Idle's PC with a browser screen. **Play** lets you hear every change live; **Render** writes a finished audio file. The original 2011 files are kept untouched as the reference.

## 1.2 Two lists kept apart: fundamentals and upgrades

The HANDOVER keeps two lists apart, and this book does the same (VERIFIED, HANDOVER "What this project is"):

1. **Fundamentals** — the audio core that should match the Reaktor Structure: Prepare geometry, image macros, distances, Air Abs `1/r²`, Diffuser Delay plus Hadamard feedback, 32 voices, `Out = In × (1/32) × Gain` on the 2011 path, no `1/√N` on the matrix, Mixer L/C/R fold plus RMS/AGC makeup.
2. **Upgrades** (tagged ASSUMED in the HANDOVER): free mic placement, modern toe-in and ORTF, Surfaces cards, measured mic colour, 3D views, seeded jitter, the Mix desk, Decay lock, the Play-live worklet, a stereo file as two sources, and so on.

The fundamentals were recovered by reading the Reaktor Structure screen by screen ("Structure mining"). The hard locks that came out of it are listed in the HANDOVER, each with a reference number in brackets (ASSUMED: the Structure screenshot or note that proves it), for example speed of sound `c = 340` (VERIFIED Const), `MCZ = L − MZ`, Diffuser Delay max 1000 ms (472, 476), Humidity Wet 100–700 default 400 (486), Diffusion Master 0…−0.5 default −0.25 (485) (VERIFIED, HANDOVER "Hard locks"). Some Structure questions remain open, for example "Dffs room-scale knob IC Default unread" and the To V 17–52 voice map (VERIFIED, HANDOVER "Still open (Structure)").

The engine keeps the 2011 behaviour reachable through a **`reaktor_parity`** path (the "Hall" button) and a Decay-lock-off path, where the loop runs `Out = In × (1/32) × Gain` and the matrix stays plain H (VERIFIED, HANDOVER "S4b", "Engine notes"). The desktop default, **Decay lock on**, is an upgrade: the loop runs at `g = 1/√N` (about 0.177) with a per-line loss `line_t60` (VERIFIED, HANDOVER).

> **Why this matters for the future.** The decision locked on 4 Oct 2026 (D-SL10) keeps this split permanent: when the defaults change in session SL7b, "Flat (2011)" stays a selectable mode and its references become a **frozen parity test** (`tests/refs_flat2011/`) (VERIFIED, `roadmap/DECISIONS_LOCKED_2026-10-04.md`). That test is not built yet (LOCKED, session SL7a).

> **In plain English.** There are two kinds of things in the program. **Fundamentals** are the parts that must behave exactly as in Idle's 2011 Reaktor patch; they were worked out by reading the patch screen by screen, and each one is "locked" (for example the speed of sound is 340 m/s, because that is what the 2011 patch uses). **Upgrades** are everything added since: free mic placement, wall materials, measured microphone sound, 3-D views, the mixing desk and so on. Upgrades may change the sound only when Idle decides. The "Hall" button (`reaktor_parity`) gets you back to the 2011 behaviour, and when the defaults change in the future the 2011 sound will be kept as a permanently selectable, test-protected mode.

## 1.3 How the work is organised

Three roles do the work (VERIFIED as a working pattern from `START_HERE.md`, `NEXT_SESSION_PLAN.md`; the description of roles is ASSUMED wording):

- **Idle** decides. Every change to the sound is Idle's decision, usually after an A/B listen. Decisions are written down with a time stamp and a number (Chapter 4).
- **Build sessions** change `software\` on the PC, "one prompt at a time" (VERIFIED, `START_HERE.md`: "Never touch `software\` from these docs: Build sessions change it, one prompt at a time.").
- **The box** (a Linux research machine) does research, prototypes, measurements, A/B renders and pre-built tested code, and writes the prompts. It works on copies; the PC `software\` is not touched from the box (VERIFIED, repeated in every box report, e.g. `roadmap/DECISIONS_LOCKED_2026-10-04.md` line 6).

Every session ends with the tests green and the Render golden hash recorded (VERIFIED, `roadmap/THURSDAY_LIST.md` §5 "Rules for every session"). A session that changes goldens changes nothing else (VERIFIED, `NEXT_SESSION_PLAN.md` rules).

> **In plain English.** Idle decides; nothing that changes the sound goes in without his yes, usually after listening to an A/B comparison. **Build sessions** are the only things that change the actual program on Idle's PC, one carefully scoped task at a time. **The box** is a separate research computer that experiments on copies, measures, prepares A/B audio and writes the instructions for Build. Every session must end with all automatic tests passing and with a fingerprint of the reference sound recorded (the "golden hash", Chapter 8), so any accidental change would be caught.

## 1.4 Timeline (what is VERIFIED from dated notes)

The dates below come from dated sections in the HANDOVER copies and roadmap files. Earlier history (2011 to September 2026) is not documented in the sources read for this draft; see "Open" at the end.

| Date (2026, BST) | What happened | Source |
|---|---|---|
| 22 Sep | HANDOVER started as the single read-first file | HANDOVER header |
| 23–24 Sep | Mic brief v2.6 locked; measured mic colour Phases 1–3 (Render, Mic tab, Play) | HANDOVER "Mic, air, and wall cards" |
| 25 Sep | Stereo file as two sources: each source has its own direct pattern and its own FDN | HANDOVER "Two-source image" |
| 26 Sep | Play becomes one C block (`live_stereo`) instead of ~50 ConvolverNodes plus a JS loop | HANDOVER "NOW — Play is one C block" |
| 27 Sep | "Refresh day" list: sample rate follows the stream; denormal guard | HANDOVER "NEXT — refresh day" |
| 28 Sep | K1–K4 and items 5–7 locked (yaw convention, air default, source default, FDN-first faders, diffusion −0.25, headroom trim, colour per rate) | `DECISIONS_LOCKED_2026-09-28.md` |
| 1 Oct | Big-jobs roadmap; S1 Foundations (blob v2, ISO 9613-1 air, mirror fix B, binaural vendoring, goldens) | `BIG_JOBS_ROADMAP_2026-10-01.md` §5 |
| 2 Oct | S2/S3 source radiation; S4/S4b Surfaces materials, Solo/Mute, H·D column signs, DC restore; Shared tail; S7 "z⁻¹ in both" (Play = Render loop) | BIG_JOBS §0, §5; HANDOVER S4b/S7 |
| 3 Oct | S-UI2; S5 (D-UI26 = A, face colour on the tail inject); S5 fix-up; S-MIX desk matrix; D-MIX-J; S-AUDIT (build 51, `WORKLET_VER` 51, wasm `6ebecc333b50`) | HANDOVER copy 4 Oct 06:16; `THURSDAY_LIST.md` |
| 4 Oct | EQ plan locked (Smooth + Movement; FWHT rotation rejected); UI audit; D18–D24, D-UI29–38; Surfaces in the loop D-SL1–9 after Idle's listen ("sounds good, certainly a lot better than flat"); ST-1, ST-2, N11, D-SL10: one default switch | `roadmap/eq_plan/EQ_PLAN.md` §4f; `DECISIONS_LOCKED_2026-10-04.md` |
| 8 Oct (Thu) | Build usage resets 10:28 BST; Thursday sessions T1 → SL7a begin | `NEXT_SESSION_PLAN.md` |

> **In plain English.** In two weeks, from 22 September to 4 October 2026, the program went from a first handover note to build 51: measured microphones, live playback in one fast engine, two-source stereo, accurate air absorption, wall materials, a proper mixing desk, and a long list of fixes, each one decided and tested. On 4 October the next big steps were approved: Smooth and Movement for the tail, and Surfaces-in-the-loop for real wall-dependent decay. Build work resumes on Thursday 8 October.

## 1.5 Where it is going (pointer, not a plan)

The run order T1 → SL7a, and the gated SL7b, live in `NEXT_SESSION_PLAN.md`. This book **references** that plan and never replaces it. In short (VERIFIED from that table):
- T1–T3b, T7–T10: desk, mics and UI, with no change to the main golden (T3b changes MS references only).
- T4 (Smooth) and T4b (ORTF C off): the two sound changes on Thursday that regenerate the main golden.
- T11: Movement (delay modulation), default 0.
- SL1–SL6: Surfaces in the loop, as an opt-in mode with Flat (2011) bit-exact.
- SL7a: preparation and a final four-way A/B. SL7b: the single default switch, only after Idle's written OK.

Beyond that roadmap are ideas Idle has described: non-rectangular rooms, a Studio One plug-in where every track is a source in one shared room, a reverb designer that exports code or variants, and a handover to Ben Supper. These are **PLANNED** and appear in this book only as stubs (Chapters 9–12).

> **In plain English.** The work plan from Thursday has five phases (as summarised for Idle on 5 Oct from `NEXT_SESSION_PLAN.md`): make the desk and mics easy to use; two first sound upgrades (Smooth, ORTF without the centre mic); freer mic placement and tidier screens, ending with Movement; Surfaces as an optional mode; and finally, after Idle has listened and agreed, a single switch that makes the new sound the default while keeping the 2011 sound available. Further ideas (unusual room shapes, a Studio One plug-in, a reverb designer, handing the technology to Ben Supper) are kept in this book as clearly labelled future chapters.

## 1.6 How to keep this book honest

- A chapter is updated **after** the session that changes its subject has landed and been verified, not before (see `README.md` and `STATUS.md`).
- Every number is copied from a source file and the file is named. If a number is not in a source, the book says "not specified" or "open".
- Unbuilt features are labelled **LOCKED** (decided, not merged), **PLANNED** (idea or later session) or **OPEN** (needs a decision).

> **In plain English.** The book only describes things after they have been built and checked. Every number comes from a named file. Anything not yet built is labelled as decided-but-not-built (LOCKED), an idea (PLANNED) or undecided (OPEN), so you can always tell what is real today.

## Open / not yet documented

- The story from 2011 to September 2026 (when the Python and web rebuild started, which tools were tried) is not in the sources read for this draft. Idle may want to add it in his own words.
- An older public document (`/workspace/docs-publish/docs/HOW_IT_WORKS.md`) gives the geometric level as `1/r`; the HANDOVER locks `1/r²` (VERIFIED, 256). The HANDOVER is canonical; the older document is out of date on this point.
