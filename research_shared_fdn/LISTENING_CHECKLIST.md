# Listening checklist: shared tail A/B (Desktop: 2011 Room Reverb\research_shared_fdn\wav\)
All files are 48 kHz / 24-bit, loudness-matched to −20 LUFS (±0.3 LU), peaks ≤ −5 dBFS.

Variants:
- **A** = today (per-mic networks)
- **B** = shared candidate (one loop, per-mic taps, 0.3 ms jitter)
- **C** = shared with no jitter
- **D** = shared with a fixed L/R pattern (not mirror-exact)

"tailonly" files contain the FDN tail alone (no direct or early sound), which makes differences easier to hear. "full" files are the normal mix.

## Listen first (in this order)
1. `1_default_ortf__tailonly__A_today.wav` vs `1_default_ortf__tailonly__B_shared.wav`
2. `2_big_room_ortf__tailonly__A_today.wav` vs `2_big_room_ortf__tailonly__B_shared.wav`
3. `1_default_ortf__full__A_today.wav` vs `..._full__B_shared.wav` (does any difference survive in the normal mix?)
4. `2_big_room_ortf__full__A_today.wav` vs `..._full__B_shared.wav`

Then:

5. `1_default_ortf__tailonly__B_shared.wav` vs `..._C_shared_nojitter.wav` (what the jitter does: C should sound narrower or "phasier" up top)
6. `3_binaural_default__tailonly__A` vs `B` and `4_binaural_big__tailonly__A` vs `B` on headphones. Measured: B misses the head-IC target, so expect a narrower in-head image.
7. `5_symmetric_hall_mono_tail__tailonly__A_today` vs `D_shared_fixeddecor` (today's tail is exactly mono here; D is not)

## What to listen for (score each pair: A better / same / B better, plus a note)
- [ ] **Width / envelopment** of the tail: does B collapse toward the centre, or get wider? Headphones and speakers.
- [ ] **Image stability:** does the tail wander, or pull to one side? (L/R balance measured within 1 dB.)
- [ ] **Tone of the tail:** default room B measured +2 dB at 125–500 Hz and −2 to −3 dB at 4–8 kHz. Is it warmer or duller? Big room: within ±1.2 dB.
- [ ] **Decay length:** B has a slightly longer bass tail in the default room (250 Hz T30 +6 to +11 %, closer to the dial). Listen on the clicks and on the hard stop of the long chord.
- [ ] **Metallic ring / flutter / comb colour** on clicks and pink bursts (B and C).
- [ ] **Early-to-tail join:** any gap, double hit or "flam" on the clicks? The FDN copy of each image moves by about 0.5–1 ms in B.
- [ ] **Mono fold-down:** sum L+R (mono button) and compare A vs B. Is there any extra comb filtering or level change?
- [ ] **Binaural (headphones):** externalisation and width of the tail, A vs B.
- [ ] **Symmetric hall:** does A's mono tail bother you? Is D acceptable? (This feeds decision D4.)

## Notes
- The WAVs come from convolving the dry file with each build's Play impulse response (same wasm and driver as Play). They are not real-time Play captures; Play is linear below its soft limiter (ASSUMED).
- To try your own dry file, run `wav/make_ab.py` after replacing `dry_test_48k.wav`.
