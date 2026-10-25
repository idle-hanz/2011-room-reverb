# SL6 Amount plan, 2026-10-25

Verdict: scale coverage. That is the same knob as interpolating alpha. A surf_cal crossfade is not. Apply the slider on release. Keep the proved `surf_cal` list at 100% only. The 16/23 gate stays the full plan.

No product file was edited. No impulse was rendered. The model calls are `auto_treat`, `room_target`, `anchored_target`, `phys_ceiling_row`, `alpha_fn`, and `design_bus` on the proved rows.

Scene: `real_default`, 6 × 3 × 8 m, humidity 0.35, plaster walls and ceiling, parquet floor. The eight rows are what `auto_treat(..., t_mid=0.8)` still returns. Porous 21% on F, D, A, C (`absorber_panel_4in_gap4in`). Membrane 62.5 Hz at 21.5% on F, membrane 125 Hz at 50% on D, Helmholtz 157.5 Hz at 47.4% on B, Helmholtz 198.4 Hz at 19% on D. Model 20/24, `t_fit` 0.8. That is the 16/23 plan. Shell rows are not in it.

`039ba09` is the guitar convolution of this pair (`surfaces_untreated.wav`, `surfaces_autotreat.wav`). A T20 of those files would be the performance. The lengths below are the lock-off model the render is designed to. The treated 500–2 kHz mean is 0.791 s, which is the 0.8 s end. The untreated mean is 2.633 s. Untreated octaves are 5.109, 4.981, 3.100, 2.654, 2.150, 1.672, 0.952 s from 125 Hz to 8 kHz. No octave is 4.4 s. The long end of that model is the 125 / 250 Hz pair, 5.11 s and 4.98 s.

## 1. Coverage is the alpha mix

`alpha_fn` is `(1 − sum coverage) · card + sum coverage · row alpha`, clipped at 1.0 on the sum and 0.99 on the result (`surf_panels.py`). On this plan the busiest face is D at 90%. Half of that is 45%. The 0.99 clip does not fire: peak alpha on the eight rows is 0.436. Scaling each row's coverage by Amount, and linearly blending the untreated alpha with the 100% alpha, differ by at most 3e-17 on 48 log-spaced frequencies from 50 Hz to 8 kHz. VERIFIED.

Area is that coverage times the shoebox face area. Scaling area and scaling coverage are the same fraction on this box. `auto_treat` does not read `room_shape`, so a polygon room still takes this shoebox fraction.

Lock-off model T, the path the 16/23 render uses (`anchor` None, then the material mid becomes the length). Mean of the thirds from 500 Hz to 2 kHz, then 125, 250, 500, 1k, 2k, 4k, 8k. VERIFIED.

| Amount | mid | 125 | 250 | 500 | 1k | 2k | 4k | 8k | inside the 0.8 s target |
|---|---|---|---|---|---|---|---|---|---|
| 0% | 2.633 | 5.109 | 4.981 | 3.100 | 2.654 | 2.150 | 1.672 | 0.952 | 0/23 |
| 25% | 1.632 | 2.381 | 2.323 | 1.797 | 1.645 | 1.444 | 1.205 | 0.778 | 0/23 |
| 50% | 1.197 | 1.599 | 1.538 | 1.284 | 1.205 | 1.096 | 0.949 | 0.661 | 0/23 |
| 75% | 0.951 | 1.212 | 1.157 | 1.005 | 0.955 | 0.887 | 0.786 | 0.576 | 6/23 |
| 100% | 0.791 | 0.980 | 0.930 | 0.829 | 0.794 | 0.748 | 0.673 | 0.512 | 20/23 |

The curve is monotonic and every mid sits between the ends. It is not a straight line in seconds. The arithmetic midpoint at 50% would be 1.712 s. The model is 1.197 s. A blend in 1/T, which is what linear absorption does, is 1.217 s. The first quarter of the area does the most: the mid falls 2.633 → 1.632 → 1.197 → 0.951 → 0.791. At 250 Hz the same steps are 4.981, 2.323, 1.538, 1.157, 0.930. A 50% setting is a sensible treated room on this curve. It is already near the short end, because that is what added area does.

A surf_cal crossfade, with the rows left at 100%, does not make that curve. The proved list is `[1, 1, 1, 0.850, 0.878, 0.870, 0.906]`. Blending it toward all-ones only moves the highs. 125 Hz stays 0.980 s and 250 Hz stays 0.930 s at every blend. The 500–1 kHz mean moves from 0.811 s at all-ones to 0.881 s at the proved list. The untreated room is not in that span.

The default desk does not play the table above. Decay lock defaults on, dial 1.8, `phys_ceiling` on. `phys_ceiling_row` re-solves k so the 500–1 kHz mean stays 1.800 s at every Amount (k 1.6379, 0.9545, 0.6818, 0.5319, 0.4365). 250 Hz moves only 2.560 → 1.831 s. 4 kHz moves 1.148 → 1.331 s, the longer way, because k falls to hold the mid. With the lock on and the ceiling off, `anchored_target` does the same pin: mid 1.800 s, and 8 kHz lengthens 0.595 → 1.136 s. The existing lock note already says the dial holds the length and the rows hold the shape.

Play does not design the lock-off length. `line_t60` is 0 when the lock is off, and `_live_surf_pack` then returns None (`render_pipeline.py`). Render does design it: a Surfaces render with the lock off sets the length to the material mid. That is why the listen can be the 0.8 s room while a Play slider on the default desk cannot sweep 2.6 s down to 0.8 s. Letting Play design that lock-off length is an edit in the live pack. It is a second law. It stays out of the run below.

## 2. Do not recalibrate, and do not interpolate the list

`surf_cal` is the residual of one rendered room: measured octave T20 over `target_T_oct`, then the room-average hold that pins 125, 250 and 500 Hz at 1. The proved list is that residual for the 100% plan. It is not a mix weight.

Putting a fraction of it on the scaled-row model moves 1 kHz at 50% from 1.205 s to 1.302 s. Coverage already moved that band from 2.654 s to 1.205 s. The factor is the small term, and it was measured where the porous coverage is 21%, not 10.5%.

`POST /api/surf_calibrate` is two impulse renders. That is the only way to know the residual at 25, 50 or 75%. It does not belong on a slider release. Below 100%, omit `surf_cal` on the post and leave the stored list alone, so returning to 100% posts it again without a render. The Calibrate button sets `surf_directional` true before it posts, so a click does not store this room-average list. Amount does not call that button.

The rendered impulse scatters around the formula. The SL6 review measured that scatter at up to about 25% on the factors-off full plan. A heard T20 at 50% can sit off the 1.197 s model by about that much and still lie between 2.633 s and 0.791 s. That scatter was not remeasured here.

## 3. Play cost: one post on release

`design_bus` on 32 delays spread from 9.6 ms to 57.5 ms, room-average rates, no `surf_cal`, loop gain set to that amount's own mid. Cold: 4.055 s at 0%, 1.962 s at 50%, 2.122 s at 100%. The same delays again: 0.020 s. The same rates with every delay one sample longer: 2.253 s. The cache key includes the delay (`_line_cache_key`), so a new amount misses, and a different delay set misses. Guard 0 on these fits. Worst line under 11%. That is fitter tracking on these delays, not a rendered score.

Play fits L, C and R (`_sos_from_spec`). Those three delay sets are not the same integers, so one new amount is three cold fits. Three times the one-bus time is about 12 s at 0% and about 6 s at 50% and 100%. That product was not timed as one call. Two sources fits a second tank. The 2.40 ms ceiling is the callback. The callback stays three biquads. This cost is the `POST /api/live_params` that builds them.

`scheduleLiveParams` waits 45 ms, then posts while Play is running. If a post is in flight, `pushLiveParams` arms another 45 ms wait. A drag would chain cold fits for as long as the pointer moves. The worklet keeps the previous coefficients until the response arrives. Post once, on pointer release. The Room result graph is `room_target` through `POST /api/room_result`. That call is the model. It can follow the slider while it moves.

## 4. The 16/23 gate is the 100% render

The gate is rendered third-octave T20 of the full plan, proved list, room average, lock off, ±10% of Mäkivirta, 23 bands from 49.6 Hz. That score is 16/23. It is already in the SL6 review. This note does not render it again.

Against that same 0.8 s target, the model is 0/23 at 0, 25 and 50%, 6/23 at 75%, and 20/23 at 100%. A mid Amount is outside that target because the room is no longer the 0.8 s design. It is not a failed gate. Scoring a partial amount against Mäkivirta at its own mid is a shape score, and that is 3/23, 5/23, 8/23, 15/23, 19/23. It stays a description, not a new gate.

## What the run changes

One goal. Step 0 stays off. The scale is the coverage mix that is already in `alpha_fn`. No edit in `live_stereo.c`, `render_pipeline.py`, `surf_loop.py`, or the bloom DSP. No new numeric gate.

Store Amount on the scene, 0–100, default 100. A missing value is 100, so a scene with no slider still posts today's rows. On the post copy only, multiply coverage of each accepted row by Amount/100. Skip `suggested` rows, and skip `type === "shell"`. Shell is the assumed 30% the Surfaces chip adds on enter. It is not one of the eight rows. Bare plaster at 125 Hz is 5.109 s. Shell alone brings that to 2.552 s and the mid from 2.633 s to 2.537 s. Plan plus shell is 0.781 s at the mid. Scaling the shell would make 0% and 100% something other than this plan. Deep-copy the rows. `heardMix` is a shallow copy, and the stored coverage has to stay at the accepted plan so the slider can return to it.

Do this in the copy that Play and Render already share (`heardMix`), and in the Room result post. At Amount 100, post the stored `surf_cal` unchanged. Below 100, omit the key on that post. Do not write the seven proved numbers into the client as a default for every room. Do not add an Amount field to the wasm pack.

Show the block that is already `#slAutoTreat`, plus the slider, by setting `RR_SL_STAGE` to 6. The file comment already calls 6 the proved Auto-treat stage. The HTML pin is 5, which hides the block. Bump `sl_room_result.js` and update the stage string in `test_sl5_wire.py`. The slider's `input` refreshes the graph. Pointer release is the only `scheduleLiveParams`. Flat still ignores rows. The Surfaces chip's `surf_directional` flag stays as it is.

QUICK after the edit. No impulse, no SURFACES tier, no FULL. Empty and centre MD5s stay on the default body, because Amount 100 with no rows posts the same scene.

Left out: Play designing a lock-off material length, the early-tap absorb rewrite Render already does and Play does not (`tap_reflect_gain` reads the card's `absorb` list), the Calibrate button forcing directional, `phys_ceiling` k, the Decay lock, shell coverage, polygon area, and any re-score of 16/23.
