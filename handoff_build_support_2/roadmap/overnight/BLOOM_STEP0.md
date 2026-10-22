# BLOOM Step 0 (overnight, 2026-10-20)

Review only. No product file was edited for this review. Verdict: **no Step 0 STOP**. Step 1 may start. Tags below are VERIFIED unless marked LIKELY or UNKNOWN.

The live pin is PERROOMK (HANDOVER Current pin, 2026-10-20). F13 has landed. PERROOMK has landed. Neither is mid-run. PERROOMK did not bump `WORKLET_VER` or `app.js?v=`. BLOOM still starts at 59 and 62 and bumps to **60** and **63**. `pack_room.js?v=` stays 52 unless that file changes, then 53.

## 0. Baseline (VERIFIED)

| Pin | Live value BLOOM starts from |
|---|---|
| WORKLET_VER | 59 (`software/static/js/live_fdn.js:20`) |
| app.js?v= | 62 (`software/static/index.html:969`) |
| pack_room.js?v= | 52 (`index.html:963`) |
| live_fdn.js?v= | 59 (`index.html:964`) |
| wasm | `843a6eb8c91a9278ba927f643481f3260766a08c`, 279668 bytes |
| live_stereo.c | `bbdf57994e0996e2c9b77eb8a634550bb71ef3cf`, 136434 bytes |
| Temp DLL | `dcde61dfa8ccc17244595244bd3cb7077c7f8433`, 285184 bytes |
| GOLDEN_META | `a362cf5e490089807b39346ba207633b88511548` |
| play_std_lock18_byp / col | `d011bafca80f4e46ae768db40becd762e78dcada` / `d9470bfad67211180fedc1a07cd2352eaf4b14c7` |
| play_std_unlocked_byp / col | `91738c70220b4edce512aebe3548dfdbd894cc41` / `a0ae72d9fb690cb7b3bbd54632abc466cefa0d24` |
| render_std_unlocked_byp | `2a806e334e06cc475868d4c3da3fc78431c9a0aa` |
| empty / centre MD5 | `b6c55d429fa63d6d0d3cd1fcc7d23e88` / `b3e6bcd9dfa13ad737d2b15d561f7d30` |
| explicit-false empty / centre | `ce009a4ccc3d85f87aa6547f59eda0e4` / `35972c29a63dbe5b33d228b68e6e575b` |
| two-source std_lock18 key absent / explicit false | `a5dcacc67a269c234c4b5745899b038e` / `0e94bd03d899b76b43adf31ae87f0cd2` |

Decay-8 cube CPU from the PERROOMK pin (page-default early, shared off, two sources, colour on, Surfaces): key absent median 1.747 ms, explicit false 1.749 ms. Ceiling stays 2.40 ms. F13's row was 1.769 / 1.769.

Version pins that move if the worklet or the page changes:

- `live_fdn.js:20`, and the wasm / worklet query strings at `live_fdn.js:181` and `live_fdn.js:184` (they already use `WORKLET_VER`).
- `index.html:964` (`live_fdn.js?v=`) and `index.html:969` (`app.js?v=`). `index.html:963` (`pack_room.js?v=`) only if `pack_room.js` changes.
- `software/tests/test_quick_pins.py:73` and `:75`.
- `software/tests/test_b2_render_length.py:56`.
- `software/tests/test_live_stereo.py:614`.
- `software/tests/test_mic_colour_relative.py:989`.
- `3_phase_acceptance_tests/tests/test_p1_blob.py:11-24` (agreement check, no hardcoded 59).

Backup before any BLOOM edit: `software_backup_2026-10-19_preBLOOM.zip`, sha1 `58a0d50b4a49b84ee09c973bb1f1f87f97ca6256`, 95289838 bytes, 252 files. The first zip of that name (sha1 `7913ec1c979aff8103785876f8f0f17fb6d3eaed`, 12937625 bytes) missed the 86 MB render stamp. It was moved aside, not deleted: `software_backup_2026-10-19_preBLOOM_INCOMPLETE.zip`. The stamp `software/renders/out_20261013_115900.wav` was restored from the prePERROOMK zip (sha1 `7365f08b96981de3b7d0085de7117382471564e9`, 86032844 bytes). The pytest stamp `out_20261020_002122.wav` was removed. Manifest: `roadmap/overnight/PIN_MANIFEST_preBLOOM.txt`.

## 1. Tail return point (VERIFIED)

`yBlk` is filled in `bus_sample` (`live_stereo.c:2657`, and the later stores at 2668, 2813, 2825, 2829). `mix_partition` is `live_stereo.c:3277`. `soft_limit` is `live_stereo.c:520`, called at `live_stereo.c:3450-3451` after dry is added (`3442-3443`). Render's `apply_soft_limit` is `render_pipeline.py:434`, called at 2064, 2269, and 2408.

Do not scale `yBlk` in place. Shared tail writes `yBlk[BUS_C]` back into the L ring at `live_stereo.c:3592` (bank B at 3593).

The FDN term, and only that term, is scaled in three places, all before makeup is applied to the sum and all before the limiter:

1. Colour off, not binaural. `sumY` of `yBlk + yBlkB` at 3299 and 3315. The FDN term is `fdn_wet * sumY` (3319) or the ramp `RG_FDN * sumY` (3305). Early is `esBlk`, added beside it. Direct is `daBlk + dbBlk`.
2. Colour on. `paint_lines` fills `fdnPre` from the FDN lines only (3340-3341, 3388). Early of L/R is added into the same FIR input or into `ident`, which is then added onto `fdnPre` (3391). Centre early `esBlk` is added beside `fdnPre` (3402, 3410). So `fdnPre` is **not** a pure FDN term on L/R when early is mapped into the FIR. The pure FDN contribution is the `paint_lines` sum **before** `ident` is added. Bloom gain, Bloom colour, and Pre colour go on that FDN sum, then `ident` and centre early are added unsccaled.
3. Binaural. `ic_apply` writes `oL` / `oR` at 3422. The FDN term is `fdn_wet * oL/oR` at 3425-3431. Direct and early are not in `oL`/`oR` (ic_collect runs only when `icOn`, and the colour-off path skips `sumY` in that case).

Per output bus, not per line. A per-line shaper would sit before `paint_lines`, and those FIRs also carry early lanes, so a per-line scale can touch early. The bus point exists in all three paths and in Render (the driven tail is already a bus sum). Cost is one gain, one shaper chain, and one pre chain per bus per sample, times two channels after the L/C/R fold. That is the cheaper point that can match Play and Render.

Order at that point, before the limiter (LIKELY, from section B's side column plus R3's single EQ series):

- Output-side presets (Natural, Room Crush, Nuke, Glue when `glue_colour` is on): `gB`, then the shaper, then the EQ series.
- Swell (input side): shaper on the pre-gain FDN sum, then `gB`, then the same single EQ series. R3 gives one biquad series, not a pre/post split. There is no separate EQ_pre.
- Glue with the key off or absent: no shaper, no ADAA, no DC blocker, no EQ. Bit-exact with Glue and colour off.
- Amount 0: the multiply is skipped, not a 0 dB multiply.

## 2. Tail input point (VERIFIED)

Predelay is on the tank copy only, after the high-pass, before `LS_DC` (`live_stereo.c:129`).

One source does not call `fdn_excite`. The tank copy is inline at `live_stereo.c:2646-2657`: early is stored from the unfiltered `xin` at 2634 or 2644, then `sub_apply` at 2650 when `subHpOn`, then `tank + LS_DC` at 2651 and 2654. Predelay delays `tank` after 2650 and before the `LS_DC` add. Early keeps `xin`.

Two sources use `fdn_excite` at `live_stereo.c:2517-2520` (`tint`, then `sub_apply` when on, then `+ LS_DC`). Callers at 2715 and the matching bank-B sites feed `xinArr`, which is the tank. Early is a different write. Predelay goes inside that helper only when the delay is non-zero, so the off path never touches the new state. The same pattern as `subHpOn`.

## 3. Return vs input (not a STOP)

D-BLOOM (2026-10-18) says the follower steers what goes into the FDN and how loud the tank comes back. Hard rule 1 of this run (2026-10-19, later and specific) puts the whole Bloom gain on the return and only Predelay on the inject. Step 1 follows Hard rule 1. This is the narrowing item 3 asks to name. It does not change makeup, `g_decay`, 1/r, or the tank. Sustain is not built.

## 4. Render structure (VERIFIED)

`render()` is `render_pipeline.py:2548`. The default path convolves a combined IR (`fft_convolve` around 2164). Movement already sets `include_fdn=False` (2211) and drives `render_fdn_ir` (`1117`) with `drive=dry` (2231-2248).

The drive branch inside `render_fdn_ir` runs only when `movement_ms > 0` (1153). With Bloom off, Movement 0 stays on today's IR path. Step 1 adds a Bloom-on branch that does the same three things at Movement 0: `include_fdn=False`, drive the tank with the real excitation, and apply `gB`, Bloom colour, and Pre colour on the FDN bus sum. One source, two sources (A and B tanks), and binaural (`render_binaural_fdn_ir` at 1252 has no drive argument today; Step 1 either drives it the same way or, if the point cannot be shared, forces Bloom and Pre colour off for binaural and greys the row, as Part 2 allows).

The detector reads the dry input in both engines. Render's dry is the file passed to `render()`. Play's dry is the input block before the tank. They are the same samples when the guitar check uses `wasm_run.js` pcm mode against `render()`.

With every Bloom key off, Render does not enter the drive branch. That is the bit-exact path.

## 5. Predelay sites and memory (VERIFIED plan)

`LANES` is 4 (`live_stereo.c:104`). `LANE_FDN` is 0. `CAP_MAX` is 192000 (`live_stereo.c:103`). `PART` is 128.

Do not add a ring lane. Changing `LANES` would reindex the existing delay memory.

Use a separate integer delay of the tank scalar (option c), one ring per source, length `round(0.100 * sr)` and never more than `round(0.100 * CAP_MAX)` = 19200 samples. At 48 kHz that is 4800 samples, about 75 KB for two double rings. At 192 kHz, about 300 KB. The off path does not read or write them.

Range 0-100 ms, `round(ms * sr / 1000)` samples. 0 samples is the absent section. Render shifts the driven excitation by the same count before `process_block_poly`. Early and direct are not shifted.

CPU of the delay itself is one read and one write per sample per source. It is not the expensive part. The expensive part is Neve at 16x (R3-D).

## 6. Detector (plan, not a STOP)

Feedforward on the dry. One linked follower per engine. Two sources: `max(|xA|, |xB|)`.

Sidechain HPF only where the 19 Oct JSON already has one. Swell's `sidechain_filter` is a 100 Hz, 6 dB/oct HPF (`compressor_presets.json` swell block). Nuke keeps the 100 Hz HPF from section A. Natural's R37 emphasis is not built. Glue and Room Crush stay as their JSON (Step 1 reads the key; it does not invent a filter).

Control rate is not used. Nuke's attack constant is 0.325 ms (`fit_nuke.json` `ta`). An 8-sample hold at 48 kHz is 0.167 ms. Item 6 says to run per sample unless an 8- or 16-sample computer is shown to move t63/t90 by 5 % or less. Step 1 runs per sample in both engines. No new coefficient.

## 7. Discrete equations (R3-A overrides the section A refit)

Pack the full double from the JSON. The prompt's printed figures match those doubles to the printed rounding. Checked this review:

- Nuke `fit_nuke.json` `params`: T -19.784136516148283, ta 0.0003251699358163522 s, trf 0.05092566450470256 s, trs 0.4071207648333795 s, ws0 0.36192251013256727, wsg 0.0658924046610099, tg 0.4621846347567713. Update is `nuke_det` in `roadmap/bloom/uad/round3/scripts/dyn3.py:46`. Label `UAD-round3-fit`.
- Room Crush `fit_room_crush.json`: T -37.87520857188871, R 30.0 (bound), W 8.250634004965589, ta1 0.00043493855480228615 s, ta2 0.001096405978700386 s, wa 0.81323744332744, lag 0.002 s, tr 0.025044333627283144 s, beta 0.3726524028730669. Update is `rc_det2` (`dyn3.py:63`). The ALL creep is not built. Label `UAD-round3-fit`.
- Swell `fit_swell.json`: T -26.21858776580744, R 1.7676822816874964, W 6.619520494526682, R2 6.0557605934358465, K2 8.24944457745325, ta 0.0023334613848280117 s, CT 4e-6, RT 146474.70785867795, RU 153168.37197239872, CU 1.0866306462698908e-05. No 10 dB clamp inside the gain computer. The tail safety cap stays `max_duck_db` **10** (`compressor_presets.json` swell `bloom_defaults`). The "0.19" in section A is not that field. `fit_swell.json` `gr_ours` contains 0.19 as a curve sample. Label `UAD-round3-fit`. rel63 +35 % / +31 % stays a reported miss, not STOP 7. The cap is not deepened. If a gate can be passed only by deepening it, that is STOP 6 and Step 1 stops.
- Natural and Glue keep `roadmap/bloom/uad/round2/scripts/models.py` `run_preset` (lines 121-128): Natural is `opto_light_memory` with a1 0.002 s, a2 0.16 s, wf 0.8, tm 0.3 s, tmd 0.3 s, and the release weights hardcoded at `models.py:49-51`. Glue is `series_two_section` with knee W 12, attack 0.010 s, tau1 0.0428 s, tau2 5.1 s, C1 0.47e-6, C2 6.8e-6. Section A's two-stage opto and Glue knee 6 / attack 6.5 ms are not built. Label on those constants stays the 19 Oct JSON status (`UAD-measured` where the file says so). The round 3 `opto2` fit is not used.

Gain law (Part 2, unchanged): `GR_dB` from the model is ≤ 0 in the Bloom sense after the sign flip (the scratch models emit positive GR). `wet_gain_dB = clamp(Amount_dB + GR_dB, -max_duck_db, +Amount_dB)` with `GR_dB` negative. Amount 0 skips the path. Amount percent maps as `Amount/100 * 12 dB`, then the preset cap. Attack and Release scales ×0.25 to ×4, attack floor 0.1 ms except Nuke at ×1 keeps its 0.325 ms coefficient so the 0.9 ms t63 target can be met.

Thresholds for Natural and Glue come from the current fit files (`static_fit.json` / the T argument `run_preset` already takes), not from a new ear choice. Step 1 reads them. It does not invent one.

## 8. Bloom colour (R3-B)

Ships from `data/colour_choice.json` and `data/eq_fit.json`. Printed coefficients match the JSON to rounding. Examples: Natural a2 -0.03854772692379803, a3 -0.1277549972366719, d0 0.420839645153811, Gs 1.2586302026251. Room Crush vr_db -13.650368620662704, b -1.2760581111273925, fc 591.9386249804384. Swell d0 is 1.0, so depth is constant; the JSON also carries Gs 0.5115222760420124, which the constant law does not use. Glue a2 0.002194475495254785, a3 0.47708951668185645, fc 207.6514310914332, and the JSON has no requirement to default the key on.

`glue_colour` missing means off. Null rule: colour on must not worsen any whole-output null by more than 0.5 dB versus colour off. A preset that fails ships colour-off. That is a reported outcome, not a stop. Vari-Mu HF IMD is not built.

Alias schemes: Room Crush 1x, Glue (key on) ADAA1, Nuke ADAA1, Natural 2x, Swell 2x. Halfband FIR 47 taps, Blackman, linear phase. 2x delay is 23 samples, compensated on the tail only, and only while that colour is on. ADAA1 uses the small-difference midpoint fallback, same code in Python and C.

EQ is the `biquads` list in `eq_fit.json` (a0 = 1, pack b0 b1 b2 a1 a2). No 20 Hz high-pass is added on top. Other sample rates redesign from the same fit in Python and the error is reported.

## 9. Pre colour (R3-C)

`data/pre_choice.json` full doubles. 610-A `nclip_flux`: vc_db -16.76700034210179, p0 12.572117815115975, p1 -0.11687860855758445, p2 -0.0077564898364037346, phi_fc 199.81961468763458, phi_db -9.756279503174206, phi_c -0.041302812595903786. Neve `nclip_emph_flux_mem`: vc_db 9.18795794644513, p0 29.999999999872756 (the bound printed as 30), p1 0.11931660973983067, p2 7.933841882649045e-05, emph 811.8627829191987 Hz at -2.798532018422813 dB, phi_fc 199.99999999999997 (printed 200), phi_db 21.21085844932143, phi_c 0.05294798519698174, mem_m 0.5750908379906007, mem_tau 0.018873659681309062 s.

The 20 Hz note in section C (−1.5 dB vs about −7 dB) is the old linear-table reconciliation. R3 replaces that form. The linear path is still the 8192-tap kernels in `data/kernels.npz` until a 2-4 biquad IIR is fitted. Step 1 fits that IIR in Python before any pre-colour C code. If the IIR costs more than 1 dB on any held-out row, that is STOP 6 (FIR cost vs sound). Options then: ship the pres off, or ship the FIR if the CPU still fits, or stop. This review does not pick one.

Ship rules stay: 610-A at least 6 dB better than linear on held-out vocal and wet mix; Neve median at least 0.5 dB better and never more than 0.5 dB worse. A failure hides that type. Not a stop. Oversampling: 610-A 8x, Neve 16x, cascaded FIR47. If the cube fully-on median goes over 2.40 ms, Neve falls back to `nclip_flux` at 8x (`prefit_neve_nclip_emph_nclip_flux_nclip_emph_flux.json`) and is measured again. If it is still over, STOP 3. Drive mapping stays the round 2 map. Drive is not limited below the knee (open item 1).

## 10. Plumbing (plan)

Keys, present in the live dict and the blob only when on: `bloom_preset`, `bloom_amount`, `bloom_threshold_db`, `bloom_attack_scale`, `bloom_release_scale`, `predelay_ms`, `bloom_colour`, `glue_colour`, `pre_colour`, `pre_drive_db`. Amount 0, Predelay 0, colour off, pre off, and a body that sets those explicitly, all hash like a body that omits them.

Sections, only when on, ids free today (1-9 are taken in `pack_blob_v2` at `render_pipeline.py:3348-3359`):

- 10 BLOOM: envelope coefficients, colour coefficients, EQ biquads, scheme id. Absent when Amount is 0 and Bloom colour is off.
- 11 PREDELAY: one float, the sample count. Absent at 0.
- 12 PRE_COLOUR: filters and shaper. Absent when the type is off.

`nsec` max 16 is `live_stereo.c:1740`. A current pack emits at most 9 sections, so three more fit. Harness t01 must still match `packRoom` byte for byte, including the new sections when on and their absence when off. `live_load_room` (`live_stereo.c:1706`) ignores unknown ids today; Step 1 adds readers for 10, 11, and 12 that do nothing when the section is absent.

`params_from_body` is `app_server.py:484`. `DEFAULTS` is `app_server.py:80`. `live_fdn_params` is `render_pipeline.py:2759`. The worklet packer is the JS twin of `pack_blob_v2`. Off bodies must not grow a key. That is the same rule as `sub_hp` explicit false.

## 11. State and clicks (plan)

New state sits on `LiveStereo`, next to `harmZ` / `subZ`, and `scrub` (`live_stereo.c:2838`) zeroes it. A room reload (`live_load_room`) must not zero it, or the tail clicks. Colour on/off and Pre colour on/off use `arm_ramps` / `rampBlk` (about 15 ms). Bloom off to on starts at 0 dB of extra gain. On to off ramps to 0 dB and colour depth 0 before the section drops. Pre colour crossfades linear to coloured over the same ramp.

## 12. UI (plan)

`#mixViews` is `index.html:191`. The FDN strip and the check rows are in that view. `#mixHint` is `index.html:315`. `#naturalBtn` is `index.html:262` (`app.js:978` and `:1218`, `state.natural_bus` at `app.js:132`). The Bloom preset label is "Bloom: Natural", not a second Natural button.

New `state` fields sit next to line 132 and match new `DEFAULTS` entries: preset natural, amount 0, threshold from the preset's calibrated value but stored as the off default, attack scale 1, release scale 1, predelay 0, bloom colour off, glue colour off, pre colour off, pre drive 0. Amount 0 keeps the keys out of the live dict. `test_p0_5_server_defaults_equal_client_state` already fails on `align_horizontal`, `link_mode`, and `pair_mode`. Step 1 does not touch those. New keys must not add a fourth mismatch.

Hints: "Bloom lifts the room between notes. Direct and early are untouched." and "Pre colour adds the 610-A or Neve preamp's saturation to the room only." Layout check at 1280 px and 390 px, no horizontal scroll, no page errors. Port is not 7860.

## 13. Tests

Every pin in item 0. No golden, MD5, `T60_TOL`, or `small_lock08` move is allowed. A move with everything off is STOP 1. Acceptance keeps `-p no:stepwise` because pytest 9 owns `--sw`.

## 14. Locked decisions

No conflict that stops the run.

- D-BLOOM's both-ends sentence is narrowed by Hard rule 1. Reported in item 3. Not a STOP.
- Makeup freeze, 1/r, SRCDIST, D-PROX, Smooth, the 0.55 fold, Surfaces, PLACE, `g_decay`, and the tank are not edited.
- Off-axis tail colour stays unbuilt. Pre colour is on the FDN return, before the limiter, which is before that later colour. **Known, for Idle to confirm, not a stop.**
- Backlog Q4 full Colour module is not this run (Hard rule 10).

R3 open items stay open. Step 1 does not decide them.

1. Pre Drive hard-clips from about +4 up. The round 2 map is kept.
2. Colour harmonics 50-70 dB down may be inaudible on the tail. No extra drive is added.
3. Room Crush release is about 25 ms. The listens are there so Idle can hear the pump.
4. Natural and Glue stay on the current dynamics.
5. Swell IMD is about half the UAD at the top step. Not retuned.

## JSON rounding

No JSON value disagreed with the R3 text by more than the printed rounding. Step 1 packs the JSON doubles, not the rounded text. Label on every fitted number: `UAD-round3-fit`, with the file and the key.
