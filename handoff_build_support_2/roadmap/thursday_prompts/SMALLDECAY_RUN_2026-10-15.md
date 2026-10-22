# SMALLDECAY RUN 2026-10-15 (D-SMALLROOM part 2). Run ONLY after ROOMTONE has landed.
Read DECISION_SMALLROOM_2026-10-15.md, the ROOMTONE landing, and INVESTIGATE_SMALLROOM_DRONE_2026-10-13.md (the lock-off render: T60 < 0.3 s, no limiting).

## Step 0: REVIEW ONLY (plan mode). Answer against the real code:
1. How the decay lock sets 1.8 s today (decay_lock, g_decay, structure_gain_for_rt60) and why it holds that in a tiny room.
2. Options for a physical exception: (a) cap the target T60 at a Sabine/Eyring estimate from the room's volume and surface and the materials, (b) a minimum loss per line once a delay is under about 8 ms, (c) a blend. Which is most natural and the least invasive? Does the boot room (6x3x8 m) stay bit-exact under each?
3. The UI: does the Decay dial show the capped value (honest display)? Play and Render the same? Wasm change?
4. The interaction with makeup (decay-lock g feeds the makeup), Surfaces and ROOMTONE.
5. The test plan: T60 per octave and the peak/limiter on the three small rooms and boot; listens.
6. Conflicts with locked decisions (the decay lock IS one; Idle has approved an exception, but report the exact scope).

## Step 1: BUILD (fresh session, after the corrections). Backup first, build, measure, listen files to roadmap\smalldecay\listen\, full suite, goldens bit-exact or STOP, HANDOVER pin + build log.

## LOCATION NOTE (2026-10-16): there is no function named decay_lock; find where the decay-lock g (g_decay) is set by search.

## UPDATE 2026-10-16 (after the ROOMTONE STOP)
ROOMTONE is in the tree at WORKLET_VER 56 (wasm be47a60a...), the bit-exact gates held, the suite is green, but it is STOPPED on CPU: the decay-8 cube, two sources, colour + Surfaces on, shared off = 2.582 ms > 2.40 ms. Idle listened: the depths sound the same; the HIGH ringing (about 860 Hz to 2.6 kHz, about 2.2 to 2.6 s) distracts and clouds everything. The fix that matters is this run.
Part A (finish ROOMTONE, no sound change): skip the muted centre tank's processing when it is not heard (shared off and centre muted), both engines; if still > 2.40 ms, cap the harmonic stages per line (report). Keep HARM_Q 8 / HARM_DB -0.3. The bit-exact gates are the same as ROOMTONE's.
Part B (SMALLDECAY): a small room's decay is capped at a physical estimate per octave (Eyring/Sabine from V, S and the surface absorption, plus air absorption), so highs die faster than lows; the target is that the 1-4 kHz ring in 3x4x2.5 and 2x2.5x2.2 m falls well under 1 s. The boot room (6x3x8) and all the goldens stay bit-exact (the cap does not bind there), or STOP with the size of the change. The Decay dial shows the honest capped value. Also report the 3x4x2.5 clipping (+3.9 dB) after the change.
Listens: the same guitar and rooms, before/after, to roadmap\smalldecay\listen\.


---

## ROUND 1 REVIEW ACCEPTED + IDLE DECISION (2026-10-17)

The Step 0 review (2026-10-17) is accepted. Idle chose: **the physical ceiling applies in every room, including the boot 6x3x8 room, and he listens to the boot room before anything is locked.** This overrides the "boot room stays bit-exact" line in D-SMALLROOM item 2 and the flat-1.8 s part of the decay-lock default, but only through the gated rollout below. All other decay-lock parts (lock on, 1/sqrt(N) loop, no 0.68/sqrt(N) cap) stay.

### Mechanism (Part B, replaces the earlier wording where they differ)
1. Per-octave ceiling: `T_eff(f) = min(dial, T_phys(f))`, where `T_phys` comes from `surf_target.room_target(W, H, L, cards, 0.35, bands)` with the current cards, humidity 0.35, air included. Do not invent a new model.
2. Put it in ONE shared function, called by `live_fdn_params` and all three Render branches (two-source still, single-source, movement). Play and Render must not split.
3. Apply it in the loop per octave, preferably through the existing Surfaces section path (a pack change, no new opcode). If that cannot be done without a new opcode or a wasm change, STOP and report what is needed.
4. `g_decay` and the makeup stay computed from the armed dial. Do not recompute makeup from the capped time.
5. ROOMTONE's Schroeder ceiling keeps using the armed dial, so the set of cuts does not change. HARM_Q 8 and HARM_DB -0.3 stay.
6. Render length (`planned_fdn_ms`) keeps using the armed dial. The tail dies inside the file.
7. Surfaces: `make_spec` keeps anchoring to the armed dial (SL2/SL3 unchanged). With Surfaces on, the per-octave result is `min(Surfaces curve, T_phys)`. If that needs a design choice beyond this, STOP and report.
8. The dial: the knob keeps the user's request and is never overwritten. Add a read-only readout beside it showing the capped 500 Hz-1 kHz value and the octave row (63 Hz-4 kHz).

### Gated rollout (this is how "listen before locking" works)
- Add a server key `phys_ceiling`, **default OFF** in this build. With it off, everything is bit-exact: the five TLAW goldens, GOLDEN_META 883cc7329582c21532fb44dbd040145e0ce7bc6e, both live MD5s (af2b154a..., f30665f4...). Any move with it off is a STOP. Bump WORKLET_VER / app.js only if a file the browser loads actually changed, and report it.
- Listens are rendered with `phys_ceiling` ON. Do NOT flip the default and do NOT re-pin goldens in this run. Flipping the default and re-pinning is a later run after Idle listens.

### Part A first
Do Part A (skip the muted centre tank, no sound change) before Part B, with its CPU measure. The CPU stop rule stands: the decay-8 cube must be at or under 2.40 ms shared-off, both with `phys_ceiling` off and on. If it is still over, follow the harmonic-cap fallback in UPDATE 2026-10-16, and if it is still over after that, STOP.

### Listens and report (to roadmap\smalldecay\listen\)
Same guitar, same first 8 s convolution as ROOMTONE. Rooms: boot 6x3x8, 4.5x6x2.8, 3x4x2.5, 2x2.5x2.2, at the PLACE positions. Flat, lock armed at 1.8 s, early 0, direct 0. For each room, a before (`phys_ceiling` off) and after (on) file, named clearly. The boot room pair is the one Idle must hear.
Report per room, off and on: octave T60 at 63, 125, 250, 500, 1k, 2k, 4k Hz; decay of the tall narrow peaks 800 Hz-4 kHz; guitar peak, limiter dB and limiter sample count; `line_t60`, `g_decay`, makeup. One small room in both Play and Render to show they match. One Surfaces-on pass showing whether 63-250 Hz is still stretched. CPU numbers as above.

### Next
Run a Round 2 review of this block (plan mode, no edits) before Step 1, in a fresh session.


---

## ROUND 2 REVIEW ACCEPTED (2026-10-17) - binding for Step 1

1. `line_t60` stays the armed dial at all four sites. The shared function returns a section pack (or nothing when `phys_ceiling` is off); it does not replace those assignments. `g_decay`, makeup, `planned_fdn_ms` and `harmonic_pack` keep reading the dial.
2. Per-octave target loss is 60 / T_eff(f), T_eff = min(dial, T_phys). Never pass raw T_phys (that would stretch boot bass to ~2.6 s). Expected boot: 125/250 Hz stay 1.8 s, capped 500 Hz-1 kHz mean ~1.41 s, 2 kHz ~0.87 s, 4 kHz ~0.64 s.
3. Surfaces on: ONE cascade whose loss is the greater of the anchored Surfaces rate and the physical rate. No second stacked cascade. Coefficients designed at pack time, not inside the block. Cache the movement branch by delay; it calls the same function.
4. room_target as specified (cards, 0.35, air on, arau_scatter, c 343); FDN delays stay on c 340. 63 Hz clamps to the 125 Hz absorption. Report any fitter fallback to identity, especially on short lines. The measured T60 is the result that counts.
5. With the key off, `live_fdn_params` must not grow ANY key (the live MD5s hash the whole dict). Serve the octave preview row from a separate endpoint. With the key off the knob and decay hint stay on the armed dial; with it on, the single readout is the mean of capped 500 Hz and 1 kHz.
6. Part B needs no wasm change. Part A does: bump WORKLET_VER and update the asserts in `tests/test_quick_pins.py` with it. That is not a golden re-pin; the five TLAW goldens, GOLDEN_META 883cc732... and both live MD5s must stay identical.
7. Part A: skip the centre tank when its speaker contribution is 0 and shared tail is off (not `cEmpty`, which never fires on the current mute). Accepted side effect: unmuting the centre starts its tail cold. Static renders must stay identical.
8. If the cube is still over 2.40 ms after Part A, lower HARM_MAX per axis (no per-line budget, no new wasm work). This is a sound change already allowed by UPDATE 2026-10-16. If any bit-exact gate moves, including `small_lock08`, STOP.
