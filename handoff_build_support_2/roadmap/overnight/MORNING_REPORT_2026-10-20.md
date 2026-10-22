# Morning report — 2026-10-20

**PERROOMK landed. Bloom did not. The app is back to the PERROOMK pin.**

**Restore: the pre-BLOOM zip matches its manifest, including the wasm and `live_stereo.c`. The Temp DLL does not match the old DLL hash.** It was rebuilt from that restored C file and installed. Details are in the restore section.

Bloom stopped on the alias rule. With the Bloom level put back on the tail, the colour stage is louder than the round-3 prototype, and folded images sit above the allowed floor. The same colour stage, fed only the compressed (turned-down) signal, matches that prototype. Room Crush being 0.38 dB quiet at 1 kHz is the fitted tone curve. That was not the stop.

## What you can play

PERROOMK listens are valid. Play these two, in order, from `handoff_build_support_2\roadmap\perroomk\listen\`:

1. `hall_d8_before.wav` — hall at Decay 8 with the old boot k (0.152005). The tail is very long: about 36 s at 500 Hz and about 28 s at 1 kHz.
2. `hall_d8_after.wav` — the same hall with the shipped per-room k (1.664012). The tail is about 9.5 s at 500 Hz and about 7.1 s at 1 kHz. The mean of both channels at 500 Hz and 1 kHz is about 8.3 s.

Both files got the same +8.26 dB boost. Before the boost the peaks were −11.26 dBFS and −12.41 dBFS. After the boost they are −3.00 dBFS and −4.15 dBFS. Limiter off. FDN only, one source, Play path, 12 s, 24-bit, 48 kHz.

Bloom listens were not rendered. There is no B2 set and no guitar set to play.

## Bloom stop

Rule: the overnight chain says stop when a gate is in doubt. The gate is R3-E / R3-B. On all 16 tones (7, 9, 13 and 17 kHz, at four levels), the worst folded image (M1) and the residue under 16 kHz (M2) must be at least 10 dB under the UAD figure in `alias_uad.txt`, or below −90 dBFS. Measure the shipped path.

This is not STOP 1 (goldens did not move). Not STOP 3 (the fully-on cube was under 2.40 ms after the Neve fallback). Clicks, Play-vs-Render, and the Amount-50 limiter listens were not reached.

The compressor table was measured in Python on the shipped chain (gain, then shaper, then EQ), Amount 100, colour on. The script's pass count was 33 of 80 rows. 47 failed. Loud examples, M1 in dBFS, shipped vs UAD (VERIFIED):

| Preset | Tone | Shipped M1 | UAD M1 |
|---|---|---|---|
| Natural | 13 kHz, 0 dBFS | −67.3 | −115.5 |
| Natural | 9 kHz, −12 dBFS | −87.8 | −110.7 |
| Glue | 17 kHz, 0 dBFS | −68.4 | −112.6 |
| Room Crush | 13 kHz, 0 dBFS | −48.0 | −68.9 |
| Nuke | 9 kHz, −12 dBFS | −67.8 | −96.8 |
| Swell | 9 kHz, 0 dBFS | −68.6 | −120.9 |

A second measurement split the gain from the shaper (VERIFIED). "Attenuation only" means the detector's gain reduction and nothing added back, which is how the round-3 prototype was measured. "Shipped" means Bloom's law: Amount minus that reduction, clamped.

| Case | Settled GR | Shipped gain | Attenuation-only M1 | Shipped M1 | Prototype M1 |
|---|---|---|---|---|---|
| Natural 13 kHz, 0 dBFS | 19.77 dB | −7.77 dB | −90.2 | −66.2 | −92.0 (2x) |
| Room Crush 13 kHz, 0 dBFS | 36.14 dB | −15.0 dB | −94.2 | −51.7 | final note −92.2; saved 1x file −76.4 |
| Room Crush 9 kHz, 0 dBFS | 35.95 dB | −15.0 dB | −97.7 | −67.4 | −97.7 |
| Glue 17 kHz, 0 dBFS | 17.55 dB | −5.55 dB | −92.0 | −68.4 | −93.1 (ADAA) |
| Swell 9 kHz, 0 dBFS | 17.98 dB | −5.98 dB | −84.1 | −72.1 | −83.6 (2x) |

Natural's 13 kHz row at the prototype level is under −90. Room Crush's 9 kHz row matches the prototype to 0.1 dB. The shaper and the 2x filter are doing what the prototype did. Bloom then adds the makeup back, the shaper sees a hotter signal, and the images jump by about 20 to 40 dB.

Swell at 9 kHz / 0 dBFS is also loud in the prototype file (−83.6). The round-3 summary still says Swell 2x passed 16/16 at −94.9. Those two records disagree. Tagged UNKNOWN which summary row that −94.9 belongs to. Our attenuation-only number matches the saved prototype line.

The gate script died after the compressor table with `KeyError: 'neve'`. Pre-amp alias rows and the click test did not run. Tagged UNKNOWN. The compressor misses were already enough to stop.

### Options

1. Keep the round-3 oversampling (Room Crush 1x, Glue and Nuke ADAA, Natural and Swell 2x) and treat the louder images as a reported result of the Bloom makeup. The colour block at the prototype's level already matches. No CPU change.
2. Raise oversampling until the shipped-level rows pass, then measure the fully-on cube again. Do not raise the 2.40 ms ceiling. The last fully-on medians were 2.209 and 2.196 ms, so there is little room.
3. Run the shaper before Bloom makeup, then apply the gain. That changes the order the prompt set for the output-side presets (gain, then shape, then EQ).

I did not pick one.

## Room Crush at 1 kHz is the fitted EQ

Small-signal check, −80 dBFS, 1 kHz, shaper plus EQ (VERIFIED): Natural −0.0026 dB, Glue −0.0002, Room Crush −0.3798, Nuke −0.0015, Swell −0.0056. The ±0.05 dB rule fails only Room Crush.

The Room Crush EQ cascade alone is −0.3768 dB at 1 kHz (VERIFIED). The shaper is not adding that drop. R3-B says pack `eq_fit.json` as-is. It was not scaled. Not a stop.

Glue's colour key passed (VERIFIED): missing and explicit false are the same, and the gain matches. Colour on packs Glue's Gs of 2.2945.

## What Bloom had measured before the restore

These were true of the tree at about 03:10. The restore took them back out. CPU numbers are the wasm bench, 4 warmup and 12 rounds, decay-8 cube (VERIFIED, recorded in `CHAIN_LOG.md` and the json files next to this report).

- Off: median 1.747 ms. Spikes 0.
- Follower only (Natural, amount 100, colour off): median 1.776 ms.
- Colour on, pre off: median 1.825 ms.
- Fully on, Neve at 16x: median 2.934 ms. Over 2.40. That was the R3-D fallback case, not a stop by itself.
- Fully on after Neve moved to the simpler nclip_flux model at 8x: median 2.209 ms, then 2.196 ms. Both p90s and both silence-late medians under 2.40. Spikes 38 both times. A spike here means a block slower than 3 times the median, not a block over 2.40. The gate is the median. The 2.40 ms ceiling was not raised.

Off-path audio after the UI and after the drive trim: harness t03 and t04 max-abs 0 (VERIFIED). Empty live MD5 stayed `b6c55d429fa63d6d0d3cd1fcc7d23e88`. Software pytest 164 passed, 0 failed, 7 warnings, 2231.74 s. That run included `test_bloom_off` and the load-sensitive `test_a12`.

The 03:08 log line says the 610-A linear cascade was +58.0 dB at 1 kHz. That figure was a −30 dBFS residual, not the linear gain. The cascade gain was 166.998, about +44.4 dB (VERIFIED). Neve's +47.4 dB on that log line is right (gain 234.915). Both trims were reverted with the C file.

Other notes from the attempt, now absent from the app: the predelay ring holds 4800 samples and the usable delay was capped at 4799 (about 99.98 ms at 48 kHz), not the prompt's 400 ms. The Drive slider on the page was 0–24. The prompt's knob is −12 to +12 around the calibrated point. `live_bytes` had grown to 138406176 from 134707680.

## PERROOMK (landed)

Step 0 wrote `roadmap\overnight\PERROOMK_STEP0.md`. Three factual findings were self-applied on the prompt (a line, a name, or a harness detail). None of them changed sound, a default, a lock, or a tolerance. No Step 0 stop.

With physics on, the Decay dial is the 500 Hz–1 kHz mean in that room. Boot k is unchanged.

| Room | Dial | k | Designed mid | Reachable |
|---|---|---|---|---|
| Boot 6×3×8 | 1.8 / 4 / 8 | 0.7757907003265825 / 0.333072595001391 / 0.15200528288314788 | the dial | yes |
| Hall 57×34.2×97 | 8 | 1.6640124255430147 | 8.0 s | yes |
| Hall | 4 | 3.6461689105649904 | 4.0 s | yes |
| Hall | 1.8 | 4.0 (clamp) | 3.672 s | no |
| Cube, side 340/60 m | 8 | 0.17945068118149424 | 8.0 s | yes |
| Small 4.5×2.8×6 | 1.8 / 4 / 8 | 0.6499310388374295 / 0.2790368814506333 / 0.12734485135157309 | the dial | yes |

Hall dial 1.8 cannot reach 1.8 s. That is the clamp, not a broken solver. Measured FDN-only, colour bypass, one source: Play and Render both 3.685 s, 0.35% off the designed 3.672 s. Dial 4 and dial 8 hit the 15% gate and Play vs Render agree. `ALPHA_MAX` was not changed. Tagged VERIFIED.

No live MD5 moved. Empty `b6c55d429fa63d6d0d3cd1fcc7d23e88`. Centre `b3e6bcd9dfa13ad737d2b15d561f7d30`. Five boot goldens max-abs 0. `d18` and `d4` prefix max-abs 0. Line-0 comb, physics on, max 0.21261059152758685, under the 0.23 limit.

Open, not built: show the max reachable dial on the page. The solver uses the actual cards, which is what the prompt defaulted to. Whether you would rather solve on the default walls is still open.

## Tests against the F13 row

F13 (2026-10-19 18:40), the comparison PERROOMK asked for: pytest 155 passed and `test_a4` failed, then passed alone (F10 flake). Node 38. Selfcheck 45/45. Harness 16 pass, 0 fail, 1 skip, 1 pending, 1 xfail. Acceptance `--slow`: 111 passed, 14 failed, 11 xfailed, 1 skipped. Six known failures. Eight extra fails were slow tests PHYSDEFAULT had skipped.

F9 notes, later the same evening, re-ran pytest 156 passed (38m11s). Harness then 15 pass and 1 fail (t19 surfaces shared-off). That t19 row passed alone twice. Pins did not move. F9 was notes only.

PERROOMK, this chain (VERIFIED, written in `CHAIN_LOG.md`):

- pytest: 161 passed, 1 failed, 37m12s. The failure was `test_a12_visible_controls_post_or_are_ui_only` under suite load. It passed alone in 89.81 s. `test_a4` passed inside the suite. Not a stop.
- Node 38. Selfcheck 45/45.
- Harness t01–t19: 16 pass, 0 fail, 1 skip (t02, no gcc/clang), 1 pending (t06), 1 xfail (t13), 496.97 s. No golden regen. t19 medians: flat shared-off 1.616 ms, shared-on 1.736, Surfaces shared-off 1.592, Surfaces shared-on 1.747. F13 was 1.607 / 1.754 / 1.598 / 1.751. Largest move +0.009 ms.
- Acceptance without `--slow`: 6 failed, 92 passed, 29 skipped, 11 xfailed, 780 s. The six known shapes.
- Acceptance `--slow`, with `-p no:stepwise`: 10 failed, 116 passed, 1 skipped, 11 xfailed, 3017 s. The six known, plus the four slow tests that already failed before this run: early Play/Render gap 0.616 vs 0.3, CPU save −0.094 (F13 was −0.097) with t19 under the ceilings, def_1 250 Hz T30 2.264 s vs dial 1.8, and the P5 coherence row. The long-decay and comb tests passed.

An earlier acceptance launch died in 0.93 s because pytest's own `--sw` clashed with the suite's `--sw`. That was harness plumbing. The rerun with `-p no:stepwise` is the one that counts.

CPU for the PERROOMK gate, page-default early (the early send is off), shared off (VERIFIED): cube key absent median 1.747 ms, explicit false 1.749 ms (F13 1.769 and 1.769). Hall dial 8, two sources, median 1.364 ms (F13 hall 1.408). Spikes 0. A first bench with early forced on sat near 1.92 ms and 1.55 ms. That was the early engine. The page-default rows are the gate.

After the Bloom restore, engine selfcheck was run again: 45/45 (VERIFIED, 2026-10-20 04:10). Node, harness, and acceptance were not re-run. The restored files match the zip taken after PERROOMK had passed those suites. The rebuilt DLL was not what selfcheck loads.

## Versions

| | Before BLOOM (this is the tree now) | During BLOOM (reverted) |
|---|---|---|
| WORKLET_VER | 59 | 60 |
| app.js | `?v=62` | `?v=63` |
| live_fdn.js | `?v=59` | `?v=60` |
| pack_room.js | `?v=52` | `?v=53` |
| wasm sha1 | `843a6eb8c91a9278ba927f643481f3260766a08c` (279668) | `add510df202f98ad875e5c10c8e66b1146ab4f27` (345206) |
| live_stereo.c | `bbdf57994e0996e2c9b77eb8a634550bb71ef3cf` (136434) | `be65976643f4158d8f240003e6ee2d2e3e538e94` |
| Temp DLL | pin `dcde61dfa8ccc17244595244bd3cb7077c7f8433` (285184) | `77a1d0726b7fe80b5ecc210d5d3cd6397be338d9` (303616) |

Installed DLL now: `970e63bb08e5092875b49796ce01ab7ce24dbb01` (285184 bytes). Same size as the pin, different hash. See restore.

## Restore

Backup used: `C:\Users\IdleHanz\Desktop\2011 Room Reverb\software_backup_2026-10-19_preBLOOM.zip`. sha1 `58a0d50b4a49b84ee09c973bb1f1f87f97ca6256`. 95289838 bytes. Manifest `roadmap\overnight\PIN_MANIFEST_preBLOOM.txt`. Every listed file was extracted and re-hashed. 251 manifest rows matched. `Launch Tweak App.bat` has spaces in the name, so the checker had skipped that one line; its hash is `82f93ce64a6059861b3fb78a646193d675082a10`, 1427 bytes, which is the manifest line. Wasm and `live_stereo.c` match the pin. The restored C file does not include `bloom_live.inc`. `index.html` loads pack 52, live_fdn 59, app 62. `WORKLET_VER` is 59. Harness `wasm_run.js` is back to sha1 `c505825f5dbbd5ec74780696ecbfd7217ebacf59`, the same hash Phase 0 recorded. Golden render stamp `software\renders\out_20261013_115900.wav` is still sha1 `7365f08b96981de3b7d0085de7117382471564e9`, 86032844 bytes.

**Temp DLL: not the historical pin.** The zip does not contain the DLL. No copy of `dcde61df...` was still on disk. The Bloom DLL was `77a1d072...`, 303616 bytes. It was replaced by a zig `-O3` build of the restored C so Play does not keep the Bloom binary. The new hash is `970e63bb08e5092875b49796ce01ab7ce24dbb01`, 285184 bytes. The source matches. The binary hash does not. Selfcheck does not load this DLL. A later harness t03 would be the check that the rebuilt DLL matches the PERROOMK wasm.

Left on disk on purpose. The zip did not contain them, and the chain says not to delete them:

- `software\engine\bloom_dsp.py` (the `eq_z` rename is in here)
- `software\engine\bloom_live.inc`
- `software\tests\test_bloom_off.py` — 2 passed in 10 s after the restore. It is not called by the app. The next full pytest will collect it.
- `software\renders\out_20261020_034205.wav` — 961964 bytes, sha1 `f18b5a85987aaa8d6d6d664de1603a254880f8e5`, from the Bloom pytest. Not deleted.

`HANDOVER.md` was not given a Bloom pin. It still says PERROOMK, and it matches the copy saved before the Bloom edits. Harness copies of the Bloom packer are in `roadmap\overnight\_scratch\pack_bloom.py` and `wasm_run_bloom.js`. The live harness files no longer emit Bloom sections.

## Step 0

F9 check: passed at the start of the chain. The F9 row was landed, notes only, and the F13 pin was still in the tree.

PERROOMK Step 0: passed. Three factual items, self-applied. Report `roadmap\overnight\PERROOMK_STEP0.md`.

Bloom Step 0: passed. Seven factual items, self-applied on `BLOOM_RUN_2026-10-19.md`. Report `roadmap\overnight\BLOOM_STEP0.md`. The R3 open items and the "known, for Idle to confirm" note were left open. Swell `max_duck_db` stayed 10.

## Open questions

PERROOMK: solve on the actual cards (this is what shipped) or on the default walls. Show the max reachable dial on the page. Not built.

Bloom, for you, not decided here:

1. Pre Drive hard-clips from about +4 up. Keep that, or stop the knob below the knee?
2. Is the colour audible on the tail at all (harmonics about 50–70 dB down)?
3. Does the Room Crush 25 ms pump sound right on drums?
4. Do the round-3 Natural and Glue dynamics sound closer than the ones we kept? They were not built.
5. Does Swell's smaller intermodulation sound thinner than the UAD at heavy gain reduction?

Known, for you to confirm: Pre colour was going to land before the off-axis tail colour. The queue had the tail colour first.

## Backups

| File | Bytes | sha1 |
|---|---|---|
| `software_backup_2026-10-19_preOVERNIGHT.zip` | 95286342 | `4f9b93e6526461e7fd8b9727f3527fc4691b228c` |
| `software_backup_2026-10-19_prePERROOMK.zip` | 92958140 | `4bb20690b6d60dfd0c886ac3d493629b5207d5d5` |
| `software_backup_2026-10-19_preBLOOM.zip` | 95289838 | `58a0d50b4a49b84ee09c973bb1f1f87f97ca6256` |
| `software_backup_2026-10-19_preBLOOM_INCOMPLETE.zip` | 12937625 | `7913ec1c979aff8103785876f8f0f17fb6d3eaed` |

The incomplete zip missed the golden render stamp. It was moved aside, not deleted, and was not used for this restore. Manifests are `roadmap\overnight\PIN_MANIFEST_preOVERNIGHT.txt` and `PIN_MANIFEST_preBLOOM.txt`.

No other prompt was started.
