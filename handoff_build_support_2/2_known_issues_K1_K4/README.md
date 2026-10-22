# Package 2: K1–K4 reproduced on the box snapshot

**Tree:** `snapshot_2026-09-28_2040`, used read-only through the box copy `work/latest/software`.

**LOCKED 28 Sep 2026 (Idle):**

- K1: fix via the single `YAW_X_SIGN` flip.
- K2: keep the 1-pole code, `air_lp` default 0.
- K3: default source 2.6 / 1.2.
- K4: FDN-first (direct/early faders 0, `early_wet` 1.0 enable) plus the stale-early fix.

Each brief now opens with a LOCKED section (implementation, patch, tests, numbers). See `../DECISIONS_LOCKED_2026-09-28.md`. The Decision column below is historical.

**Run:** `RR_SW=<software> python scripts/<k>.py`. The results land in `results/*.json`.

| K | Issue | Verdict | Key number | Decision |
|---|---|---|---|---|
| K1 | Stereo presets aim the capsules inward (crossed) | **CONFIRMED** | Source 2 m left: L capsule gain 0.539 vs R 0.963. Early-only L−R −4.8 dB (fixed: +3.6 dB). Direct with MEASURED colour −5.4 dB (fixed: +5.5 dB). Time cue L-first by 12 samples. Affects xy_90, xy_120, ortf, nos, din and ms | **DECISION FOR IDLE** + listen (changes the image). Fix A (convention) or B (data) in `briefs/K1_crossed_ortf.md` |
| K2 | Structure humidity 1-pole corner fc = Wet/d = 133 Hz at 3 m (humidity 0.5) | **CONFIRMED numerically; cause UNKNOWN** | With air_lp 0.25: a broadband −2.4 to −2.5 dB step above about 1 kHz for d ≥ 3 m. At full LP: −17.6 dB at 1 kHz at 3 m (not physical, ASSUMED). The code matches the Structure note; the unit of Dis is unknown | **NEEDS IDLE LISTENING** / reference captures |
| K3 | Only 12 unique FDN delays on C (20 on L/R) in the default room | **CONFIRMED** | Caused by the doubly symmetric default (sx = mcx = W/2, sy = my = H/2). sx 2.6 + sy 1.2 gives 29/29/29, which matches Structure Live-32 | **DECISION FOR IDLE** (default geometry); a de-dup nudge is not recommended |
| K4 | Early reflections off by default | **CONFIRMED** | early_wet 0 on the server and client, fader_early 0. When on, the early bus is −17.8 dB of the first 80 ms. The FDN is unaffected (lock holds). Side finding: a stale early lane after re-enabling (C `bus_sample`, ASSUMED audible) | **DECISION FOR IDLE** (default level) |

## Files

- `scripts/common.py`: imports the tree via `RR_SW`.
- `scripts/k1_ortf_crossed.py`: look vectors and gains, plus a real Render (direct, direct with colour, early).
- `scripts/k1b_all_presets.py`: every preset, shipped signs vs negated.
- `scripts/k2_air_corner.py`: corner frequency and response grid.
- `scripts/k3_unique_delays.py`: unique delays per bus for 5 geometries.
- `scripts/k4_early_off.py`: defaults, early bus energy, FDN invariance.
- `briefs/K1…K4_*.md`: one-page fix briefs with file:line references.
