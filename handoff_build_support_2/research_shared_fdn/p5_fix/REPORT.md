# Shared tail P5 (L/R coherence): cause, prototypes, recommendation
Box research, 2 Oct 2026 (BST). Snapshot of PC `software\` taken 18:40, read-only (the PC was never modified and no app was restarted).
PC Play bytes were re-checked at 19:30 after S7 landed: `live_stereo.wasm` 6188C78C…AEFBE and `live_stereo.c` 595713A5…742D, the same as the snapshot.
I could not read Build's transcript t321u (I have no transcript tool). Build's numbers came from its files: `roadmap/shared_tail/proof.json`, `phase_p5p9.json` and `tests/test_shared_tail.py`. I reproduced them exactly (VERIFIED).

## 1. Cause
- **One network, one modal set (ASSUMED mechanism; the data agree with it).** With the shared loop, L and R read the same 32 lines. Only sub-ms read offsets, the 0.3 ms jitter and per-line colour separate them. Off, each mic has its own network with spacing-dependent delays, so it has its own modes, and that is what decorrelates the 250 Hz–2 kHz range. Evidence: shared-on coherence barely changes with mic spacing (ortf_wide on ≈ default on ≈ 0.93–0.95 at 250 Hz), while off drops from 0.86 to 0.77. That is why ortf_wide is the worst scene.
- **CSIGN_D makes it worse (VERIFIED).** In a per-line decomposition (default room), under H·D the cross-line terms *add* coherence (+0.03…0.12 over diagonal-only). Under plain H they subtract. Across 8 jitter seeds, the mean LF excess (250–1k, 5 scenes) is +0.114 for CSIGN_D and ≈0 for plain H or a fully new d. So the bias is systematic and the seed SD is only 0.005–0.03.
- **Why "just change d" does not work: P6 (VERIFIED).** The off networks also use H·D with CSIGN_D. That shared matrix is why the shared tail's third-octave levels match off within ±0.6 dB below 400 Hz. Any d far from CSIGN_D moves the LF modes:
  - m1019: −5…−6 dB at 250 Hz in every scene; P6 raw is 5.5–6 dB against a 3.5 dB limit.
  - plain H: +7 dB at 200 Hz, and the comb comes back.
  - D·H·D: P6 about 8 dB, and the comb comes back.
  
  P5 and P6 pull in opposite directions.
- **Hard constraint I found (VERIFIED).** The shared-loop d must be invariant under the line mirror π = index-bit swap (b0 b4)(b1 b3) (see the `fdn.py` LOOP_COLUMN_D comment). π commutes with Sylvester H, and CSIGN_D is π-invariant. A non-invariant d breaks P7: dv33/dv133 give −12 dB against the −120 dB limit. My earlier dv33/dv133 "passes" were invalid for this reason. Mirror-invariant vectors have 20 orbits (8 fixed lines and 12 pairs).

## 2. What was tried (option-off is bit-exact in every case: P1 max|diff| = 0 in 5 scenes × colour on/off, and P8 = 0)
Seed-family means come from 8 jitter-hash seeds of the same build. P5 gate is rms ≤ 0.09 and max ≤ 0.15. P6 gate is |level| ≤ 1 dB and third-octave raw ≤ 3.5 dB.

| family | mean rms def/big/small/mid/wide | LF bias | P5 all-5 | P6 ok | both | comb/ac19 | P7 |
|---|---|---|---|---|---|---|---|
| ship CSIGN_D, jitter 0.30 ms | .138/.057/.086/.097/.188 | +0.114 | 0/8 | 6/8 | 0/8 | ok | exact |
| CSIGN_D, jitter 0.60 | .096/.056/.058/.085/.128 | +0.048 | 0/8 | 1/8 | 0/8 | ok | exact |
| plain H (shared only) | .075/.060/.112/.068/.089 | −0.024 | 0/8 | 0 (P6 ≈ 8 dB) | 0 | **comb back** (ac19 0.31–0.36) | exact |
| D·H·D | .084/.065/.060/.096/.095 | +0.072 | 1/8 | 0 (≈ 8 dB) | 0 | **comb back** | exact |
| tap offset ×2, tapD, OSQ hashed out-signs, readout signs (m pairs) | — | — | 0 | mixed | 0 | ok | exact |
| random new d (non-mirror) dv33/dv133 | — | — | some | 0 | 0 | ok | **−12 dB fail** |
| 72 random mirror-invariant d (j0.30/0.45) | best m1019 j0.45: .082/.062/.070/.084/.089 | +0.003 | 2/8 | 0/8 (P6 ≈ 6 dB) | 0 | ok | exact |
| **F12: CSIGN_DS (CSIGN_D, orbit {3,24} flipped), j0.30** | .098/.056/.067/.092/.131 | +0.075 | 0/8 | 5/8 | 0 | ok | exact |
| R750: CSIGN_DS + line weights β=0.75 + j0.45 | .073/.052/.058/.071/.096 | +0.018 | 2/8 | 2/8 | 2/8 | ok | exact |

Screened: 222 builds, including 39 one- or two-orbit flips of CSIGN_D. Flipping orbits {13}, {17} or {18} gives the same IR as not flipping (ASSUMED: those lines carry no tap or injection weight in these rooms). Line weights (WTAP) scale each mic's tap of line i by (1−β)+β·inj_mic,i/injS_i. They decorrelate well, but they raise the late level by +0.5…+1.4 dB regardless of the renormalisation tried (rms, none, mean).

## 3. Finalists, shipped seed (P5 rms/max per scene; P6 = worst |level| dB / worst third-octave dB)

| | ship (Build) | **F12 (recommended code change)** | R750s7 (passes the gate as written) | m1019 j0.45 |
|---|---|---|---|---|
| default | .099/.158 ✗ | .057/.100 | .044/.092 | .050/.070 |
| big | .038/.072 | .039/.075 | .055/.081 | .047/.092 |
| small | .094/.142 ✗ | .085/.120 | .043/.087 | .073/.096 |
| mid | .089/.140 | .088/.125 | .065/.118 | .061/.102 |
| ortf_wide | .181/.253 ✗ | **.135/.221 ✗** | .078/.123 | .064/.129 |
| P6 (gate scenes) | 0.46 / 3.03 ✓ | 0.56 / 3.22 ✓ | 0.87 / 3.14 ✓ | 0.97 / **5.9 ✗** |
| HOLD P5 (hall20_off, ortf_narrow, big_off, default_2src) | .061/.085, .065/.108, .080/.155, 0 | .057/.087, .046/.080, .077/.146, 0 ✓ | .042/.076, .069/.099, **.088/.188 ✗**, 0 | .049/.102, .042/.068, .042/.084, 0 |
| HOLD P6 | ✓ (≤ 2.3 dB, ≤ 0.25 dB lvl) | ✓ (≤ 3.11 dB, ≤ 0.27 dB lvl) | **✗** ortf_narrow 4.37 dB, big_off lvl 1.69 dB | ✗ |
| P4 T30 worst err (Δ vs off) | 4.7 % (+0.9) ✓ | 3.9 % (+1.1) ✓ | 2.3 % (+0.6) ✓ | 3.1 % (+1.2) ✓ |
| P7 mirror | −600 dB | −600 dB | −600 dB | −600 dB |
| P9 (30 s, decay 8 s) rise/drop | −15.0/180 ✓ | −15.0/180 ✓ | −15.0/180 ✓ | −15.0/180 ✓ |
| comb on (dB L/R), ac19.36, acmax | 2.02/3.15, .096/.105, .135/.126 | 2.02/3.16, .141/.158, .141/.158 | 1.49/2.14, .123/.130, .144/.151 | 2.08/3.00, .058/.077, .208/.196 |
| CPU on, 2 sources, box, min of 8 (ms/block) | 1.389 (rebuild of the same source 1.409) | 1.403 | 1.411 | 1.378 |

- CPU: all candidates sit inside build-to-build noise (about ±1.5 %). The changes are a different constant table, a pointer swap around one call, and load-time weights. None adds per-sample work (VERIFIED on the box; PC timing not measured, and I left the t19 drift investigation alone). R750's jitter 0.45 ms needs a slightly larger tap reach; ring capacity is unchanged.
- P5 noise floor (VERIFIED): off vs off with the source moved 5–20 cm gives rms 0.02–0.05 and max 0.03–0.09. The P5 limits are about 2× that. The seed-to-seed scatter of one fixed design is ±0.02–0.04 rms.

## 4. Recommendation
**Adopt F12 for the shared loop only: CSIGN_DS = CSIGN_D with entries 3 and 24 set to +1.** Keep jitter at 0.30 ms and seed 1.
- It is mirror-safe (π-invariant), not a Walsh row (peak |Hd|/32 = 0.375), and P6-neutral.
- It holds out on all 4 HOLD scenes, costs no CPU, and keeps the option off, binaural and parity bit-exact.
- Effect (VERIFIED):
  - P5 passes in default, small, mid and big.
  - The seed-mean LF bias falls from +0.114 to +0.075.
  - Seed-mean rms falls about 30 % in default and ortf_wide.
- **It does not make ortf_wide pass (0.135/0.221).** No variant passed P5 and P6 together robustly: the only full passes were seed-tuned and failed held-out scenes. My conclusion (ASSUMED) is that the 0.09/0.15 single-shot gate in ortf_wide can't be met by one shared network while also holding P6.

### Decisions for Idle

> **Locked by Idle, 2026-10-02 20:29 BST:** D1 yes (two-sign tweak F12, entries 3 and 24 set to +1, shared loop only). D2 = ortf_wide gets its own P5 limit of 0.15/0.25; other scenes keep 0.09/0.15. D3 (R750s7) declined.

1. **D1, sound change (shared mode only, default off).** F12 changes the shared tail slightly: LF/mid coherence goes down, so it is wider and closer to off, and third-octave shapes move by ≤ 3.2 dB (P6 ok). Option off is bit-identical.
2. **D2, P5 gate for ortf_wide (needed with F12).** Pick one:
   - (a) a per-scene limit for ortf_wide, e.g. rms ≤ 0.15 and max ≤ 0.25, recorded as a known property: the shared tail is a bit narrower with wide-spaced mics;
   - (b) keep the gate and accept that P5 fails as a documented limitation of the option;
   - (c) take R750s7 instead (D3);
   - (d) redesign, e.g. two shared networks or partial per-mic loops. Not prototyped; it costs CPU.
3. **D3, alternative R750s7 (not recommended).** It passes P1, P4–P9 and the comb on the gate scenes as written. But it is tuned to the jitter-hash seed (2/8 seeds pass), it raises the shared-tail level by about +0.9 dB, and it fails P5/P6 on 2 of 4 held-out scenes. Constants: CSIGN_DS + β = 0.75 line weights, no gain renormalisation, jitter 450 µs, hash seed 7.

## 5. Files
- `BUILD_FIXUP_PROMPT.md`: paste-ready prompt for Build (same window).
- `c/variant.c`, `c/mkvariant.py`, `c/build.sh`: the prototype. The shared-only switches are SH_DVTAB, SH_WTAP, SH_WREN, SH_JIT_US, SH_JSEED, SH_PLAINH, SH_DHD, SH_OSQ, SH_OTAB and SH_ALPHA. `c/live_stereo_1840.c` is the snapshot source. `c/dbg_line.c` is the per-line probe.
- `c/ref/`:
  - `F12_csign_ds_j300.wasm` (MD5 30a68b0e…): the IR target for Build's implementation;
  - `R750s7_alt.wasm`;
  - `rebuild_1840_ship_src.wasm`: the ship source built with zig, IR bit-exact to ship;
  - `ship_live_stereo_6188c78c.wasm`.
- `scripts/`: `p5lib.py` (P4–P7, P9, comb and bench, all mirroring Build's test), `screen.py`, `screen2.py`, `full_eval.py`, `mirror_dvec.py`, `otab.py`, `decomp.py`, `noise.py`, `baseline.py`. They run against the `tpc/` harness copy, which is not synced.
- `data/*.json`: every screen. `family_final.json` holds the table in §2 and `full_eval.json` the table in §3.
