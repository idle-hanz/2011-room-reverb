# s_audit/heights_research: D-AUD-6 per-mic heights (box, 3 Oct 2026 19:30–19:55 BST)

Box only. Nothing here goes into the real tree. Baseline = the PC copy at 0c7fd78490ea / WORKLET_VER 47 (`/workspace/audit_1852/software`).

## Files
- `hpatch.py`: monkeypatch prototype.
  - Each capsule gets Y = `my_l` / `my_r` / `my_c` (absolute metres, default `my`, clamped to [0.02, H−0.02]).
  - M/S (`ms_decode`) and binaural ignore the heights.
  - With env `HMODE=early` it is **H-1**: FDN line lengths, line diffusers and line air use the stand reference height `my`.
- `render_ir_h.py` and `dump_params_h.py`: the harness drivers with the patch.
- `smoke.py`: Play-params diff.
- `bench_h.py`: CPU, `bench_heights.json`.
- `guitar_h.py` and `h1_ctx.py`: the renders.
- `LISTENING_CHECKLIST.md`.
- The WAVs.

## Results (all VERIFIED on the box unless marked)
1. **Back-compat.** With no per-capsule heights, the Play params JSON is identical (0 differing fields) and the Render IR is max-abs 0 (null −2999 dB).
2. **Structure.** Image taps already carry per-capsule distance, delay, level and angle (`ImageTap.distance_l/r/c`), and Play already has one delay set per bus (L, C, R). So heights add **no taps, lines or blob fields**. Only values change.
   - The tilt case changes the colour-IR dedup count: 150 → 130 unique IRs, i.e. fewer.
3. **CPU** (box, Node wasm, shipped `live_stereo.wasm`, t19 two-source scene, 6 alternating rounds, `bench_heights.json`):
   - shared off: flat 1.9175 ms vs tilt 1.8938 ms, paired median **−1.15 %**;
   - shared on: 1.8973 vs 1.8915 ms, **−0.62 %**.
   - Both are inside noise. Expected PC change: 0 (ASSUMED).
   - Caveat: this box bench shows shared on ≈ shared off, so the bench script may not engage the shared tail. The shared-on number is ASSUMED to transfer.
4. **Sound (Render, guitar, level-matched):** see the table in `LISTENING_CHECKLIST.md`.
   - Early ⅓-octave changes of up to 8–10 dB in single bands. That is floor/ceiling comb filtering, the physical effect of height.
   - Broadband early level −0.7…0 dB.
   - Tail: up to 4.6 dB in single low bands with the full model, ≤ 0.42 dB with H-1.
5. **Design.**
   - Heights should enter the image taps (3D distance → delay, 1/r², and the arrival angle including elevation, so a cardioid's off-axis gain applies) and the direct path (the n = (0,0,0) tap per capsule). Both happen automatically once `mic_positions()` and the C centre use per-capsule Y.
   - Recommended **H-1**: the FDN line set stays on the stand reference height, so a capsule drag doesn't move the tail ±4 dB per band. As a bonus, Play's delay lines don't change length during a height drag.
   - M/S coincident pairs and binaural ignore per-capsule heights.
   - `my` stays the stand and C height (the C drag already writes both).
   - Overlap: S-MIX item 4 adds per-mic positions (including height) through `MicStand`. S-AUDIT must re-check what S-MIX did first.

Render length and Mono-C measurements for the other decisions are in `../decision_measure/len_mono.json`.
