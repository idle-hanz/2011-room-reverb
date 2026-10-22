# Listening checklist: sound tricks A/B (box prototypes, 4 Oct 2026)

All files are 24-bit, 48 kHz stereo. They are matched to equal RMS within each group, then one shared gain takes the group to −1 dBFS peak (`ab_levels.json`).

**Scene:** default room (6 × 3 × 8 m, dial 1.8 s), ORTF with C off (N18 locked) and SM57s. Faders are as in the UI body, so the FDN carries direct and early in its first pass. Render path, convolved with the dry guitar (12 s) and with two snare hits 1.5 s apart.

## Group 1: Natural decay (frequency-dependent T60 in the loop)
| File | What changed |
|---|---|
| `1_natural_decay__*__A_today_flat.wav` | Today: every band decays at 1.8 s |
| `1_natural_decay__*__B1_air_in_loop.wav` | Air absorption (ISO 9613-1, 20 °C / 50 % RH) inside the loop. 1 kHz stays at the dial, 4 kHz 1.42 s, 8 kHz 0.88 s |
| `1_natural_decay__*__B2_air_plus_surfaces.wav` | Air plus the default surface cards. Bass up to 1.25× (2.25 s), 2 kHz 1.10 s, 8 kHz 0.50 s |

Listen for:
1. **Fizz and hiss in the tail.** Does A have a bright, splashy "digital" tail on the snare that B1 removes?
2. **Natural darkening.** Does the tail get warmer as it dies, like a real room (B1)? Or too dull (B2)?
3. **Bass bloom.** Does B2's longer low end muddy the guitar?
4. **Length.** Does the overall length still sound like 1.8 s?
5. **Clarity of the attack.** Is it unchanged? It should be, because the first pass is identical.

## Group 2: Direct level (direct-to-reverb ratio)
| File | DRR (L) | What changed |
|---|---|---|
| `2_direct_level__*__A_today.wav` | +6.7 dB | Today |
| `2_direct_level__*__B_direct_minus9dB.wav` | −2.3 dB | First arrival 9 dB down; reflections and tail as they are |
| `2_direct_level__*__C_direct_minus18dB_physical.wav` | −11.3 dB | About what physics predicts for a cardioid 3.3 m from the source in this room (Barron) |

Listen for:
1. **Distance.** Does A sound close-miked with reverb added, while B and C sound like mics in the room?
2. **Envelopment.** Is the room around you or behind the source?
3. **Usability.** Is C too washy for a mix? Is B the sweet spot?

**Setup:** fixed moderate level, headphones and monitors. Play each file twice and swap the order. Use blind ABX where you can (for example, foobar2000 ABX).

**Scoring:** none / slight / clear.

| | A | B1 / B | B2 / C |
|---|---|---|---|
| Group 1: fizz removed | ref | | |
| Group 1: natural darkening | ref | | |
| Group 1: bass bloom | ref | | |
| Group 2: distance / realism | ref | | |
| Group 2: usable in a mix | ref | | |
| Rank | | | |

**Decision rule**
- Group 1: adopt B1 if it is preferred or equal and no "dull" note appears. B2 needs a clear preference to justify its cost.
- Group 2: listening only. Locked D22 says the Physical level law stays opt-in, so a preference for B or C argues for revisiting D22, not for switching it silently.
