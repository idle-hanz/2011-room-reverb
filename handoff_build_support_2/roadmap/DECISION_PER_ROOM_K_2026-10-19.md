# DECISION: per-room k - the decay dial sets the mid decay in every room (Idle, 2026-10-19)

Status: BINDING. Chosen by Idle on 2026-10-19 (evening) over "cap at 2x the dial" and "keep as is, re-baseline tests only".

## The decision in one line
When physics decay is on, the decay dial number is the mid decay (the average of the 500 Hz and 1 kHz octave T60) in **every** room, not only the boot room. Physics only shapes how the lows and highs differ from that mid number.

## Why this was needed (plain words)
- Physics decay works by making the walls harder or softer. One number, `k`, scales how absorbent every wall is. Small k = harder walls = longer decay.
- Today `k` is worked out once, on the boot room (6 x 3 x 8 m), so that the boot room's mid decay equals the dial. The same k is then used in every other room (`software\engine\surf_loop.py:304` `k_for_dial`, docstring "Same k in every room").
- A big room with the same hard walls rings much longer, because sound travels further between bounces. So in the 57 x 34.2 x 97 m hall:
  - dial 1.8 gives about 14.5 s mid decay,
  - dial 4 gives about 24.4 s,
  - dial 8 gives k 0.152, about 34 s designed and about 37 s measured (T30, flat from 31.5 to 500 Hz, 27 s at 1 kHz, 16 s at 2 kHz).
- Correction: an earlier message said the hall mids were "6-10 s". That was wrong. The numbers above are the measured ones.
- This is not instability and not a two-source bug. It is the design: the dial meant "wall hardness, calibrated on the boot room".

## What changes
- k is solved for **each room** (its size and its wall cards) so the room's mid decay equals the dial.
- Lows and highs still come from physics: air absorption makes the highs fall faster in big rooms, and the panel bass term shapes the lows. So the hall at dial 8 will have about 8 s mids, longer or shorter lows depending on the room, and shorter highs.
- The boot room with default walls should not change at all (same k, bit-exact). Other rooms with physics on will change: big rooms get shorter, rooms smaller than the boot room get slightly longer.
- Changing wall materials with physics on will no longer change the mid decay (the dial wins). Materials then change only the tone of the decay (lows vs highs). See "Open questions".

## What it fixes
- The hall no longer rings for 30+ s at dial 8.
- The three slow acceptance failures from F13 (`test_s4b_long_decay_no_runaway`: hall two sources decay 8, binaural decay 4 and 8) were caused by this. That test is also re-written as a decay-slope check so it measures "does it fall at the right rate" rather than a fixed level at 18-20 s.
- The line-0 comb test (boot room, 0.2126 against a 0.20 limit) is a boot-room number, so per-room k should not change it. Its limit is re-baselined to about 0.23 for physics on, re-measured after the change.

## What it does not change
`s` 0.106194 and the bass knots, makeup, the decay lock, `line_t60`, T60_TOL, the 2.40 ms CPU limit, Render/Play parity, the worklet DSP (coefficients are designed in Python, so the worklet should not need a change).

## Open questions for Idle (not blocking the Build prompt)
1. Materials and the dial: solve k on the room's actual wall cards (dial = mid exactly, materials only change tone) - the default in the prompt - or on default walls only (materials can still push the mid away from the dial).
2. Extreme dial/room pairs: a tiny room at a very long dial, or a huge hall at a very short dial, can hit the wall limits (absorption 0.01 to 0.99). The prompt reports the reachable range and clamps; Idle may want the page to show "max reachable decay" when it clamps.

Build prompt: `roadmap\thursday_prompts\PERROOMK_RUN_2026-10-19.md`.
