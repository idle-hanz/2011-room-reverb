# Listening checklist: FWHT stage rotation prototype (box only)

Files (24-bit, 48 kHz, level-matched by equal RMS, then one shared gain to −1 dBFS peak):
- `default_guitar_before.wav`: today's engine (default room, FDN tail only: no direct, no early, colour Bypass)
- `default_guitar_rot5.wav`: one butterfly stage at 45° ± 9° (5 % of π), 0.3 Hz
- `default_guitar_rot10.wav`: 45° ± 18° (10 % of π), 0.5 Hz

The guitar goes **through** the time-varying FDN, not through IR convolution, so any wobble you hear is real.
These are wet-only tails, so any ringing is easier to hear than it would be in a mix.

**Setup:** headphones and monitors, at a fixed, moderate level. Play each file at least twice. Swap the order, and use blind ABX if you can (for example foobar2000 ABX).

**Listen for**
1. **Metallic ring.** Is the "tin-can" or "picket-fence" tone in the decay of each note or chord weaker in rot5 or rot10 than in before? Pay particular attention to the 700–800 Hz and 1.3 kHz / 2 kHz area.
2. **Pitch wobble / chorus.** On sustained notes and the last chord's decay: any seasick pitch, beating or chorusing? (rot10 is the most likely to show it.)
3. **Pumping or swirl.** A slow periodic change in brightness or width at about 3 s (rot5) or 2 s (rot10) periods.
4. **Decay length.** Does any version sound shorter or longer? (The measured T30 is within about 5 %.)
5. **Tone balance.** Any change in low end or brightness?
6. **Preference.** Before / rot5 / rot10 / no difference.

**Score each item as: none / slight / clear, per file.**

| | before | rot5 | rot10 |
|---|---|---|---|
| Metallic ring | | | |
| Pitch wobble | | | |
| Pumping or swirl | | | |
| Decay length | ref | | |
| Tone | ref | | |
| Preference | | | |

**Decision rule (from EQ_PLAN §4d):** keep rotation only if the ring is clearly reduced with no audible wobble. The box metrics show only small peak reductions (see `proto_rot.json`), so a "no difference" result is plausible. In that case, move to the backup (delay modulation, allpass reads) and/or the Dffs cap.
