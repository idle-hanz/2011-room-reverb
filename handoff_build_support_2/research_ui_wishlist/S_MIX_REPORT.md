# S-MIX report — item 10 closed by D-MIX-J

D-MIX-J (Idle, same day) made Render's early jitter mirror-invariant and regenerated only the Render golden. The stop below is the state before that fix. The landed numbers are in `HANDOVER.md` under S-MIX, heading D-MIX-J.

# S-MIX report — stopped at item 10

**Date:** 2026-10-03. Prompt: `REPORT.md` §7 S-MIX (rebased 18:45; item 11 added 19:00).

**Stop.** `pytest tests` in `software` is **54 passed, 1 failed, 6 warnings** (214.07 s). The failure is `tests/test_s5_surf_tail.py::test_mirror_exact`. Render null **−29.31468981760668 dB**, gate `nd <= -120.0` at line 458. Play max-abs on the same pair is **0.0**. The gate was not loosened, skipped, xfailed, or deleted. No jitter-hash change was made: a mirror-invariant early jitter would move the default Render golden. Item 13: do not start S-OUT, scatter, or smear. A bare continue starts nothing new.

The six warnings are `PytestReturnNotNoneWarning` on `test_ms_classic_null`, `test_mono_cancel`, `test_width_scales_s_only`, `test_room_mic_independent`, `test_any_strip_route`, and `test_each_db_matches_engine`. The assertions in those tests had already run. They are not the failure. This is not “N passed, 0 errors”.

`test_passivity_carpet_ls` passed in the same pytest. Both former setup errors now have a module-scoped `ctx` fixture and actually run.

## Baseline (checked before edits)

Matched. Do not treat this as a baseline miss.

| Pin | At session start | This write-up |
|---|---|---|
| Wasm | `0C7FD78490EAEED0D477D6F613945933EF4AD969`, 213856 bytes, mtime 17:54:56 | Copy still at `%LOCALAPPDATA%\Temp\live_stereo_0c7fd78490ea.wasm`, same SHA1, re-hashed this write-up |
| WORKLET_VER | 47 | **48** (`live_fdn.js`, `index.html` `live_fdn.js?v=48`). S-MIX was required to bump it |
| Goldens | 18:29:47 | Same bytes. Re-hashed below |

Shipped wasm now: `272C0EB16FC6F95686C785C3E6E61947CE55BED9`, 214136 bytes, mtime 20:03:27. `GOLDEN_META.json` still names wasm `0c7fd78490ea` and `when` `2026-10-03 18:29:47`. That file was not rewritten. Its wasm field is the wasm the golden audio was generated from.

## What is in the tree

Items 1–9 and 11 are in the tree. Defaults stay on the old pan law: section 7 is omitted when the signed weights equal plain `side()`, so ORTF and the other current setups at defaults do not send a desk matrix. `g`, the per-line loss, the shared-tail logic, and the SURF cascade were not changed for this miss.

**Coincident S colour, ASSUMED (Idle 15:57).** While S sits on the M point, User-defined shelf and colour theta follow the M axis. Pattern gain stays on the S aim (M yaw + 90°). Once S leaves that point, shelf and colour follow the S axis.

**Shared tail.** M/S with the shared tail on is not the same as per-mic tails. One network feeds every mic. The S-MIX nulls are shared tail off. The shared-tail logic was not retargeted.

**MS classic product path.** Old `ms_decode` stays for bodies that do not activate the desk. A desk-active MS classic sets `ms_decode` false (L = S at +g/−g, C = M at exact linear 1.5, R free). Setting both would double-decode.

## Item 12

### Golden SHA1s

Re-hashed this write-up. Before and after are the same files. Byte-identical at defaults.

| File | SHA1 | mtime |
|---|---|---|
| `play_std_lock18_byp.f32` | `ca052f3f1f9af7c30a30b62139370b3468cb54a7` | 18:29:34 |
| `play_std_lock18_col.f32` | `3774b7d5f284ca445306db153ba9bae35d637651` | 18:29:34 |
| `play_std_unlocked_byp.f32` | `07dc23c3a35c5752f0d4f2a3b767a61f03fa9876` | 18:29:31 |
| `play_std_unlocked_col.f32` | `53024c874192c4e0276be7fea4b1c2ec201f1a19` | 18:29:32 |
| `render_std_unlocked_byp.f32` | `7894bab0da4526c975e78084ecdf62163fada1bc` | 18:29:47 |
| `GOLDEN_META.json` | `e120528bc20cd2f0706ff6a3c653140ab8cbe0c8` | 18:29:47 |

Harness t03/t04 against these files: nulls about −3005 dB, max-abs diff 0. `--perf-scale` stayed 1.0. Goldens were not regenerated.

### Item 7 nulls

Shared tail off, direct 0, early 0, fdn 1, `ir_length_ms` 160, `decay_lock` false. Gates were not loosened. Render lines are from `python software/tests/test_smix_desk.py` (exit 0, `smix desk ok render`) and were collected again by the later pytest (no `SMIX_PLAY`, so that pytest did not re-run Play). Play lines are from `$env:SMIX_PLAY="1"` on the same script (exit 0, `smix desk ok play`). Play does not force colour off.

| Check | Render dB | Play dB | Gate |
|---|---|---|---|
| MS classic, User defined, R off, Width 0 | −252.99 | −161.06 | ≤ −90 |
| MS classic, Bypass, R off, Width 0 | −255.63 | −150.6 | ≤ −90 |
| Mono cancel, C muted, R off, L vs −R and mono rel | −2994.97 / −2994.97 | −2994.97 / −2994.97 | ≤ −200 |
| Width +2, S / M / M-only | −301.73 / −309.15 / −2998.03 | −143.11 / −153.71 / −2998.03 | ≤ −100 |
| Room mic, R muted vs R moved | −2995.55 | −2995.55 | (null) |
| Any strip, C=S/L=M/R=room vs L=S/C=M/R=room | −2995.49 | −2995.5 | (null) |
| Any strip, R=S variant | −311.48 | −2995.5 | (null) |

Room-mic image delay: `delay_ms_r` 5.8009 ms equals `delay_ms_from_distance`, position (4.0, 1.6, 2.2). R-preset-only `each_db`: L 0.0 dB, R 299.8087982965697 dB.

### t19 paired A/B

Same session, app server stopped. Baseline wasm `0c7fd78490ea` vs S-MIX wasm `272c0eb16fc6`. Scene: std lock 1.8, talking_head + trumpet_byu, two sources, source yaw 35 / −25. `bench 4 10`, 12 alternating rounds. Source: `%LOCALAPPDATA%\Temp\smix_t19.json`. Spikes 0 on every round.

Shared off. Median of the new wasm’s per-round medians **2.22355 ms** (ceiling 2.40). Paired median of 100×(new/old−1) **+0.0000444 %** (ceiling +1 %). Both gates true.

| Round | Old ms | New ms | Paired % |
|---|---|---|---|
| 1 | 2.2332 | 2.2167 | −0.739 |
| 2 | 2.2307 | 2.2320 | +0.058 |
| 3 | 2.2214 | 2.2237 | +0.104 |
| 4 | 2.2173 | 2.2315 | +0.640 |
| 5 | 2.2226 | 2.2192 | −0.153 |
| 6 | 2.2281 | 2.2273 | −0.036 |
| 7 | 2.2226 | 2.2234 | +0.036 |
| 8 | 2.2281 | 2.2290 | +0.040 |
| 9 | 2.2165 | 2.2222 | +0.257 |
| 10 | 2.2248 | 2.2070 | −0.800 |
| 11 | 2.2248 | 2.2203 | −0.202 |
| 12 | 2.2276 | 2.2242 | −0.153 |

Shared on, new wasm only. Median **1.74565 ms** (ceiling 2.133). Spikes 0. Rounds: 1.7384, 1.7460, 1.7394, 1.7511, 1.7460, 1.7460, 1.7453, 1.7485, 1.7406, 1.7438, 1.7330, 1.7471.

The harness one-shot in `last_results.json` is not the acceptance pair. It passed: shared off median 2.233 ms (limit 2.40), shared on median 1.744 ms (limit 2.133), spikes 0.

### Harness, selfcheck, pytest

Harness `run_all.py`, `--perf-scale 1.0`, server stopped: **16 pass, 0 fail, t02 SKIP** (no gcc/clang), **t06 PENDING**, **t13 XFAIL**. Counts are not below the 18:29 baseline. `last_results.json` still shows that row, including t19 PASS.

Selfcheck `software/engine/selfcheck.py`: **45/45** (`All 45 checks passed`), including `test_press_grad_and_ms_decode` and `test_desk_fader_and_capsule_weights`. `tests/test_live_stereo.py`: core ok, PASS, `WORKLET_VER` 48. Not re-run for this write-up.

Pytest: see the stop at the top. Baseline was 43 passed and 2 setup errors. Those two tests now run. Carpet passed. Mirror failed its written Render gate.

### Hidden audit and tab tour

`scripts/hidden_audit.py` exit 0. Tabs 7, states 84, visible `[hidden]` elements 0. No confirm dialog: the audit changes `mic_setup` without touching the desk, and the confirm is only after a user desk edit. One product-unrelated console line on the shot run: `GET /favicon.ico` 404. No favicon was added.

Tour, ORTF, visible sidebar ids (`data/smix_shots.json`): edit/source/surfaces `panelRoom`, `panelPreview`, `panelAdvanced`; mic `panelListen`, `panelMics`, `panelAdvanced`; mix `panelPreview`, `panelAdvanced`; space `panelRoom`, `panelHadamard`, `panelAdvanced`; polar `panelListen`, `panelAdvanced`. Shots: `sui2_fixup/shots/tour_ortf_{edit,source,mic,mix,space,surfaces,polar}_smix.png`.

No browser tools in this session. Playwright (`sui2_fixup/scripts/smix_shots.py`, Windows Chrome) is the substitute. Two “Replace the desk…” confirms were accepted on purpose, after the split case had set `desk_touched`. No other dialog.

### Screenshots

Under `sui2_fixup/shots/`:

- Mix, Idle’s scenario: `mix_scenario_smix.png`. Matrix text on that run: `L +1.259 -1.259   C +1.500 +1.500   R +0.175 +0.326`. That is 2011 linear (Width +2 on the S strip, C exact 1.5, R pan +0.3 at the −6 dB fader knot). Constant power would not print 0.175 / 0.326.
- Mic legend: `mic_legend_smix.png`. Swatches from the same run: 20 Hz `rgb(231, 64, 64)`, 63, 125, 250, 1 kHz, 4 kHz, 8 kHz, 16 kHz `rgb(170, 64, 231)`. Hue samples from the unit test: 0.00, 32.84, 50.06, 95.85, 188.38, 239.19, 261.31, 278.00.
- Source plane badge: `badge_measured_smix.png`, `badge_bypass_smix.png` (“preset data: measured”), `badge_user_smix.png` (“user defined”).
- Stack top: `stack_top_smix.png`.
- MS figure-8 strip: `ms_fig8_L_smix.png` (route “S → +L, −R”, rear “−S”).
- At speakers: `polar_speakers_smix.png` (Speaker L and Speaker R). Setup had become Custom because the shot followed a desk edit.

### Item 11

`data/smix_shots.json` (mtime 20:30:08). Measured and Bypass, AB omni, ORTF, MS 3-mic, and Split L/R: max |Δ| of `/api/polar` `each_db` vs `rings_db` above −30 dB is **0.0 dB** on L, C, and R. Drawn grid vs that response: dataMax **0**. Pixel check: maxPx **0**, n=64, on every Measured and Bypass capsule. User defined is shot and not gated (rim-drag radius).

Shots: `mic_each_{ab_omni,ortf,ms,split}_{measured,bypass,user}_smix.png`, plus `mic_each_ortf_pending_smix.png` (three graphs, “updating…”, taken while Measured).

**Room aim, after that JSON.** `mic_desk.js` was saved at 20:32:07. A room-placed strip draws `room_yaw`, and a yaw drag on that strip writes `room_yaw` only. The array yaw and the L/R link are left alone. `mic_each_split_measured_smix.png` was rewritten at 20:32:49. The retake in that session reported drawn yaw L −55°, C 0°, R +20° and maxPx 0. This write-up did not re-open the app, so that yaw triple is not in `smix_shots.json`. The floor plan still draws the array, not the room point.

## Item 10 — why it stopped

`test_mirror_exact` one source. Centred ORTF, W=6 H=3 L=8, source x 1.4 mirrored to W−x, faces A and C swapped, early wet 1, colour Bypass, flat cards of the mean absorb, face A absorb rising to 0.22 plus high-shelf +6 dB. The assert stops on the one-source Render null, so the two-source iteration did not run.

| Bus | Null |
|---|---|
| Play, full IR, L vs mirrored R | max-abs **0.0** |
| Render, full IR | **−29.31 dB** |
| Render direct | −2998.79 dB |
| Render early | **−17.91 dB** |
| Render FDN | −234.65 dB |
| Render early, `lambda_ref` 0 | **−245.69 dB** |

VERIFIED by a fresh render in a new `rr_tests_*` directory, then deleted. The miss is not a stale cache, not the desk fold, and not makeup (the FDN bus is also scaled by makeup and is still −234 dB). Early with the reference wavelength forced to 0 goes to −245.7 dB, so the residue is the seeded path-length jitter.

Default cards keep diffusion / `jitter_D` 0.15 when the test only sets absorb. `jittered_distance` hashes `(seed, image_index, wall letter, mic)`. The mirror test is two separate one-source renders. `mirror_x` is false. Partner image index, the A↔C letter swap, and L↔R do not share that hash, so the jitter does not follow the x-mirror. Play early does not use this hash the same way, which is why Play is exact.

Changing that hash so the two renders match would change default Render early samples. `render_std_unlocked_byp.f32` (`7894bab0…`) is still the 18:29 file, and t04 was max-abs 0. The prompt also requires those goldens to stay byte-identical. Both constraints cannot be met by editing the jitter. The −120 dB assert was left as written.

## Left alone

S-OUT, scatter, and smear were not started. `g`, per-line T60 loss, shared tail, SURF cascade, Hadamard, 1/r², the 0.55 Direct fold, default desk law, and L/R were not retuned for this stop.
