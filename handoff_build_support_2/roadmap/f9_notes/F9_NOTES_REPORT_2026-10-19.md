# F9 NOTES report (2026-10-19)

Notes only. No sound change. The ruler in `ambience\make_listens.py` now filters each channel and sums the octave energies. The old hypot row is still computed, from the same impulse, and is not the number the notes should quote.

Measure-only entry: `python make_listens.py --measure-only`. It does not call `main()`, `one()`, `play_vs_render()`, `convolve_guitar`, or `wavfile.write`. Output is this folder. Play vs Render scratch files are under `%TEMP%\f9_notes_play_*`.

## Boot check (VERIFIED)

`boot_6x3x8_B_phys`, explicit `phys_ceiling` true, `sub_hp` true, dial 1.8. Proper T20 is 1.9378 / 2.3200 / 2.3160 / 1.9902 / 1.5721 / 1.1137 / 0.8487 s. Max relative error from 125 Hz to 4 kHz against the PHYSDEFAULT corrected row is 0. `k` rounds to 0.775791 (stored 0.7757907003265825). `identity_n` 0.

The hypot row on that same impulse is 2.5606 / 2.0525 / 2.3172 / 2.4053 / 1.9386 / 1.3983 / 0.9774 s, the old F9 line.

## Method (VERIFIED)

Proper: trim 2400 samples, one onset on `|L|+|R|` at 0.1 of the peak, `surf_loop._octave` (3rd-order Butterworth) on each channel, sum the squared bands, Schroeder −5 to −25 dB, four decimals. Hypot: `np.hypot(L, R)` then `surf_loop.t20_per_octave`, same trim. `surf_loop.py` was not edited. Every render passed `phys_ceiling` and `sub_hp` explicitly.

Bands are 63, 125, 250, 500, 1000, 2000, 4000 Hz. Times are seconds.

## Old (hypot) vs proper

### boot 6×3×8

| scene | ruler | 63 | 125 | 250 | 500 | 1k | 2k | 4k | k | id |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_today | hypot | 1.5900 | 1.8228 | 1.5377 | 1.5859 | 1.6237 | 1.7294 | 1.8354 | | |
| A_today | proper | 1.2943 | 1.7612 | 1.8400 | 1.7971 | 1.8233 | 1.8332 | 1.8288 | | |
| A_old | hypot | 1.5520 | 1.8125 | 1.4877 | 1.6190 | 1.6273 | 1.7231 | 1.8395 | | |
| A_old | proper | 1.2995 | 1.7702 | 1.8401 | 1.7971 | 1.8234 | 1.8332 | 1.8288 | | |
| B_phys | hypot | 2.5606 | 2.0525 | 2.3172 | 2.4053 | 1.9386 | 1.3983 | 0.9774 | 0.775791 | 0 |
| B_phys | proper | 1.9378 | 2.3200 | 2.3160 | 1.9902 | 1.5721 | 1.1137 | 0.8487 | 0.775791 | 0 |
| C dial 4 | hypot | 4.7309 | 4.5802 | 4.4609 | 4.5693 | 4.2309 | 3.3090 | 2.1385 | 0.333073 | 2 |
| C dial 4 | proper | 2.7932 | 3.9176 | 4.4059 | 4.2222 | 3.4832 | 2.4945 | 1.7350 | 0.333073 | 2 |
| D dial 8 | hypot | 8.1111 | 8.2726 | 8.4278 | 7.6465 | 7.7786 | 6.4817 | 4.0173 | 0.152005 | 3 |
| D dial 8 | proper | 3.2813 | 5.4715 | 6.9630 | 7.9890 | 6.8769 | 4.7539 | 3.0039 | 0.152005 | 3 |

### 4.5×6×2.8

| scene | ruler | 63 | 125 | 250 | 500 | 1k | 2k | 4k | k | id |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_today | hypot | 0.8840 | 1.3877 | 1.8174 | 1.7040 | 1.7328 | 1.8309 | 1.8242 | | |
| A_today | proper | 1.0292 | 1.5691 | 1.8028 | 1.8007 | 1.8503 | 1.8320 | 1.8119 | | |
| B_phys | hypot | 0.9891 | 1.7095 | 2.0835 | 1.9180 | 1.5583 | 1.2195 | 0.8280 | 0.775791 | 0 |
| B_phys | proper | 1.3142 | 2.0125 | 1.9413 | 1.6878 | 1.3983 | 0.9714 | 0.7463 | 0.775791 | 0 |
| C dial 4 | hypot | 4.5968 | 3.5409 | 3.9744 | 3.8972 | 3.6604 | 2.9076 | 1.8516 | 0.333073 | 1 |
| C dial 4 | proper | 1.7609 | 3.3231 | 3.7966 | 3.7319 | 2.9895 | 2.1631 | 1.5262 | 0.333073 | 1 |

### 3×4×2.5

| scene | ruler | 63 | 125 | 250 | 500 | 1k | 2k | 4k | k | id |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_today | hypot | 1.5597 | 1.6179 | 1.8229 | 1.7295 | 1.7701 | 1.7227 | 1.8083 | | |
| A_today | proper | 0.6843 | 1.2604 | 1.3565 | 1.6146 | 1.8341 | 1.8125 | 1.8218 | | |
| B_phys | hypot | 0.7537 | 1.0466 | 1.2590 | 1.1620 | 1.1987 | 0.9225 | 0.6286 | 0.775791 | 0 |
| B_phys | proper | 0.7792 | 1.3020 | 1.2689 | 1.1426 | 1.0376 | 0.7701 | 0.5715 | 0.775791 | 0 |
| C dial 4 | hypot | 2.5466 | 3.0739 | 2.5065 | 2.2720 | 2.2187 | 2.3179 | 1.5181 | 0.333073 | 0 |
| C dial 4 | proper | 1.1239 | 1.8056 | 1.7786 | 2.3561 | 2.3149 | 1.6198 | 1.2102 | 0.333073 | 0 |

### 2×2.5×2.2

| scene | ruler | 63 | 125 | 250 | 500 | 1k | 2k | 4k | k | id |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_today | hypot | 0.3207 | 1.1017 | 1.7301 | 1.8279 | 1.7841 | 1.7631 | 1.8011 | | |
| A_today | proper | 0.1293 | 0.6527 | 1.0950 | 1.5702 | 1.7780 | 1.7847 | 1.7912 | | |
| B_phys | hypot | 0.1718 | 0.4461 | 0.7687 | 0.8786 | 0.8659 | 0.7003 | 0.4593 | 0.775791 | 0 |
| B_phys | proper | 0.1284 | 0.5936 | 0.8595 | 0.9059 | 0.7802 | 0.5291 | 0.4405 | 0.775791 | 0 |
| C dial 4 | hypot | 0.4513 | 2.0940 | 2.3118 | 1.7568 | 1.7154 | 1.7449 | 1.0754 | 0.333073 | 0 |
| C dial 4 | proper | 0.1909 | 1.0840 | 1.3602 | 1.8254 | 1.6998 | 1.1800 | 0.9084 | 0.333073 | 0 |

`k` above is the stored value rounded to 6 decimals. Dial-off rows have no physics `k`.

## Play vs Render (VERIFIED)

Room `2×2.5×2.2`, explicit `phys_ceiling` true, `sub_hp` true, dial 1.8. Render impulse vs Play `wasm_run.js` into `%TEMP%`. Null −78.34 dB. Max abs 1.0497e-5. `k` 0.775791. `identity_n` 0. File length 2.79 s.

Proper T60, Render: 0.1284, 0.5936, 0.8595, 0.9059, 0.7802, 0.5291, 0.4405. Play: 0.1284, 0.5936, 0.8595, 0.9059, 0.7802, 0.5291, 0.4404. They match through 2 kHz. At 4 kHz they differ by 0.0001 s. Hypot rows are equal: 0.1718, 0.4461, 0.7687, 0.8786, 0.8659, 0.7003, 0.4593.

## F12 (quoted, not re-measured)

2026-10-19 figures already in OPEN_FAULTS: 926 Hz 1.366 s, 1623 Hz 1.172 s, longest 800 Hz–4 kHz band 1.552 s at 800 Hz. The 3.8 s figure is the old hypot path.

## Order

Per-room k (IDEAS row 99, PERROOMK) is not in this tree. F9 NOTES ran first. It is notes-only and boot-room based. Boot `k` is unchanged. PERROOMK must re-measure non-boot rooms with the proper ruler.

## What changed in `make_listens.py`

`octave_t60` no longer builds `np.hypot(L, R)` and then calls `t20_per_octave`. It trims 2400 samples, takes one onset on `|L|+|R|` at 0.1 of the peak, runs `surf_loop._octave` on each channel, sums the squared bands, and fits the Schroeder slope from −5 dB to −25 dB. `octave_t60_hypot` keeps the old ruler for the comparison row. `--measure-only` renders the fourteen overs from the four-room loop through `impulse_ir` and writes only `f9_remeasure.json`. The source note in `main()` names the new method. `main()` was not run.

## Gates

No `f13_baseline` or `uad_measure` process was running.

| gate | result | time |
|---|---|---|
| Selfcheck | 45/45 | 18.3 s |
| Node `software\tests` `*.mjs` | 38 pass, 0 fail | 0.4 s |
| software pytest | 156 passed, 0 failed, 7 warnings | 38m11s (21:40–22:18) |
| Harness `run_all.py` | 15 pass, 1 fail, 1 skip, 1 pending, 1 xfail | 9m36s (22:18–22:28) |
| Harness t19 alone | pass | 49.1 s, and again 45.6 s |

`test_a4_binaural_hides_dead_rows` and `test_colour_stays_finite_and_realtime` both passed inside the pytest run, so neither was re-run alone. The harness failure is t19, surfaces shared-off: silence median 2.30 ms against play median 1.62 ms. That is 1.42× the 1.3× ratio. The 2.40 ms ceiling held. Alone, shared-off silence median was 1.843 ms against play median 1.631 ms, and the whole test passed. A second alone run also passed (play median 1.628 ms, silence median 1.742 ms). Wall-clock flake. No code change.

Pytest's render-stamp keeper wrote `software\renders\out_20261019_220837.wav` and deleted `out_20261013_115900.wav`. The deleted file was restored from `software_backup_2026-10-19_preF13.zip` (sha1 `7365f08b96981de3b7d0085de7117382471564e9`, 86032844 bytes) and the new stamp was removed. After that, the software tree (236 files, caches and `.venv` left out) and `ambience\listen\` (18 files) match the before SHA1. `out.wav` was never in the diff.

## Pins before and after (VERIFIED)

Wasm `843a6eb8c91a9278ba927f643481f3260766a08c` (279668). `live_stereo.c` `bbdf57994e0996e2c9b77eb8a634550bb71ef3cf`. Temp DLL `dcde61dfa8ccc17244595244bd3cb7077c7f8433`. `render_pipeline.py` `5fb71ad02be38dfb6a7d771e0032d6c959431434`. `app_server.py` `77ed1542be77105b62fdc29bd4e037536acf7a0b`. `fdn_worklet.js` `b39ccd9178c7ecf7145b3e267283b0b07aa6749d`. `live_fdn.js` `a936a5f1bfaf62d648c4e8da22d3808a8c73ac11`. Harness `wasm_run.js` `c505825f5dbbd5ec74780696ecbfd7217ebacf59`. GOLDEN_META `a362cf5e490089807b39346ba207633b88511548`. Five goldens `d011bafc…`, `d9470bfa…`, `91738c70…`, `a0ae72d9…`, `2a806e33…`. `WORKLET_VER` 59. `pack_room.js?v=52`, `live_fdn.js?v=59`, `app.js?v=62`, `sl_room_result.js?v=3`. Same before and after.

## Docs

- `HANDOVER.md` Current pin: F9 NOTES bullet. Pins not moved.
- `HANDOVER.md` AMBIENCE boot IR line: hypot correction after the original `+20%` sentence. Original numbers kept.
- `HANDOVER.md` AMBIENCE listen line: pointer to `f9_remeasure.json`. The four room rows are marked as that ruler.
- `HANDOVER.md` SMALLDECAY listen lines: hypot bias, bass sentence, 926 Hz superseded by 1.366 s.
- `HANDOVER.md` PLACE re-measure line: same biased ruler.
- `OPEN_FAULTS_2026-10-18.md` F9 closed. The section-fit sentence is corrected. F12's hypot sentence was already there and was left.
- `OPEN_FAULTS_2026-10-10.md`: F9 closed 2026-10-19.
- `IDEAS_BACKLOG_2026-10-19.md`: F9 closed, F12 numbers updated, options 2 and 3 added as unscheduled backlog, row 99 records that F9 ran first.
- `BUILD_RUN_LOG.md`: F9 NOTES row.
- `smalldecay\listen\listen_report.json` note only. Numbers unchanged.

No engine, page, wasm, golden, or test file was edited. Nothing you hear changed.
