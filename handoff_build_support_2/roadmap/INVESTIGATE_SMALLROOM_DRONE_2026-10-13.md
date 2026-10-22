# Small-room low-mid drone and guitar clip (2026-10-13)

Read-only. Nothing in `software\` was edited. No re-pin.

**Verdict.** Shrinking the boot room on the page pins the source and the stand to the walls, collapses the ORTF pair onto one point, and leaves Decay locked at 1.8 s. The guitar then sits on a few repeated short image delays (3.06 ms in the 2 m room, five lines on the same length) and the tail adds up until the limiter takes 10 dB. The loop never reaches gain 1. Proximity stays off. Smooth is holding the ring back. Surfaces, if it is on, makes the bass longer.

## How it was measured

Boot page, not an empty engine body. ORTF 17 cm, ±55°, centre off, Shure SM57 measured colour, Decay lock 1.8 s, Smooth on, humidity 0.35, air one-pole mix 0, ISO shelves on. FDN fader at the 0 dB travel. Direct, early, and dry are down. Proximity ticks stay on. `c` = 340.

Room order is the page chip, W × L × H. Boot is 6 × 8 × 3 m. Steps are 4.5 × 6 × 2.8, 3 × 4 × 2.5, and 2 × 2.5 × 2.2. Typing a size on the page clamps; it does not scale. `RoomMath.clampRoom` and `clamp_body` both pin a coordinate to the new wall, and Space falls to 0 when the stand X sits on a side wall.

Render is `render()` at 48 kHz, the same arguments as `POST /api/render`. Each case is an impulse, then the first 8 s of `roadmap/robotic_1240/test_guitar_dualmono.wav` (already 48 kHz, excerpt peak −2.59 dB) convolved with that IR, then the same soft knee (identity through ±0.95). The IR carries the usual 50 ms end fade. T60 is the T20 slope (−5 to −25 dB) extended to 60 dB, octaves 63 Hz through 2 kHz, fade left out. Play audio was not run. The Play pack is `live_fdn_params` on the same body: same delays, same `1/√32` loop, same line losses, same makeup figure.

The internal Play/Render lock trim (about −4.5 dB on the FDN send) is on at every locked size. It does not explain the growth.

## What the shrink does

| Room | Where things land | Mic distance | Makeup | Shortest delay | Guitar peak | Limiter | Low-mid vs presence |
|---|---|---|---|---|---|---|---|
| 6×8×3 boot | nothing on a wall, Space 0.17 | 3.28 m | +1.93 dB | 9.65 ms, one line, 104 Hz | −7.06 dB | off | −6.5 dB (dry is −8.3) |
| 4.5×6×2.8 | still inside, Space 0.17 | 3.28 m | +0.81 dB | 9.65 ms | −2.90 dB | off | −6.8 dB |
| 3×4×2.5 | source on the back wall, stand on the side wall, Space 0 | 2.55 m | −5.53 dB | 7.50 ms × 5 lines, 133 Hz | −0.13 dB | 0.04 dB, 9 samples | −8.6 dB |
| 2×2.5×2.2 | source in the corner, mics stacked on the side wall, Space 0 | 1.04 m | −2.14 dB | 3.06 ms × 5 lines, 327 Hz | +10.02 dB | 10.03 dB, 321374 samples | +1.4 dB |

Low-mid vs presence is the level of 80–400 Hz minus 400–4000 Hz while the guitar is sounding. The dry file is −8.3 dB. A move toward positive is the drone.

Mean image delay: 29.2 ms, 22.0 ms, 15.8 ms, 10.9 ms.

Nothing is outside the room after the clamp. Before it, the 3×4 room has to pull Z from 4.75 m back to 4 m. The 2×2.5×2.2 room pulls source X 2.6→2, source Z 4.75→2.5, and stand X 3→2. No mic distance falls under 0.5 m, so the proximity shelf is not in the pack. Ticking the boxes off changes nothing.

## Octave T60 (Flat, lock on)

| Room | 63 | 125 | 250 | 500 | 1 kHz | 2 kHz |
|---|---|---|---|---|---|---|
| 6×8×3 | 1.29 s | 1.83 s | 1.83 s | 1.75 s | 1.79 s | 1.85 s |
| 4.5×6×2.8 | 1.14 s | 1.49 s | 1.65 s | 1.79 s | 1.83 s | 1.85 s |
| 3×4×2.5 | 0.51 s | 1.69 s | 1.66 s | 1.78 s | 1.78 s | 1.85 s |
| 2×2.5×2.2 | 0.56 s | 0.93 s | 1.48 s | 1.76 s | 1.85 s | 1.79 s |

On Flat the longest band is the top of the table, about the 1.8 s dial. 63 Hz gets shorter as the room shrinks. The complaint is not a 60 Hz mode that will not die. It is a few hundred hertz, held for the whole 1.8 s, and piled up by the corner.

Narrow peaks, width about 1.2 Hz:

- Boot: 160 Hz rings 2.80 s, 207 Hz rings 2.22 s. The default room already has narrow rings. They are quiet (guitar −7 dB).
- 4.5×6×2.8: 431 Hz rings 2.51 s, near the Y axial 425 Hz (`c/2H`, H = 2.8). 321 Hz rings 2.00 s.
- 3×4×2.5: 387, 571, 1001, 1264, 1316 Hz, each about 1.9–2.0 s. The five-fold 7.50 ms delay (133 Hz) is real; it is not the tallest narrow peak.
- 2×2.5×2.2, Smooth on: tallest narrow peaks are 704, 1206, 1910, 1995 Hz, each about 1.9–2.4 s, plus 227 Hz at 1.75 s. The five-fold 3.06 ms delay is 326.5 Hz. It becomes obvious once Smooth is off (974 Hz, the third harmonic, 2.04 s) or Surfaces is on (330.5 Hz, 2.64 s, within 4 Hz of 326.5).

First axials, `c/(2·dim)`: boot 28.3 / 56.7 / 21.3 Hz (X/Y/Z). At 3×4×2.5 they are 56.7 / 68 / 42.5 Hz. At 2×2.5×2.2 they are 85 / 77 / 68 Hz. The engine’s only room-tone cut is 1.5 dB, Q 1.5, on the first axial, and only on the lines of that axis. It does not touch 327 Hz.

## One change at a time (2×2.5×2.2 unless said)

**Proximity off.** Already idle at 1.04 m. No second render. Not the cause.

**Smooth off.** Worse. Guitar +23.1 dB, limiter 23.1 dB, 679897 samples. The 3.06 ms line’s third harmonic at 974 Hz rings 2.04 s. Smooth is damping the comb. It is not the source of it.

**Surfaces instead of Flat.** Worse, and this is the long low-mid. Guitar +12.6 dB, limiter 12.6 dB, 482402 samples. Octave T60: 63 Hz 3.29 s, 125 Hz 3.00 s, 250 Hz 2.68 s, 500 Hz 2.05 s, 1 kHz 1.66 s, 2 kHz 1.17 s. Narrow peaks: 164 Hz at 3.17 s, 226 Hz at 3.16 s, 331 Hz at 2.64 s. The 60–300 Hz share of the tail rises from −13.5 dB under the broadband tail (Flat) to −3.7 dB.

The same pattern is already there at 3×4×2.5 with Surfaces on: guitar +2.63 dB, limiter 2.63 dB, 35157 samples, 63 Hz T60 3.26 s, a 120 Hz peak at 4.25 s, and 40.7 Hz at 3.59 s next to the Z axial 42.5 Hz. Flat at that size only kissed the knee (9 samples).

D-SL3 drops an axis whose first mode is at or above 30 Hz. Every axis of both small rooms is above 30 Hz, so `surf_keep` is `[0, 0, 0]`. The 1.5 dB axial cuts are removed, and the three biquads per line still run, anchored at 1.8 s. Worst loop gain is −0.055 dB (2 m room) and −0.135 dB (3×4). Under 0 dB, so the guard leaves Surfaces on. Flat is still the boot default. Surfaces is a second cause only when that chip is on.

**Decay lock off,** same clamped 2 m room, Structure Gain still 1. Trip gain falls to 0.177 (−15.1 dB). Octave T60 is 0.14–0.29 s. Guitar −2.0 dB, limiter off, low-mid balance −6.6 dB. The 3.06 ms delays are still in the tank. They no longer ring, and the note no longer stacks into the knee. Makeup on this law is +8.7 dB and the impulse peak is hotter (−2.2 dB against −15.9 dB locked). The clip was the locked tail adding up, not one loud sample.

**Interior control,** not what the page does. The same 2×2.2×2.5 m room with source and stand scaled to the boot fractions, Space left at 0.17, nothing on a wall. Distance is still about 1.04 m, and one line is still 3.06 ms, but the delays are almost all different. Makeup falls to −12.8 dB because the small-room images at the reference point are loud. Guitar −6.1 dB, limiter off, low-mid balance −10.6 dB (less bass-heavy than the dry file). 1 kHz T60 is still 1.81 s. A small room with people kept off the walls does not clip this guitar and does not flip the low-mid balance. The page’s clamp does both.

## Does g reach 1?

No. Decay lock runs the loop at `1/√32` and puts the loss on the line, `10^(−3·delay / (sr·1.8))`. That product is 1 times the line loss.

On the shortest line of the 2 m room the loss is 0.988 (−0.10 dB) at 1 kHz. With the axial cut and the air shelves it is −1.53 dB at 63 Hz and −0.16 dB at 250 Hz. Every probed band from 63 Hz to 1 kHz stays under 1. The 3×4 room’s shortest line is 0.972. Boot is 0.964.

`g_decay` (the gain makeup sees, before the loop is replaced by `1/√32`) moves only from 0.158 to 0.170 as the mean delay shortens. It is capped below `0.99/√32`.

Surfaces’ worst frequency is −0.055 dB in the 2 m room. Close, still under 0 dB, not a runaway.

## Why the level moves

Makeup is frozen at the boot offset from the stand (source 2.6, 1.2, 4.75 minus stand 3.0, 1.5, 1.5). That reference stays about 3.3 m from the stand even after the stand is pinned to a short room, because the offset is +3.25 m in Z and Z is not clamped inside `makeup_at_stand`. The live source is what got clamped, down to 1.04 m.

Live 1/r from 3.28 m to 1.04 m is +9.9 dB. Makeup only moves from +1.93 dB to −2.14 dB. The rest of the +17 dB on the guitar (from −7.1 to +10.0) is the tail: five copies of a 3 ms delay, fed by a source in the corner, held for 1.8 s, summed across an 8 s note. The impulse itself only rises from −20.5 dB to −15.9 dB and does not hit the knee. The note does, for 321374 samples.

At 4.5×6×2.8 nothing has moved and the impulse peak is unchanged, but the guitar is already +4.2 dB. Mean delay dropped 7 ms and makeup gave back 1.1 dB. Shorter images integrate harder. That is the same mechanism, before any wall is hit.

## What to change (not built)

The clip and the low-mid flip need two different decisions. A level cap without a shorter ring still leaves a 1.8 s comb. A shorter ring without a level change still leaves the corner about 10 dB up on 1/r.

1. **Stop pinning the scene to the wall when the box shrinks.** Scale the source and the stand with the room, or refuse the size until they are moved inside, and do not let Space fall to 0. The interior control is the evidence: same box, guitar −6 dB, no limiter, no low-mid flip. This changes what a size edit posts. It does not by itself retune 1/r or the 0.55 direct fold.

2. **A makeup ceiling, or a makeup that notices a clamp.** D-MAKEUP-FREEZE and D-SRC-DIST-LEVEL are locked: makeup is the boot offset, and it must not follow the live source on a normal move. A ceiling that never fires on the boot stand (makeup there is +1.9 dB, guitar −7 dB) would catch the +10 dB case. It would not remove the 327 Hz comb. Flag both locks. Needs a yes before it touches a golden.

3. **Do not hold 1.8 s on a tank whose delays have collapsed.** Five lines at 3.06 ms with a per-trip loss of 0.10 dB is the ring. A small-room exception (shorter dial, or a floor on line loss once the delay is under about 8 ms) fixes the drone. The lock-off render is the evidence: T60 under 0.3 s, guitar −2 dB, limiter off. This is a decay-lock change. The retired `0.68/√N` cap is a different lever and stays retired. Needs a yes.

4. **Room-tone cuts in front of the tank, on the harmonics, not only the first axial.** The 2011 cut that is in the tree is 1.5 dB at `c/(2·dim)` on one third of the lines. In these rooms those frequencies are 43–85 Hz, and D-SL3 then deletes them because they are above 30 Hz. The heard ring is 327 Hz and its multiples. Cuts there would be a sound change, including on the boot room’s 160 Hz peak (already 2.8 s). Needs a yes.

Leaving Smooth on is the right default. Turning Surfaces on in a small room is the wrong fix: it lengthens 63–250 Hz past 2.5 s and clips harder. Proximity does not need a change for this report. No distance was under 0.5 m.

A dense mix can hide a 1.8 s comb that a solo guitar does not. That part was not rendered. The guitar numbers above were.
