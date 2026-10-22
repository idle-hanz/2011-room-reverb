# Chapter 10 — One shared room in Studio One

> **Status: STUB, expanded 2026-10-05 — PLANNED (design research only, no plug-in code).**

**Chapter purpose.** Idle's vision: the reverb as a plug-in on many Studio One channels, all instances living in the **same virtual room**, moved and controlled from one place in 3-D. This page summarises the existing design study so the chapter can grow when a prototype exists. It is after the roadmap, not part of T1→SL7b.

**Sources:** `/workspace/build_support/research/studio_one_plugin/DESIGN.md`, `GROK_BUILD_BRIEF_Plugin_prototype.md`, `SOURCES.md`; `roadmap/THURSDAY_LIST.md` L4, L6.

> **In plain English.** Normally, if you put a reverb on five tracks in a song, you get five separate reverbs that know nothing about each other, each pretending to be its own room. Idle's idea is the opposite: every track's plug-in is a *window onto the same room*. Drums, bass, guitar and vocal become dots in one 3-D room, and from one screen you drag them around: the vocal forward, the drums back left. Each instrument then gets the echoes it would really get from that spot, and they all share one tail, the way instruments in a real live room all excite the same air.

## The proposed shape (from DESIGN.md; tags as given there)

- **Architecture A (recommended):** a *Source* insert on each track renders direct + early for that instrument and sends to one *Room* instance that runs **one** Hadamard FDN per L/C/R bus. The host's own send graph keeps latency and bounce/freeze behaviour normal.
- **Registry:** an in-process singleton keyed by `(documentID, roomId)` with versioned RoomState/SourceState; a bridge thread links to the web tweak app as the central editor.
- **A deliberate change from 2011:** with many sources and one FDN, the line delays cannot follow every source, so the shared FDN uses **room-fixed delays**. This must be flagged to Idle and A/B-tested against per-instance engines (P2).
- **Formats:** VST3 SDK (MIT since 3.8) first, CLAP (MIT) second.
- **Prototype phases:** P0 singleton proof → P1 registry + bridge → P2 audio A/B → P3 Studio One hardening → P4 CLAP + heavy offline export.
- **Prerequisite:** one C core for Play, Render and plug-in (J2 / L4, C migration).
- **Prior art checked** includes linked-instance designs (Fiedler Beam/Composer, FLUX SPAT LAP, Audio Ease 360pan, 2CAudio Precedence + Breeze). So "one shared room" is not entirely new; this design's twist is the 2011 geometry engine behind it (ASSUMED judgement).

## A session in Studio One, as it might look (PLANNED, plain English)

*An illustration of the intended workflow from DESIGN.md's architecture, not built behaviour.*

1. You put the **Source** version of the plug-in on each instrument track, and one **Room** version on an FX channel.
2. Each Source works out its own instrument's direct sound and early echoes from where that instrument stands, and sends the sound on to the Room.
3. The Room runs one shared tail for everyone.
4. You open the room editor (the familiar web screen) and see every track as a named dot. Dragging a dot updates that track's echoes live.
5. Saving the song saves the room and all positions with it. Freezing or bouncing behaves like any normal plug-in.

**The trade-off Idle should know about.** In the 2011 design each tail corridor is exactly as long as one echo from *the* source. With many sources sharing one tail, the corridors can't match every source at once, so the shared tail would use corridor lengths fixed by the room, not by each source. That is a deliberate change from 2011, and the plan is to A/B it against giving every instrument its own full engine (DESIGN.md §3.2, prototype step P2).

**Has it been done?** Linked plug-ins that share one space exist (DESIGN.md lists Fiedler Beam/Composer, FLUX SPAT, Audio Ease 360pan, 2CAudio Precedence + Breeze). What would be distinctive here is the engine behind it: a geometric room with mirror-image echoes, real wall materials and modelled microphones (ASSUMED judgement).

## Partitioned convolution (Idle's and Ben's idea, L6)

In plain words: instead of running the whole room engine live, each plug-in could just apply a pre-rendered echo fingerprint (convolution). Long fingerprints are expensive to apply in one go and would add delay, so the usual technique is to cut the fingerprint into short slices and process them in parallel, so that the sound starts immediately and the cost is spread out (this is a general description of the well-known technique, ASSUMED background; Ben mentioned it to Idle). Each instance could then be very cheap, with an offline full-quality render available when needed. Being one IR snapshot, it **cannot carry Movement exactly**; options are no modulation or a few cross-faded IRs (VERIFIED as noted in THURSDAY_LIST L6). No code or benchmark exists.

## Open / not yet built

Everything. Studio One multi-Session behaviour (H9) and effect multi-outs (H10) are ASSUMED and need testing.
