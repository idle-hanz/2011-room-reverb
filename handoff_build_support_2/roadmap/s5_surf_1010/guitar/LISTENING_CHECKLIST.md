# S5 / D-UI26 = A: A/B listening checklist (guitar, Render) — 3 Oct 2026, box, 1010 tree

**Files** (48 kHz stereo 16-bit, first 20 s of `robotic_1240/real/dry_est_0.001.npy` resampled 44.1→48 k with resample_poly 160/147, convolved with a 3 s Render IR of the default client body `client_body_1140.json`):

| Pair | before | after | after level trim (to match the before RMS) | null after−before |
|---|---|---|---|---|
| Default, full mix | `default_mix_before.wav` | `default_mix_after.wav` | −0.18 dB | −27.9 dB |
| Default, tail only (direct + early off) | `default_tailonly_before.wav` | `default_tailonly_after.wav` | −0.74 dB | −25.1 dB |
| All faces HS +6 dB @ 5 kHz, mix | `hs6_allfaces_mix_before.wav` | `hs6_allfaces_mix_after.wav` | −0.17 dB | −26.8 dB |
| All faces HS +6 dB, tail only | `hs6_allfaces_tailonly_before.wav` | `hs6_allfaces_tailonly_after.wav` | −0.74 dB | −23.2 dB |
| Carpet floor (face E absorb .02 .06 .14 .37 .60 .65 .70), mix | `carpet_floor_mix_before.wav` | `carpet_floor_mix_after.wav` | −0.53 dB | −19.1 dB |
| Carpet floor, tail only | `carpet_floor_tailonly_before.wav` | `carpet_floor_tailonly_after.wav` | −2.00 dB | −15.3 dB |

- **before** is the shipped Render (snapshot 1010): the tail gets each face's broadband mean only.
- **after** is Render prototype A (`../protoA_root/software/render_pipeline.py`, box only): each FDN inject line also gets its hit faces' absorb shape (relative to the card mean) and face EQ. The early taps are unchanged (max-abs 0.0).
- Each pair shares one peak normalisation (offset logged in `guitar_ab.json`), so the files within a pair can be compared directly. "after" is RMS-matched to "before", so you hear shape, not level. The un-matched level change is the trim column with its sign flipped: "after" is louder by that much.
- VERIFIED: the numbers above come from `guitar_ab.json`.
- ASSUMED: Play will sound like "after" once S5 is in. No Play "after" exists yet, because the SURF prototype wasm only has identity coefficients.

**Listen for (tick each, then write "prefer before / after / same"):**
1. Default mix: is the tail slightly warmer or darker (about +0.2…+0.5 dB below 1 kHz, about −0.3 dB at 5–10 kHz)? Expect "barely audible". Note whether you can pick A from B blind.
2. Default, tail only: same question, easier to hear. Does the tail sound less "grey"?
3. HS +6 dB on all faces, tail only: before = the tail does **not** brighten (today's bug); after = the tail brightens about +3…+6 dB at 6–16 kHz. Is the after tail what you expect when you turn up a face's treble?
4. Carpet floor: before = the tail loses lows as well as highs (mean absorb only); after = the lows stay and the highs go. Is the after more plausible for a carpeted floor? Is it louder (≈ +2 dB tail, ≈ +0.5 dB mix, before matching)?
5. Any new artefacts in "after" (ringing, a metallic tail, pre-echo)? Expected none: the filter is feed-forward, outside the loop.
6. Overall verdict for D-UI26 = A as shipped in S5: OK / OK with a trim / not OK.

## PC (2026-10-03)

This machine did not re-render the pairs. `guitar_ab.py` points at `/workspace/build_support_2` (snapshot 1010 versus prototype A), and `client_body_1140.json` is not in the canonical tree. Play pairs were not recorded from the app. The box table above is the listening set. The un-matched level change is the trim with its sign flipped: default tail +0.74 dB, default mix +0.18 dB; carpet tail +2.00 dB, carpet mix +0.53 dB.
