# Build brief: "Shared tail" Live option + binaural skip-empty-centre (paste-ready)
Applies only if Idle approves D1 / D2 (see REPORT.md §8). Play engine only (`live_stereo.c` + the Live param push).
Render, Reaktor parity and `reaktor_parity` are untouched.

## Context (from research_shared_fdn, 2 Oct)
- **Shared tail:** Play runs one 32-line Hadamard network per mic bus. That is 3 per source, so 6 with two sources.
  - One shared loop with per-mic output taps cuts the Play block by **11–24 %** (box bench).
  - It keeps T30, tail coherence (RMS deviation ≤ 0.08), level (≤ 1 dB) and the bit-exact mirror for stereo mic setups.
  - It fails the binaural head-IC test, so **binaural stays per-ear**.
- **Skip-empty-centre:** in binaural, the empty centre bus is still computed. Skipping it is bit-exact.
- **Reference prototype:** `research_shared_fdn/proto/live_stereo_shared.c`.
  - Build the candidate with `-DSHARED_MODE=1 -DSHARED_JITTER_US=300 -DSHARED_JSEED=1`.
  - Build skip-empty-centre with `-DSKIP_EMPTY_C`.

## Part 1: skip the empty centre bus (always on, no sound change)
1. Per partition, set `cEmpty = (micG[C] == 0 && every C line inj == 0 && injB == 0)`.
2. When `cEmpty`, skip `bus_sample(C)` and skip bus C in `mix_partition`: no colour FIRs and no IC collect.
3. When the centre returns (cEmpty 1 → 0), zero bus C's rings and line filter states before running it.

## Part 2: "Shared tail" option (Live only, default OFF, stereo mic setups only; ignored in binaural)
1. **Param:** add `shared_tail` (bool, default false) to the Live param push and the room blob. Python's `reaktor_parity` path never sets it.
2. **Inject:** only bus C runs the loop, with inject injS_i = sign(Σ_mics inj_m,i) · sqrt(mean_m inj_m,i²) over the 3 mics (bank B: same with injB).
   - Bus C's early lane keeps C's own inject.
   - Tint is linear, so xin = tint_early · injS/inj when inj ≠ 0, with no extra tint.
3. **History:** after bus C's loop, write each line output y_i (and bank B) into a per-line history ring with at least max-offset + 2 samples of headroom.
4. **Taps:** each mic b ∈ {L, C, R} reads line i at the integer offset round(D0 + 1 + (d_b,i − d_C,i) + J_b,i).
   - D0 = ceil(max over L/R, i of (d_C,i − d_b,i)), so every offset is causal.
   - Multiply by g_b = sqrt(Σ_i inj_b,i² / Σ_i injS_i²), computed per bank.
5. **Jitter:** J_b,i = 0.3 ms · sr · hash(delayT of the partner bus line i), with L keyed on R and R on L.
   - C is keyed on its own delayT + 0.5.
   - Bank B uses delayBT with the same hash (mirror-safe).
   - Hash: the integer mix in `shared_jit()` with seed 1, **computed at load**, not per sample.
6. **Unchanged:** the taps feed each mic's per-line colour FIRs (`fdnIdx[b]`) exactly as yBlk does today. Nothing else changes downstream.
7. **Toggle or room load:** when switching shared_tail on or off, clear the history ring, bus C's loop state and the L/R FDN lanes so nothing stale plays.
8. **Locks, do not touch:**
   - unscaled ±1 FWHT and g;
   - early images excite the FDN;
   - 1/r² inject values;
   - per-line colour;
   - serial cascade and stage order;
   - two diffusion layers kept separate;
   - no air on the FDN return.

## Proof tests (add to 3_phase_acceptance_tests; all on the Play wasm via `wasm_run.js`)
- **P1 Off is bit-exact:** shared_tail = false gives IR max |diff| = 0.0 vs the previous build in 5 scenes: default 1 and 2 sources, big 1 and 2 sources, binaural 2 sources; colour on and off.
- **P2 Skip-empty-centre is bit-exact:** binaural default 1 and 2 sources, binaural big; colour on and off; diff 0.0. Plus CPU: binaural block min ms lower than before.
- **P3 CPU:** shared_tail on, default 2 sources: Play block min ms ≥ 15 % below off. Use alternating rounds and the min of 6.
- **P4 T30:** octaves 250 Hz–8 kHz, default and big room, 1 and 2 sources: |T30 − dial| ≤ 10 %, and not worse than off by more than 3 points.
- **P5 Coherence:** tail L/R octave coherence vs off, in default, big, small 6×3×8 m, mid 15×8×22 m off-centre and ORTF wide: RMS deviation ≤ 0.09, max ≤ 0.15.
- **P6 Level:** tail RMS L and R each within ±1.0 dB of off. Third-octave shape (125 Hz–12.5 kHz) within ±3.5 dB.
- **P7 Mirror:** two sources, balance −1 vs +1, B.L vs A.R tail null ≤ −120 dB (bit-exact expected).
- **P8 Binaural unaffected:** with shared_tail = true and mic_setup = binaural, output is bit-exact to shared_tail = false, and `test_binaural_play_tail_coherence_matches_head` passes.
- **P9 Stability:** 30 s IR in the default room at decay 8 s: finite and still decaying at 30 s. Same NaN/scrub behaviour as off.
- **P10 Toggle:** toggle shared_tail during noise playback: no sample above the pre-toggle peak + 3 dB and no NaN.

## Not in this brief (separate item, D5)
Today's engine has a DC/infrasonic runaway at long decays. Measured:
- big room, decay 8 s: about +7 dB/s growth to full scale;
- binaural big room at decay 4 s: grows about +2 dB/s.

It needs its own fix and its own proof test (30 s IR, level must fall monotonically after 2 s).
