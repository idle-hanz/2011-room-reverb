# BLOOM alias diagnostic (2026-10-22)

Read-only. No product edit. Current pin stays UI-TIDY-1. This note scores the round-3 prototype on the same 112 rows as `BLOOM_RETRY2_STOP_2026-10-22.md`, checks the 610-A +68 dB peak, estimates oversampling against the 2.40 ms ceiling, and records the `ls_ln` line to put back when `bloom_live.inc` is included again.

The build column is the stop’s score, `%TEMP%\bloom_rt2_alias_score.json`, re-read and not rewritten. The prototype column is a new run. Its dump is `%TEMP%\bloom_alias_diag_out.json` (342.8 s, plain loops; numba is absent from `software\.venv`).

## Scorer (VERIFIED)

The copy is the stop’s scorer, `%TEMP%\bloom_rt2_alias_score.py`. Meter is `tone_alias` in `roadmap\bloom\uad\round3\scripts\alias.py`. Unit is dBc after one scalar level-match. Pass is our worst ≤ UAD worst + 0.5 dB on that row. Gap in the tables is ours − UAD, so a pass is a gap ≤ +0.5 dB.

M1 is the Blackman-Harris folded harmonic. M2 is the below-16 kHz residue peak minus the fundamental. A below-16 kHz peak that is outside 80 Hz of an integer harmonic and within 150 Hz of the UAD M2 frequency is dropped from our pool. UAD M2 is dropped from the UAD pool when it fails that same harmonic test. Same-bin UAD data is absent from the csv, so the comparison is worst against worst. dBc is invariant to the level-match; `match_db` is reported and does not decide the row.

Re-scoring the existing build f32 (`%TEMP%\bloom_rt2_alias.f32`, 1 s at 48 kHz, meta order natural, glue, room_crush, swell, nuke, neve, u610a) matched all 112 rows: worst absolute delta 0.0 dB, flag mismatches 0. The build table below is that file. Totals stay 79 fail, 33 pass.

Compressors are `alias_proto.run_c` with `dyn3.gr_of` and `fit_<preset>.json` params merged over `dyn3.DEF`. Pres are `alias_proto.pre_y` with `pre_choice.json`. `run_c` has no makeup and no EQ. The build score is after both. A flat gain cannot move dBc. An EQ tilt can move a harmonic relative to the fundamental, so a prototype/build difference of a few dB on a compressor row can be that.

Prototype oversampling is `scipy.signal.resample_poly`. The build’s oversampling is the 47-tap halfband. A prototype factor is evidence about the nonlinearity. It is a build factor only where the two columns already agree.

`pre_choice.json`: Neve family `nclip_emph_flux_mem`, 610-A family `nclip_flux`. The build ships Neve as `_neve_ship()` → `nclip_flux` at 8x (`bloom_dsp.py`). The Neve columns are different models.

## 1. Prototype vs build vs UAD

Shipped rates, one worst row per preset. Prototype fail total 82 / 112. Build fail total 79 / 112.

| Preset | Rate | Proto fail | Proto worst row | Proto dBc | UAD on that row | Proto gap | Build fail | Build worst row | Build dBc | UAD on that row | Build gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| natural | 2x | 15 | 7 kHz, 0 | −78.827 | −113.6 | +34.773 | 15 | 13 kHz, 0 | −70.402 | −104.1 | +33.698 |
| glue | ADAA1 | 16 | 9 kHz, −6 | −74.813 | −97.7 | +22.887 | 16 | 17 kHz, −12 | −78.033 | −99.4 | +21.367 |
| room_crush | 1x | 4 | 17 kHz, 0 | −56.103 | −58.1 | +1.997 | 4 | 17 kHz, 0 | −56.105 | −58.1 | +1.995 |
| swell | 2x | 16 | 9 kHz, 0 | −77.090 | −107.8 | +30.710 | 16 | 9 kHz, 0 | −67.010 | −107.8 | +40.790 |
| nuke | ADAA1 | 6 | 13 kHz, −24 | −90.313 | −141.4 | +51.087 | 6 | 13 kHz, −24 | −90.314 | −141.4 | +51.086 |
| neve | 8x | 16 | 9 kHz, −6 | −31.852 | −86.3 | +54.448 | 8 | 17 kHz, −6 | −43.674 | −65.5 | +21.826 |
| u610a | 8x | 9 | 17 kHz, −12 | −30.861 | −107.6 | +76.739 | 14 | 9 kHz, −6 | −24.436 | −114.4 | +89.964 |

Sidebands on the prototype worst rows (VERIFIED):

- natural 7 kHz 0: M1 and M2 both −78.827, M2 at 13000 Hz, kept (UAD M2 is 3000 Hz). `match_db` +6.847.
- glue 9 kHz −6: M1 −74.813, M2 −81.104 at 3000 Hz, excluded (UAD M2 is 3000 Hz). `match_db` +0.386.
- room_crush 17 kHz 0: M1 and M2 both −56.103, M2 at 14000 Hz, excluded (UAD M2 is 14000 Hz). The remaining M1 still fails. At 48 kHz, 2 × 17 kHz folds to 14 kHz. `match_db` +24.141.
- swell 9 kHz 0: M1 −77.090, M2 −78.999 at 15000 Hz, excluded (UAD M2 is 15000 Hz). `match_db` +4.674.
- nuke 13 kHz −24: M1 −90.313, M2 −114.985 at 9000 Hz, kept (UAD M2 is 5000 Hz). `match_db` −2.400. The −90 dBFS floor stays withdrawn, so −90.3 dBc still fails by 51 dB.
- neve mem 9 kHz −6: M1 and M2 both −31.852, M2 at 15000 Hz, kept (UAD M2 is 3000 Hz). `match_db` −6.484.
- u610a 17 kHz −12: M1 and M2 both −30.861, M2 at 14000 Hz, kept (UAD M2 is 2190 Hz). `match_db` −33.073.

Room Crush and Nuke match the build on the same row to 0.002 dB (VERIFIED). Natural and Glue are within about 1–3 dB and the worst row differs. Swell’s build is 10.08 dB worse than the prototype on the same 9 kHz, 0 dBFS row (−67.010 vs −77.090). The cause of that 10 dB was left UNKNOWN this pass. Neve is a different model, so the +54 dB prototype gap is the mem prototype and the +21.8 dB build gap is shipped `nclip_flux`. 610-A is the same `nclip_flux` family in both columns; the worst row differs, and both fail by tens of dB.

## 2. 610-A +68 dB peak (VERIFIED)

The stop’s Python row is real, and it is the once-trimmed path. `pack_pre` divides the H2 numerators by the 1 kHz cascade gain once:

```python
g = _cascade_gain_1k(kind, sr)
scale = 1.0 / g
row[20] *= scale
row[21] *= scale
row[22] *= scale
```

`g` for 610-A at 48 kHz is 166.997885 (+44.454 dB). Packed H2 `b0` / raw H2 `b0` = 0.0059881 = 1/g. Raw H2 `b0` is 1.000253. Packed H2 `b0` is 0.005990.

`_pre_bus` and `bloom_pre` in `software\engine\bloom_live.inc` each apply that packed H2 once. The only output divide is Drive, and only when Drive is nonzero:

```c
/* Section C. H2 is packed already divided by the 1 kHz cascade gain.
   Drive must not change that linear level. */
if (p[2] != 0.0 && drive > 1.0e-12) y /= drive;
```

There is no second cascade divide in `bloom_dsp.py` or in `bloom_live.inc`.

Three trims of the same 9 kHz, 0 dBFS, 1 s sine through `_pre_bus` (drive 0):

| Trim | Full-buffer peak | Tail peak (last 0.5 s) | 1 kHz gain | M1 |
|---|---|---|---|---|
| once (shipped `pack_pre`) | 2643.9157 (+68.445 dB) | 2.49935 (+7.957 dB) | 0.000 dB | −7.013 dBc at 21000 Hz |
| zero (raw H2 restored) | 441528.3 (+112.899 dB) | 417.386 (+52.411 dB) | +44.454 dB | −7.013 dBc at 21000 Hz |
| twice (packed H2 divided by `g` again) | 15.832 (+23.991 dB) | 0.01497 (−36.498 dB) | −44.454 dB | −7.013 dBc at 21000 Hz |

2643.9157 is the stop’s number. It is sample 95 of the once-trimmed buffer (the sine there is −0.92388). Linear |H1·H2| after the single trim is 1.000 at 1 kHz and 0.8946 at 9 kHz (−0.968 dB). The same 9 kHz tone at three other levels:

| Input | Peak index | Peak vs input |
|---|---|---|
| −100 dBFS | 15 | −0.968 dB |
| −40 dBFS | 580 | +3.677 dB |
| −12 dBFS | 95 | +44.317 dB |
| 0 dBFS | 95 | +68.445 dB |

−100 dBFS sits on the linear 9 kHz magnitude. The +68 dB figure is the full-second max of the nonlinear path. The alias meter, which uses the last 0.5 s, sees a tail peak of 2.50 and M1 −7.013 dBc. H2 is linear, so it scales the fundamental and the image together. M1 stays −7.013 dBc at zero, once, and twice. A second divide moves the 1 kHz trim from 0.0 dB to −44.454 dB and leaves the image where it is.

**One-line fix:** do not add `y /= g` after the H2 biquad. The single trim is the three `row[20..22] *= scale` lines in `pack_pre`. The C line stays the Drive divide above.

The flux cubic is applied at the base rate, on H1’s output `v`, after nclip has been downsampled (`bloom_dsp.py` `_pre_bus`, the `af` block; the same order in `bloom_pre`). Oversampling wraps nclip. It does not wrap that cubic. LIKELY that base-rate cubic is why the 610-A image does not fall with oversampling. This pass did not run a with/without-flux render, so that attribution stays LIKELY. The once-only trim is VERIFIED.

## 3. Oversampling vs UAD + 0.5 dB, and the 2.40 ms ceiling

Sweeps use the prototype and the same gate, all 16 rows. “Stuck” means the worst gap stopped moving, so a higher factor on this nonlinearity does not meet the gate. CPU figures are the published wasm cube and the round-3 native microbench. RT-4 was not run. The ceiling stays 2.40 ms. The stop’s RT-4 line requires median, p90, and silence-late each ≤ 2.40 ms.

Published cube, decay-8, shared off, from `roadmap\overnight\bloom_cpu_neve8.json`, `bloom_cpu_neve8b.json`, `bloom_cpu_neve16.json` (VERIFIED as recorded on the wired tree, which the restore removed):

| Case | Median | p90 | Silence-late median |
|---|---|---|---|
| Off | 1.747 ms | 1.773 | 1.737 |
| Colour on, pre off | 1.825 ms | 1.837 | 1.820 |
| Full, Neve `nclip_flux` 8x (first) | 2.209 ms | 2.246 | 2.381 |
| Full, Neve `nclip_flux` 8x (repeat) | 2.196 ms | 2.216 | 2.369 |
| Full, Neve 16x mem | 2.934 ms | 2.958 | 2.979 |

Spikes on both 8x flux runs: 38. A spike there is a block slower than 3× the median. The 16x mem run is over 2.40 on median, p90, and silence-late. Headroom from the tighter 8x silence-late (2.381) to 2.40 is 0.019 ms.

Round-3 native bench (`UAD_ROUND3_2026-10-19.md`, ns/sample/channel | µs per 128-sample stereo block): comp 1x 35 | 9.1, comp 2x FIR47 51 | 13.1, pre 8x with nclip 417 | 107 (0.107 ms), pre 16x estimate about 0.21 ms. The full-cube wasm delta from colour-on (1.825) to Neve 8x (2.209) is +0.384 ms, about 3.6× the isolated 0.107 ms. Use that only as a scale warning. It mixes the pre into the whole cube.

| Preset | What the sweep did | Factor that meets UAD + 0.5 | CPU against 2.40 |
|---|---|---|---|
| natural | 1x gap +50.172 (13 kHz 0, −53.928). ADAA +37.999. 2x, 4x, and 8x identical: 15 fail, gap +34.773 at 7 kHz 0, ours −78.827. Stuck from 2x. | None. The −78.8 dBc image is inside what oversampling removes. | Moot. |
| glue | 1x gap +23.400 (17 kHz −12, −76.000). ADAA +22.887. 2x, 4x, and 8x identical: 16 fail, gap +22.849, ours −74.851. Stuck. | None. | Moot. |
| room_crush | 1x is the shipped miss: 4 fail, gap +1.997 at 17 kHz 0, ours −56.103. 2x: 0 fail, worst gap +0.269 at 9 kHz 0, ours −61.731, UAD −62.000. | 2x on the prototype (VERIFIED). Shipped stays 1x. The build’s 47-tap 2x was not scored. 1x already matches the build to 0.002 dB, so a build 2x pass is LIKELY. | Native 1x→2x is +4 µs per 128-sample stereo block (9.1 → 13.1). ESTIMATE: that add stays under 2.40 even at a few times the native cost. It was not re-benched on the cube. Silence-late headroom is only 0.019 ms, so the estimate is tight and is an estimate. |
| swell | 1x gap +64.427 (9 kHz 0, −43.373). ADAA +54.854. 2x +30.710 (−77.090). 4x +30.636. 8x +30.619. About 34 dB from 1x to 2x, then flat, 30 dB short. | None. | Moot. The build is already 10 dB worse than this 2x prototype, so more build oversampling is not a path to +0.5 dB either (LIKELY, from the prototype being stuck and the build being louder). |
| nuke | 1x 13 fail, gap +67.657 (17 kHz −24, −78.143 vs −145.8). ADAA 6 fail, +51.087 (−90.313). 2x +44.812 (−96.588). 4x +44.838. 8x +44.842. About 6 dB from ADAA to 2x, then flat, still 6 fails and 45 dB short of −141.4. | None. The quiet −24 dBFS rows are a floor. | Moot. |
| neve (mem prototype) | 4x 16 fail, gap +63.175 (7 kHz −6, −28.025 vs −91.2). 8x +54.448 (−31.852). 16x 13 fail, +40.937 (−45.363). 32x 11 fail, +26.578 (−59.722). Still falling about 14 dB per octave from 8x to 32x. | Not converged. Linear extrapolation of that slope to a gap ≤ +0.5 is about two more octaves, near 128x. ESTIMATE, and it may flatten. The shipped `nclip_flux` factor is UNKNOWN this pass. Do not copy the mem slope onto the flux build. | Do not spend 128x. Isolated 8x is 0.107 ms; a rate-linear 128x is about 1.7 ms added, past 2.40 by itself. The measured 16x mem full chain is already 2.934 / 2.979 ms. Those two published runs also differ in model (mem vs flux), so 2.934 − 2.209 is not a pure oversampling scale. |
| u610a (`nclip_flux`) | 4x 9 fail, gap +76.410 (17 kHz −12, −31.190 vs −107.6). 8x +76.739 (−30.861). 16x +76.812 (−30.788). The image got slightly worse. 32x was not run. M2 stays at 14000 Hz, the fold of 2 × 17 kHz. | None. | Moot. |

Room Crush is the only preset where a finite factor meets the new gate. Raising everyone else until the old −90 dBFS rule would have passed does not meet UAD worst + 0.5 dB.

## 4. `ls_ln` 11-bit fix, for the next include (VERIFIED, still reverted)

`software\engine\bloom_live.inc` line 11 is the restored mask:

```c
e = (int)((v.u >> 52) & 1023) - 1023;
```

The IEEE exponent field is 11 bits. The line to put back when this file is included again:

```c
e = (int)((v.u >> 52) & 2047) - 1023;
```

With `& 1023`, `ls_ln` is right on (0, 2) and wrong for every x ≥ 2. Natural `20·log10(1+u)` broke near GR 6.02 dB. Swell `18.1·ln(1+v/8.06)` broke near GR 12.55 dB. Room Crush release `ls_ln(g/10)` broke once GR ≥ 20 dB, so settled GR at 0 dBFS was about 15.9 instead of about 36. The off path does not call `ls_ln`. Nuke does not call it on x ≥ 2. No `.c`, `.h`, `.js`, or `.py` in the tree names `bloom_live`, so the restored audio path does not call this function. The alias gate in the stop was measured after the `& 2047` fix, so the 79 build fails are not this log bug.

This pass did not edit the line.

## Left as they are

HANDOVER, `BLOOM_*.md`, goldens, wasm, and `software\` were not edited. The build score json and the build f32 were not rewritten. `WORKLET_VER` 59, `app.js?v=63`, and the 2.40 ms ceiling stay as the stop left them.
