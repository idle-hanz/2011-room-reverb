# Listening checklist: delay modulation and Dffs cap prototype (box only)

The FWHT rotation (`../proto_rot/`) was rejected: no audible difference.

Files are 24-bit, 48 kHz, matched to equal RMS, then one shared gain to −1 dBFS peak. All are the default room, FDN tail only (no direct, no early, colour Bypass). The guitar runs **through** the loop, so any wobble is real.

| File | What changed |
|---|---|
| `default_guitar_before.wav` | Today's engine (reference) |
| `default_guitar_mod10.wav` | Delay modulation: 0.10 ms peak, 0.7 Hz × 0.6–1.4, 16 of 32 lines, allpass interpolation |
| `default_guitar_mod15.wav` | Same at 0.15 ms (stronger) |
| `default_guitar_dcap.wav` | Diffuser gain capped at 0.7 only (no modulation, still LTI) |
| `default_guitar_mod10dcap.wav` | mod10 + Dffs cap |

**Setup:** headphones and monitors at a fixed, moderate level. Play each file at least twice, swap the order, and use blind ABX where you can. Compare each file against `before` first, then `dcap` against `mod10dcap`.

**Listen for**
1. **Metallic ring.** Is the tin-can or picket-fence tone in the note decays weaker? Focus on 700–800 Hz, 1.3 kHz and 2 kHz, and the low ring around 157 Hz and 261 Hz.
2. **Pitch wobble or chorus.** On sustained notes and the final chord: any seasickness, beating or chorusing? The most likely file is mod15.
3. **Swirl.** Slow changes in brightness or width, with a period of roughly 1–2.5 s.
4. **Decay length.** Does any file sound shorter or longer? See the T30 figures in `proto_mod.json`.
5. **Tone balance.** Any change in the low end or brightness? The Dffs cap changes the diffuser colour.
6. **Density and smoothness.** Is the tail grainier or smoother? The cap lowers diffusion.
7. **Preference.** Rank the five files.

**Scoring:** none / slight / clear.

| | before | mod10 | mod15 | dcap | mod10dcap |
|---|---|---|---|---|---|
| Metallic ring | ref | | | | |
| Pitch wobble | ref | | | | |
| Swirl | ref | | | | |
| Decay length | ref | | | | |
| Tone | ref | | | | |
| Density / smoothness | ref | | | | |
| Rank | | | | | |

**Decision rule (EQ_PLAN §4)**
- Keep modulation only if the ring is clearly reduced with no audible wobble on sustained notes.
- Keep the Dffs cap if the ring drops and the tail doesn't sound thinner.
- If neither wins on its own, try the combination.
- Any modulation also needs Render to run the loop (§4e).

**Measured numbers:** `proto_mod.json` has the tail peaks, peakiness (noise reference 5.53 dB), T30 per band, and wobble in cents on a 440 Hz sustained tone.
