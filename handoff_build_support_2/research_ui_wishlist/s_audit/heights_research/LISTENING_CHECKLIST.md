# D-AUD-6 per-mic heights: guitar listening checklist (box research, 3 Oct 2026 19:35–19:55 BST)

**Render only, box only.** These are not Play files. Dry = `roadmap/robotic_1240/real/dry_est_0.001.npy` (44.1 kHz → 48 kHz), first 20 s. Room = the standard measure body `roadmap/s4_verify_1140/measure/client_body_1140.json`:
- 6 × 3 × 8 m, ORTF 0.17 m, Measured SM57, stand height 1.5 m, source height 1.2 m;
- all buses on.

**before** = today's engine, where heights are ignored and every capsule sits at 1.5 m.
**after** = box prototype `hpatch.py`, where each capsule sits at its own height.

Every pair is **level-matched** (after scaled to before's RMS; the trim is listed), so you hear colour and image, not loudness. Each pair shares one normalisation; all files are −22.2 dBFS RMS. All numbers are VERIFIED (box, `guitar_heights.json`, `h1_ctx.json`).

| Pair (files `<pair>_before.wav` / `<pair>_after.wav`) | Heights L / C / R (m) | Trim to match | Worst early ⅓-oct Δ | Worst tail ⅓-oct Δ |
|---|---|---|---|---|
| `pair_up_0p5` | 2.0 / 1.5 / 2.0 | −0.31 dB | 8.4 dB | 3.9 dB (full model) |
| `pair_up_0p5_after_H1.wav` (same before) | 2.0 / 1.5 / 2.0 | +0.36 dB | 9.2 dB | **0.42 dB** (H-1) |
| `tilt_lr_0p6` | 1.2 / 1.5 / 1.8 | −0.44 dB | 9.9 dB | 3.9 dB (full model); H-1 0.24 dB (no WAV) |
| `pair_up_1p0` | 2.5 / 1.5 / 2.5 | +2.33 dB | 8.7 dB | 4.6 dB (full model) |

The full model and H-1 differ in what follows the capsule heights:
- **Full model:** FDN line lengths, line diffusers and line air also follow each capsule's own height. This is what today's code does when the whole stand moves: raising the whole stand 0.5 m moves the tail by up to 3.9 dB in single bands, VERIFIED `ref_stand_up_0p5`.
- **H-1 (recommended):** only the direct sound, the early reflections and the per-bus inject levels follow the capsules. The FDN lines keep the stand height.

## Listen for
1. **pair_up_0p5, before vs after (full model).** The early colour changes: a floor/ceiling comb moves, deep notches near 2 kHz and 6.3 kHz on L, and R is brighter at 8–12.5 kHz. The tail also shifts in the low bands (250 Hz up to −3.9 dB on R). Does it sound like "mics higher up", or just "a different room"?
2. **pair_up_0p5, before vs after_H1.** The same early change, but the tail stays within 0.42 dB. Listen in particular to the decay after chord stops: it should sound like the same room.
3. **tilt_lr_0p6.** L is lower and R higher. Direct L arrives 2 samples earlier and R 6 samples later (VERIFIED: direct sample index L 463→461, R 466→472). The early L/R correlation drops from 0.435 to 0.394. Does the image tilt or widen? Is it unpleasant?
4. **pair_up_1p0** (extreme, outriggers 1 m above C, 0.5 m under the 3 m ceiling). The direct arrives about 0.7 ms later on the pair (+33 samples), and the matched output is 2.3 dB quieter before the trim. Check the comb in the 2–6 kHz region and whether the guitar sounds "distant/thin".
5. Mono check: sum each after file to mono and listen for new comb-filter "phasiness" compared with before.

## Verdict boxes (Idle)
- [ ] Heights are audible and useful
- [ ] Prefer H-1 (stable tail), or [ ] prefer the full model (tail follows the capsules)
- [ ] The extreme case is acceptable, or [ ] cap the height difference (e.g. ±1 m from C)
