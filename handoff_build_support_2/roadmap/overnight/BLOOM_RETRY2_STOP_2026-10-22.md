# BLOOM RETRY 2 — STOP (2026-10-22)

Step 1 stopped on the alias gate. 79 of 112 tone rows failed. The product tree is the pre-edit backup again. Current pin stays UI-TIDY-1. `WORKLET_VER` is 59. `app.js?v=63`. HANDOVER, BUILD_RUN_LOG, OPEN_FAULTS, and `BLOOM_*.md` were left unchanged. RT-4, Play vs Render, clicks, the null rule, the full suites, the browser pass, B2 listens, and the version bump were not started.

Oversampling was left as shipped: Room Crush 1x, Glue ADAA1, Nuke ADAA1, Natural 2x, Swell 2x, 610-A 8x, Neve nclip_flux 8x. The 0.05 dB RT-2 gate and the 2.40 ms ceiling were left as written. The 10 dB margin and the −90 dBFS floor stay withdrawn.

## Alias gate (STOP, VERIFIED)

Meter is `tone_alias` in `roadmap\bloom\uad\round3\scripts\alias.py`. The score is `%TEMP%\bloom_rt2_alias_score.json` (112 rows). Shipped colour-chain output, after makeup and after EQ, from a scratch wasm tap of the then-current engine. Makeup was left in. Each row was level-matched with one scalar so the fundamental equals the UAD fundamental. Unit is dBc. Pass is our worst image ≤ UAD worst image + 0.5 dB on that row. M1 is the Blackman-Harris folded harmonic. M2 dBc is the below-16 kHz residue peak minus the fundamental. A below-16 kHz peak that is not within 80 Hz of an integer harmonic and sits within 150 Hz of the UAD M2 frequency was excluded from the gated worst and counted below. Same-bin UAD data is not in the csv, so the comparison is worst against worst.

Compressor map: la2as_pr50 → natural, ssl_4_auto → glue, fet_all → room_crush, fc_t5 → swell, dis_nuke_room → nuke. Pre map: `neve` / `u610a` in `alias_uad_tones.csv`, live names `neve1073` / `u610a` via `pre_type()`. Pre UAD levels are −12 / −6 / 0 / +6. Compressor levels are −24 / −12 / −6 / 0. Tones are 7 / 9 / 13 / 17 kHz.

| Preset | Fail / 16 | Worst gap | Row | Ours dBc | UAD dBc |
|---|---|---|---|---|---|
| natural | 15 | +33.70 dB | 13 kHz, 0 dBFS | −70.402 | −104.1 |
| glue | 16 | +21.37 dB | 17 kHz, −12 dBFS | −78.033 | −99.4 |
| room_crush | 4 | +2.00 dB | 17 kHz, 0 dBFS | −56.105 | −58.1 |
| swell | 16 | +40.79 dB | 9 kHz, 0 dBFS | −67.010 | −107.8 |
| nuke | 6 | +51.09 dB | 13 kHz, −24 dBFS | −90.314 | −141.4 |
| neve | 8 | +21.83 dB | 17 kHz, −6 dBFS | −43.674 | −65.5 |
| u610a | 14 | +89.96 dB | 9 kHz, −6 dBFS | −24.436 | −114.4 |

33 rows passed. 30 rows had an M2 peak excluded as a UAD-matching in-band sideband. The exclusion did not clear the worst Room Crush miss: at 17 kHz, 0 dBFS the 14 kHz peak was excluded (UAD M2 is also 14 kHz) and the remaining M1 is still −56.105 dBc against UAD −58.1. At 48 kHz, 2 × 17 kHz folds to 14 kHz. LIKELY that image is the folded second harmonic on the 1x Room Crush path.

Nuke’s −24 dBFS rows sit against a very quiet UAD floor (worst gap +51.09 dB at 13 kHz, ours −90.314, UAD −141.4). The written rule has no −90 dBFS floor, so those rows fail.

### Room Crush 9 kHz, 0 dBFS (VERIFIED, this row passed)

Wasm after makeup and EQ: match gain +2.999 dB, M1 −92.75 dBc at the gated worst, UAD worst −62.0 dBc, M2 −99.568 dBc at 6 kHz. Pass.

The prompt’s −61.731 dBc is `alias_proto_v2.csv` column `m1_dbc` for the prototype at this row. It is not this build. This build’s image is quieter. LIKELY because Room Crush GR is about 36 dB and the shaper sees the attenuated signal.

## Python check of the same chain (VERIFIED)

`apply_fdn_buses` / `_pre_bus` on the then-current `bloom_dsp.py`, printed by `%TEMP%\bloom_rt2_alias_pycheck.py`:

| Row | Fund dBFS | M1 dBc | M1 Hz | Peak |
|---|---|---|---|---|
| natural, 7 kHz, −24 | −13.26 | −91.1 | 13000 | 0.2236 |
| room_crush, 9 kHz, 0 | −15.66 | −89.13 | 21000 | 1.3635 |
| 610-A, 9 kHz, 0 | −2.68 | −7.01 | 21000 | 2643.9157 |

Natural 7 kHz −24 agrees with the wasm row (wasm M1 −91.471 dBc, Python −91.1 dBc). The tap is not the cause of that miss. Python Room Crush 9 kHz is also cleaner than the UAD (−89.13 vs −62.0) and a few dB off the wasm figure (−92.75). Both pass.

610-A linear peak is 2643.9, about +68 dB. M1 is −7.01 dBc at 21 kHz. LIKELY the 03:08 pre level trim, H2 numerators already divided by the 1 kHz cascade. A later job must not divide that gain a second time in C. OS was not raised to hide it.

## Gates that passed, then were reverted (VERIFIED)

These ran on the wired tree. The restore removed that tree. They are not a claim about the restored binary.

- Pilot Nuke 7 kHz, 0 dBFS: |dGR| 0.0, inside the 0.005 dB pilot. Butterworth sidechain was in both engines before RT-2: Nuke and Swell only, `K = tan(π·100/sr)`, `b0 = 1/(1+K)`, `a1 = 1−2·b0`. Natural and Glue had no sidechain high-pass.
- RT-2 Python, 80 rows, amount 100, colour on, last 0.5 s. Nuke, Room Crush, and Swell: dRMS, dPeak, and mean-GR against `dyn3.gr_of` are 0.0 dB. `n_fail` 0. Spot check of the `apply_fdn_buses` feed is max-abs 0.0 on all five presets (output-side `x·10^(−GR/20)`, Swell raw `x`).
- Natural and Glue vs `dyn3` are report-only. Natural dGR +0.015 to +0.155 dB, dRMS −0.155 to −0.015 dB. Glue dGR −0.889 to +0.659 dB, dPeak −0.588 to +1.083 dB. The script field `worst_gated_db` is 1.0829 because it also tracks Glue’s report-only peak. The gated error is 0.0 dB.
- Scratch wasm after the `ls_ln` fix, 80 rows against that Python: worst absolute delta 1.8895314397582297e-6 dB (Room Crush 9 kHz, 0 dBFS, GR). Fails 0. Saved in `%TEMP%\bloom_rt2_rows.json` and `%TEMP%\bloom_rt2_wasm.json`.
- Makeup max over those rows, `W+GR` with the cap: natural 12.0, glue 12.0, room_crush 21.150, nuke 12.0, swell 12.0 dB. Room Crush `max_duck` is 15, so a GR near 36 dB makes about +21 dB of makeup. No extra clamp was added.
- Off path on the wired tree, before the one-line C fix: `test_b2_render_length.py` 2 passed in 380.99 s (d18 and d4 prefix max-abs 0). Selfcheck 45/45, SURF residual 0.2435 dB. Harness t03 and t04 max-abs 0.0. Quick pytest (`test_quick_pins.py`, `test_bloom_off.py`, `test_physdefault_two_source.py`, `test_s_audit_api.py`) 20 passed in 19.20 s.
- Same quick pytest after the `ls_ln` fix: 20 passed in 21.13 s. Selfcheck again 45/45, same SURF residual. The post-fix d18/d4 re-run (task `01a1639f-7d12-7a23-abd1-bad5ded145d5`) was killed at about 174 s with one progress dot. It is not a result. The C-only `ls_ln` fix cannot move the Python render.

Pre-makeup M1 stayed report-only, as IDLE DECISION (2) says.

## `ls_ln` (VERIFIED, then reverted)

`bloom_live.inc` masked the exponent with `& 1023` (10 bits). The IEEE field is 11 bits, so `ls_ln` was right on (0, 2) and wrong for every x ≥ 2. Natural `20·log10(1+u)` broke at GR about 6.02 dB and returned about −6159. Swell `18.1·ln(1+v/8.06)` broke at GR about 12.55 dB and returned about −12834. Room Crush release `ls_ln(g/10)` broke once GR ≥ 20 dB, so settled GR at 0 dBFS was about 15.9 instead of about 36. State was right. The log return was wrong. The off path does not call `ls_ln`. Nuke does not call it on values ≥ 2.

The one-line fix, present only until the restore:

```c
e = (int)((v.u >> 52) & 2047) - 1023;
```

RT-2’s scratch wasm passed after that fix. The restore put the mask back. This turn: `software\engine\bloom_live.inc` line 11 is `& 1023` again, sha1 `ebb0e2c0860070415010ca8aa68374efdcd60323`, 15414 bytes. `live_stereo.c` does not include the file, so the restored audio path does not call it. A later include needs the 11-bit mask.

## Restore (VERIFIED)

Source: `software_backup_2026-10-22_preBLOOMRETRY2.zip`, sha1 `3342de32fee658632e6c70bf59398f1d2b8805fb`, 96057344 bytes, 256 files. Manifest `%TEMP%\PIN_MANIFEST_preBLOOMRETRY2.txt`. The 2026-10-20 preBLOOMRETRY zip and the 2026-10-19 preBLOOM zip were not used.

`bloom_restore.py` printed `MANIFEST_OK 256` (every member sha1 and size). `bloom_survivors.py` printed `survivors 0` under `software\` and the harness golden dir, skipping `.venv`, `__pycache__`, and `.pytest_cache`.

Listen scripts live outside the zip. Both unpacks are back to two values, confirmed this turn:

- `roadmap\bloom\make_listens.py`: `g, gr = bloom_dsp._gain_env(...)`
- `roadmap\bloom\uad\round2\scripts\mk_listen_b2.py`: `g, gr = bloom_dsp._gain_env(...)`

Listen wav `software\renders\out_20261013_115900.wav` sha1 `7365f08b96981de3b7d0085de7117382471564e9`, 86032844 bytes.

Selfcheck after the restore printed `All 45 checks passed`. SURF worst residual 0.2435 dB. This report turn did not re-run selfcheck.

DLL rebuilt twice after the restore, both `6b1612c7bf40ed29ec0adcf1aad97939cf5c8f79`, 285184 bytes, straight to `%LOCALAPPDATA%\Temp\live_stereo.dll`. This turn confirmed that hash on disk. Phase 0 of this job, before any edit, was `8408f9e066b3da59523df8b3f8471cb3e40adc80` (285184). Fallback `970e63bb08e5092875b49796ce01ab7ce24dbb01` was not copied: the rebuild exited 0 and no parity pin moved. UNKNOWN why the same `live_stereo.c` (`bbdf5799`) and the same recipe now hash to `6b1612c7` rather than Phase 0 `8408f9e0`. Zig was stable across the two post-restore builds. The pre-Phase-0 DLL `181d05cd` remains at `%TEMP%\live_stereo_181d_keep.dll`.

## Pins this turn (VERIFIED)

| File | sha1 | Bytes |
|---|---|---|
| `software\engine\live_stereo.c` | `bbdf57994e0996e2c9b77eb8a634550bb71ef3cf` | 136434 |
| `software\engine\bloom_dsp.py` | `ab1f3c4b87044edecb921f72e46e0e74f2366c12` | 34475 |
| `software\static\wasm\live_stereo.wasm` | `843a6eb8c91a9278ba927f643481f3260766a08c` | 279668 |
| `software\static\js\live_fdn.js` | `a936a5f1bfaf62d648c4e8da22d3808a8c73ac11` | 16794 |
| `software\static\js\app.js` | `fb44577e41daca1c3eccfd0e33e27ddf47560e53` | 151737 |
| `software\static\index.html` | `3a56f623b3af107ad67b1fe6ab14ecc1da1e4066` | 68563 |
| Temp `live_stereo.dll` | `6b1612c7bf40ed29ec0adcf1aad97939cf5c8f79` | 285184 |

`index.html` query strings: `app.css?v=35`, `pack_room.js?v=52`, `live_fdn.js?v=59`, `app.js?v=63`, `sl_room_result.js?v=3`. `WORKLET_VER` is 59. The 60 / 64 bump was in the tree before the restore and is gone.

Wasm and DLL that existed only before the restore:

| When | Wasm | DLL |
|---|---|---|
| Phase 0, unmodified C | `843a6eb8` (279668) | `8408f9e0` (285184) |
| Wired, before the `ls_ln` fix | `064135bbde6beb9b82ac7bd7d0726579e09f543c` (370469) | `0eb6b2bbeda7386acd2b865faa9175556a18e784` (315904) |
| Wired, after the `ls_ln` fix | `b75e2af1b1713206e0bbef4be849adbbac3c2f8d` (370445) | `e341ffe9e7f7fd94b6fb633e72c4c3f814a31953` (315904) |
| After restore | `843a6eb8` (279668) | `6b1612c7` (285184) |

Off-path pins that the wired tree held, and that the zip puts back: empty MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88`, centre `b3e6bcd9dfa13ad737d2b15d561f7d30`, two-source `std_lock18` key-absent `a5dcacc67a269c234c4b5745899b038e`, explicit false `0e94bd03d899b76b43adf31ae87f0cd2`, GOLDEN_META `a362cf5e490089807b39346ba207633b88511548`, render `2a806e334e06cc475868d4c3da3fc78431c9a0aa`, play_std_lock18_byp `d011bafca80f4e46ae768db40becd762e78dcada`, play_std_lock18_col `d9470bfad67211180fedc1a07cd2352eaf4b14c7`, play_std_unlocked_byp `91738c70220b4edce512aebe3548dfdbd894cc41`, play_std_unlocked_col `a0ae72d9fb690cb7b3bbd54632abc466cefa0d24`.

## Standing notes

- **23-sample colour latency (VERIFIED in `halfband_47`).** The 47-tap halfband has its centre tap at 23. A 2× up-and-down delays the distortion by 23 samples at 1×. The linear part of the tail is not delayed. This attempt did not add that delay to the whole tail. Direct and early stayed undelayed. Makeup used the same-sample GR, which lines up with the linear part. The distortion sits 23 samples later.
- **Ramp-varying `w` (approximate, reverted).** On the coloured Play path the attempt used `early = full − w·raw` and `fdnPre = bloom_apply(raw)·w + early`. While `w` moves inside a block that split is approximate. It is not in the restored tree.
- **`path_on` (unhandled, reverted).** Moving OLA was left alone. Bloom on a moving path was not wired.
- **Predelay cap (VERIFIED, still in `predelay_samples`).** Ring 4800, usable delay 4799 samples, 99.98 ms at 48 kHz. A 100 ms request clamps there.
- **Threshold trim (PROPOSAL, reverted).** The attempt added `bloom_threshold_db` as a ±24 dB trim on the fitted T, default 0. Absent or 0 left the fit. It is not in the restored tree.
- **`live_bytes` (LIKELY the overnight growth, not re-measured this attempt).** The wired struct was the overnight Bloom struct, including `pdMem` at 3 × 2 × 32 × 4800 floats (3,686,400 bytes). The overnight measurement of that struct was 134707680 → 138406176. This attempt did not print a fresh `live_bytes(48000)` before the restore. The restored tree is the F13 / UI-TIDY-1 layout, whose recorded value is 134707680.

## Left on disk, not product

`%TEMP%\bloom_rt2\` (scratch C, inc, tap wasm), `%TEMP%\bloom_rt2_alias_score.json`, `%TEMP%\bloom_rt2_alias.f32`, `%TEMP%\bloom_rt2_rows.json`, `%TEMP%\bloom_rt2_wasm.json`, `%TEMP%\bloom_restore.py`, `%TEMP%\bloom_survivors.py`. The tap exports were never in the pinned wasm.

## Not started

RT-4 (decay-8 cube, shared off, one compressor at 2× plus Neve 8×, median / p90 / silence-late ≤ 2.40 ms). Play vs Render at −60 dB and GR within 0.01 dB. Clicks. Null rule. Node, full software pytest, acceptance `--slow`, harness. Browser proofs. B2 listens. Docs. A later session starts from this stop, not from the middle of Step 1.
