# PC2 — 610-A input reference

Evidence only. No coefficient change, no trim applied. Drive 0. 610-A only.

HEAD `8996fa1f5b8ee2d48020656cb1a5dbb24fc49c3a` (`8996fa1` drop unread mic hp and proximity from the harness render). PC1 `e0a61d0` is the parent. `pack_pre` for the 610-A is still that commit.

Gate: **PASS**. The capture level is recorded. The input trim that maps an app −18 dBFS peak onto the fit's drive-0 reference is **−39.0 dB**.

## Heard fault

After PC1, a −18 dBFS 1 kHz sine at Drive 0 reads 319% THD. H1 at 1 kHz is still the fitted linear gain, about 161, so an app full-scale sine is far above the level the fit was aimed at.

## The reference

The fit and the app use one peak law. Amplitude 1.0 is 0 dBFS. The level the round-3 captures and the fit treat as drive 0, and which the fit note calls the 1% point, is **−57 dBFS peak**.

−18 dBFS plus −39.0 dB lands on −57 dBFS.

That named point is a hard-clip row on the measured stair (17.0038% THD), so −39.0 dB does not land on 1% THD. The UAD 1% region and this model's 1% region are below.

## Links

1. **VERIFIED.** `siglib.py` lines 4–7. `db2a` is `10^(d/20)`. `stair` documents `level = dBFS peak`. A 0 dBFS step has peak amplitude 1.

2. **VERIFIED.** `prep.py` lines 36, 51, and 60–65. Pre-stair levels are `g0 + (-30..+12 step 2)` with `g0 = -57.0` for `u610a`. The sine is `S.stair(f, lv, 0.5)`, so the dB values are baked into `pst3_u610a_1000.npy`. The job stores those levels and has no `gain_db`.

3. **VERIFIED.** `jobs_r3.json` lines 3459–3586, job `pst3_u610a_1000`. Plugin `uaudio_610_a`, Mic, pad Off, input gain Hi, level `0.0 dB`, output `0.00 dB`, both EQ gains 0. `levels` run −87.0 through −45.0 in 2 dB steps. No `gain_db` key. The npy itself is not in this tree (`prep.py` line 1: inputs stayed on the capture PC). The level list in the job is the record of that stimulus.

4. **VERIFIED.** `pre_stairs.py` lines 6–11. `in_dbfs` is the job level. `rel_drive_db = L - (-57)` for `u610a`. THD is `100 * sqrt(sum(amp[1:]^2)) / amp[0]` after `hfit` of five harmonics (H2–H5).

5. **VERIFIED.** `pre_stairs_r3.csv` lines 145–149, `u610a` at 1000 Hz:

| in dBFS | rel drive | THD % | out dBFS |
|---:|---:|---:|---:|
| −65 | −8 | 0.2836 | −20.86 |
| −63 | −6 | 0.5352 | −18.88 |
| −61 | −4 | 4.8004 | −17.15 |
| −59 | −2 | 11.5081 | −16.06 |
| −57 | 0 | 17.0038 | −15.35 |

6. **VERIFIED.** `pass1.py` line 10, `CLIP_IN["u610a"] = -57`. Line 38 calls that unit "0 dB at the 1% point". Lines 86–93 apply `gain_db = -57 + rel` to the burst, the ESS (`pess_u610a_-30` is −87 dB), the noise, and the synthetic programme. The round-2 pre stairs at lines 79–80 have no `gain_db`; their levels are absolute.

7. **VERIFIED.** `UAD_ROUND3_2026-10-19.md` line 167. Vc −16.77 dBFS, input-referred, at drive 0 defined as the UAD mic gain such that −57 dBFS in is the round 2 1% point. Line 174 says both UADs clip hard at that named point. Line 176's "0.28% at −8, 5% at −4, 17% at 0" matches the rel-drive column above (0.2836, 4.8004, 17.0038), not a second absolute scale.

8. **VERIFIED.** `pre_fit.py` lines 6 and 35. `DRV` for `u610a` is −57. Stair steps outside `[−87, −51]` dBFS (`DRV-30` to `DRV+6`) are given residual weight 0. The 1 kHz round-3 stair's hottest step is −45 dBFS, inside the file and outside that training window.

9. **VERIFIED.** `prelib.py` lines 13 and 16–18 and 77–81. `rec3` scales `x` only when the job has `gain_db`. The 1 kHz stair has none, so the fit sees the baked peaks. `klin` is the −30 dB ESS (`pess_u610a_-30`). `v = x * G`, `u = v / Vc`. `mk_kernels.py` line 4 stores that kernel as `klin_u610a` and adds no level of its own. Line 41's "unity" is the shaper's small-signal slope, not an input level.

10. **VERIFIED.** `pre_choice.json` line 30. Shipped `vc_db` is −16.76700034210179. `real_meta.json` is the RMS of five peak-normalised programme excerpts (drums −20.55, bass −10.94, guitar −18.24, vocal −14.58, mix −10.02). `prep.py` line 27 peak-normalises each excerpt, then line 56 plays `rpprog_u610a_*_+0` at `gain_db` −57.0 (`jobs_r3.json` line 2795). Those RMS figures do not set the sine level. Guitar at −18.24 dBFS RMS is the normalised excerpt, before the −57 dB capture gain.

11. **LIKELY.** Log interpolation of the csv rows, `ln(THD)` against dB, across the 2 dB gaps. UAD 1 kHz THD crosses 1% near −62.43 dBFS (between −63 / 0.5352% and −61 / 4.8004%), 3% near −61.43 dBFS (same gap), and 10% near −59.32 dBFS (between −61 / 4.8004% and −59 / 11.5081%). The knee is steep, so the tenth of a dB is soft.

12. **UNKNOWN** as a measured 1.00% datum. No round-1 table in this tree shows 1.00% THD at exactly −57 dBFS. `UAD_ROUND2_2026-10-19.md` line 242 says pres have no Headroom knob and that their reference is the round-1 1% point. It does not record the 610-A number. The number that is recorded is `CLIP_IN` and the round-3 stair.

## This model, current HEAD

Python only, nothing written to disk. `pack_pre({"pre": "u610a", "sr": 48000, "pre_drive_db": 0})` then `_pre_bus`. One second, 48 kHz, peak sine. THD from the settled second half, exact-bin `rfft`, harmonics 2–15 over the fundamental. 1 kHz falls on a bin (24 000 samples, 500 cycles).

**VERIFIED.** `|H1|` at 1 kHz is 161.466931945. Settled −18 dBFS: THD 319.129%, peak 2.31285. Same point as the PC1b check.

`|u| = 1` at `20 log10(vc / |H1|)` = −60.929 dBFS. At −61 dBFS the model reads 11.73% THD, and at −60 dBFS it reads 19.28%. The vc knee is not the 1% point.

First rise from the cold side. The curve is not monotonic: THD is 48.6% at −53 dBFS, falls toward the high 20s, then climbs through 99% at −30 dBFS and 319% at −18 dBFS. The three levels below are that first crossing.

**VERIFIED** brackets, 0.05 dB grid, H2–H15. **LIKELY** only for the thousandth of a dB inside the bracket (`ln(THD)` against dB).

| THD | Measured bracket | Reported input |
|---:|---|---:|
| 1% | −63.70 dBFS is 0.989%; −63.65 dBFS is 1.030% | −63.69 dBFS |
| 3% | −62.60 dBFS is 2.934%; −62.55 dBFS is 3.093% | −62.58 dBFS |
| 10% | −61.25 dBFS is 9.954%; −61.20 dBFS is 10.303% | −61.24 dBFS |

H2–H5 on the same 1 dB grid crossed within 0.04 dB of these (1% at −63.70, 3% at −62.51, 10% at −61.17). Harmonic count does not move the reported tenth.

At the named −57 dBFS point this model reads 40.1% THD. The UAD row at the same level is 17.0038%. This ledger does not score that gap.

## Trim

| Aim | Lands a −18 dBFS sine on | Trim | Tag |
|---|---:|---:|---|
| Fit drive-0 reference, the named 1% point | −57.0 dBFS | **−39.0 dB** | VERIFIED |
| UAD stair ~1% | −62.43 dBFS | −44.4 dB | LIKELY |
| This model's 1% bracket | −63.69 dBFS | −45.7 dB | LIKELY |

The gate number is −39.0 dB. It is the recorded mapping. The other two are where 1% THD actually sits.

## Left alone

Neve, compressors, flux, `phi_c`, `vc`, `render_pipeline.py`, `bloom_live.inc`, `live_stereo.c`, wasm, UI, pins, goldens. No UAD binary. No wav kept.
