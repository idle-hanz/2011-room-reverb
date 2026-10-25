# Mic routing plan, 2026-10-25

Read-only. No product code, goldens, wasm, or `WORKLET_VER` were edited. No impulse was rendered. The direct-path numbers below are `pattern_gain × 1/r ×` the speaker weight, on the page boot room, before the 0.55 direct fold.

Contract for every run below: `RUN_RULES.md` 17–22. One goal per run. One heard fault per run. These are wiring and copy. Leave `live_stereo.c`, `render_pipeline.py`, `surf_loop.py`, and the bloom DSP alone, so Step 0 stays off. Start from `CURRENT_BRIEF.md`. Leave `HANDOVER.md` unread. A run proves a new post with the node test. One `render()` call only when a weight changes and the node test cannot see it. Open the app only after that, and only if the fault is still there.

Pins, from `CURRENT_BRIEF.md` and `software\tests\test_quick_pins.py`: `WORKLET_VER` 63, `app.js?v=85`, empty MD5 `b20cf5dc675f613992aa6a31c2cd74f4`, centre MD5 `ba1bbc6d386ed75bf484156f08043f37`. Play ceiling 2.40 ms. Shared-on ceiling 2.133 ms. The five golden sha1s stay. None of these runs re-pin them.

Boot room used for the numbers: 6 × 3 × 8 m, source (2.6, 1.2, 4.75) m, stand (3.0, 1.5, 1.5) m. `c = 340`. Delay is `(d/340)×1000`. Fader travel 0.5 is 0 dB (`FADER_KNOTS` in `app.js`).

## 1. Two-mic presets still put a centre mic in the middle

VERIFIED. `loadDeskPreset` (`app.js` 424) sets `third_mic` to `"off"` only for `ortf`. Every other setup, including the pairs, sets `"centre"`. `heardMix` (`app.js` 599) then posts `mic_gain_c` at the fader. At the 0 dB fader that gain is 1, pan 0, so the fold is the 477 pair `cl = cr = 0.5`.

The pair rows in `MIC_PRESETS` (`app.js` 6–46) are `ab_omni`, `ab_card`, `xy_90`, `xy_120`, `nos`, `din`. Their `polar` lists are L and R. The centre capsule is still placed on the stand, yaw 0.

XY 90°, space 0.01 m, cardioids, C on. Direct path, linear amplitude into the speakers:

| Mic | Position (m) | Delay | Off-axis | Pattern | Left | Right |
|-----|----------------|-------|----------|---------|------|-------|
| L | (2.995, 1.5, 1.5) | 9.670 ms | 38.37° | 0.892 | 0.27132 | 0 |
| C | (3.000, 1.5, 1.5) | 9.671 ms | 8.75° | 0.994 | 0.15117 | 0.15117 |
| R | (3.005, 1.5, 1.5) | 9.673 ms | 52.29° | 0.806 | 0 | 0.24502 |
| Sum | | | | | 0.42249 (−7.48 dB) | 0.39619 (−8.04 dB) |

Taking C out of that sum leaves 0.27132 and 0.24502. The centre mic adds about 3.8 dB on the left and 4.2 dB on the right, at one delay (9.671 ms), into both speakers. L and R are 1 cm apart, so the three capsules are one point. AB is the same fold with an 0.80 m pair and the centre still on the stand between them.

ORTF already posts C off (`mic_gain_c` 0, weights `cl = cr = 0`). `ortf_c` is the preset that keeps C. Binaural zeros C by `mic_setup`. Mono centre and the MS menu items need C. Leave those.

D20 stays. `test_t4b_ortf_c_off_draft.py` (`test_xy_nos_ab_still_include_the_centre`) locks the server: a body that only names `xy_90`, `xy_120`, `nos`, `ab_omni`, `ab_card`, or `din`, and omits `third_mic` and `mic_gain_c`, still folds C at 0.5 / 0.5. The page is what posts the keys. Leave `params_from_body` (`app_server.py` 554–565) as it is.

The centre fader still prints 0.0 dB when `third_mic` is off. Only binaural rewrites that read to "off" (`app.js` 942–948). ORTF already has this gap.

PROPOSAL, this run: on those six pair ids, `loadDeskPreset` sets `third_mic` to `"off"` and the centre strip paints off, the way binaural already does. `ortf_c` keeps C. The Room chip stays for a mic the user places on purpose.

Substitute, if the third mic should stay audible: same six ids set `third_mic` to `"room"` and `place_c` to `"room"`, and the strip label becomes "Room". Do not call `snapRoomSpotToStand` for that load. That function copies the stand (`app.js` 556–566), which puts the room mic back in the centre. The unused spot already on state is (4, 1.5, 2) m, yaw 0, which is 1.12 m from the boot stand. That coordinate is a proposal, not a measured spot. This substitute replaces the mute run. It does not follow it.

Files: `software\static\js\app.js` (`MIC_PRESETS`, `loadDeskPreset`, the centre-strip paint), `software\static\index.html` (the Mic setup menu, 685–699). The substitute also touches the centre strip name (234) and `snapRoomSpotToStand`.

Risk: empty `{}` and `{third_mic: centre, mic_gain_c: 1}` do not load a pair preset, so both MD5s hold. The five golden sha1s hold. `WORKLET_VER` stays 63. Bump `app.js?v=` only. The bench body is not a clicked preset, so the 2.40 ms path is the same shape. QUICK after the edit. The D20 test above must stay green. FULL and the two `t19` lines once, at the end, expecting a flat delta.

## 2. A two-mic MS preset

The engine already has the send. `desk_matrix._pair` (`desk_matrix.py` 111–123):

| Route | Left speaker | Right speaker |
|-------|--------------|---------------|
| `pan` at −1 / 0 / +1 | g, g/2, or 0 | 0, g/2, or g |
| `centre` | g/2 | g/2 |
| `both` | g | g |
| `s` | g | −g |
| `l` / `r` | g or 0 | 0 or g |

`s` is the phase-invert parallel send: one capsule, full gain to the left speaker and the same gain with the sign flipped to the right. `phase` on the strip flips both signs. `both` is the mid to both speakers at full gain. `centre` is the 477 half-gain and is 6.02 dB quieter than `both` at the same g.

`pair_mode` `"ms"` parks the side capsule on the mid and aims it at the mid yaw plus 90° (`apply_desk_geometry`, `desk_matrix.py` 377–396). While it is parked, colour follows the mid axis. A desk that is active clears `ms_decode` (`app_server.py` 552–553), so the old decode must not also run.

`ms_b` already posts this desk (`ms_presets.js` 27–31 and 44–48). Unity trim −3 dB, `g = 10^(-3/20) = 0.707946`. Section 7 is sent. Weights:

`ll, lr, cl, cr, rl, rr = 0.707946, −0.707946, 0.707946, 0.707946, 0, 0`

L is fig-8, C is cardioid, R is a muted fig-8. On the boot room the parked side sits on C at (3, 1.5, 1.5), delay 9.671 ms, 96.99° off the fig-8 (pattern −0.122). R's gain is 0, so three capsules are built and two are heard. `loadDeskPreset` still sets `third_mic` to `"centre"` before copying that desk, and the desk does not clear it.

PROPOSAL: one new menu id, two heard mics. Mid on C, cardioid, yaw 0, route `both`, gain 0.707946. Side on L, fig-8, route `s`, same gain, `pair_mode` `"ms"`, `ms_s` `"l"`, `ms_m` `"c"`. R muted (`mic_gain_r` 0) and not shown as a live centre mic. Same six weights as `ms_b`. Leave `ms_a`, `ms_b`, `ms_c`, and `ms_classic` as they are. Leave the −3 dB trim as the preset's trim. A later button click does not invent a second trim.

Files: `software\static\js\ms_presets.js`, `software\static\js\app.js` (`MIC_PRESETS`, `loadDeskPreset`), `software\static\index.html` (one `<option>` on `#mic_setup`). Engine files are read, not edited.

Risk: a new id is absent from `{}` and from the centre body, so both MD5s hold. No section is added to the blob format. `WORKLET_VER` stays 63. Bump `ms_presets.js?v=` and `app.js?v=`. Play stays on the existing section 7 path. QUICK includes `tests\test_ms_presets.mjs`. FULL and two `t19` lines once, flat delta expected.

## 3. Stereo pair, M/S pair, and Independent

One cause. The click handler (`app.js` 1235–1243) writes `pair_mode` and, for M/S, sets the side yaw to the mid yaw plus 90° (`aimCoincidentS`, 1227–1234). It does not write routes, pans, gains, or mutes. `syncUI` does post the body (`scheduleLiveParams` at 3068). The key arrives. With every route still `pan` and the linear law, `matrix_needed` is false (`desk_matrix.py` 202–204) and section 7 is omitted. The six weights stay whatever the faders and pans already were.

There is no Stereo-mic button in `index.html`. `stereoMicBtn` is bound in `app.js` (1317) and nothing in the page calls it. `stereo_mic` stays false, so Left and Right are not ganged. Independent has nothing to ungang. The hint under the desk still says the gang exists (`index.html` 325).

Page boot, faders at 0 dB, routes `pan`, pans −1 / 0 / +1. VERIFIED by `fold_for` and `place_stand` on `params_from_body`.

XY 90°, C on, gain 1. Stereo and Independent:

- `desk_active` is false for stereo and true for independent (the flag only). `matrix_needed` is false either way. Section 7 is off.
- Weights both `[1, 0, 0.5, 0.5, 0, 1]`.
- Positions, yaws, delays, and the folded direct match. Left 0.42249 (−7.48 dB), right 0.39619 (−8.04 dB). Max abs difference 0.

XY, M/S button (side yaw written, routes still `pan`):

- Weights stay `[1, 0, 0.5, 0.5, 0, 1]`. Section 7 stays off.
- L is parked on C and aimed at +90°. Delay 9.670 ms → 9.671 ms (+0.001 ms). Pattern 0.892 → 0.439.
- Left sum 0.42249 → 0.28473, which is −3.43 dB. Right stays 0.39619 (−8.04 dB).
- That is a quieter left capsule, still hard-left. It is not an MS decode. An MS decode is the `ms_b` weights in section 2.

ORTF, C off. Stereo and Independent match: weights `[1, 0, 0, 0, 0, 1]`, left 0.25118 (−12.00 dB), right 0.21889 (−13.20 dB). `desk_active` is true on both because `third_mic` is `"off"` (`desk_matrix.py` 87–89), and the fold still matches. The M/S button keeps those weights, parks L on the stand (x 2.915 → 3.000, 8.5 cm), delay 9.644 → 9.671 ms (+0.027 ms), and the left sum falls to 0.13356 (−17.49 dB), −5.49 dB. Right stays −13.20 dB.

On `ms_b`, the routes are already `s` / `both` / `pan`. Clicking Stereo or Independent leaves the weights on the section 2 list and only un-parks L by 2.5 cm (x 3.000 → 2.975). Delay 9.671 → 9.663 ms (−0.008 ms). The folded direct moves about 0.07 dB on the left and 0.06 dB on the right.

The on-screen matrix uses the same route math (`deskWeights`). While the routes stay `pan`, that line does not change when the button changes. The floor plan does not park the side either: `viewMic` (`mic_desk.js` 951–955) draws the spaced stand. The polar caption is the line that says "coincident with M".

PROPOSAL, this run, one handler:

- Stereo pair sets `pair_mode` `"stereo"`, routes `pan`, pan L −1 and R +1, and gangs the L and R faders. That is the `stereo_mic` behaviour the missing button never wired.
- M/S pair sets `pair_mode` `"ms"`, the side strip to route `s`, the mid strip to route `both`, and mutes the spare strip. Gains stay the faders that are already there. The −3 dB trim belongs to the preset in section 2, not to this click. At 0 dB faders the weights are `[1, −1, 1, 1, 0, 0]` with R spared.
- Independent clears the gang and leaves each route where it is.

Files: `software\static\js\app.js` (the `[data-pair]` click, the gang), `software\static\index.html` (the three buttons, 202–206, and the hint on 325), `software\static\js\mic_desk.js` only so the parked side is the capsule the engine already moves. `desk_matrix.py` already does the fold. Leave it.

Risk: boot stays Stereo with the current pans, so `{}` and the centre body are unchanged and both MD5s hold. No new blob section. `WORKLET_VER` stays 63. Bump `app.js?v=`. The 2.40 ms bench does not click these buttons. QUICK, then FULL and two `t19` lines once.

## 4. Labels for Physical ceiling, Rumble filter, and Off-axis tail

The three checkboxes are `index.html` 312–323. They have no `title`. Proposed label, then the title.

Physical ceiling. Label: "Room limits the tail". Title: "Holds the tail to this room. Decay sets the length around 500 Hz to 1 kHz. The highs follow the walls. Nothing is held until Decay is armed."

VERIFIED behaviour to match that sentence. Default on. A missing key is on (`app_server.py` 662–663). The pack is omitted when the box is off or Decay is not armed (`render_pipeline.py` `_ceiling_spec`, 2928–2931). `k` is solved so the 500 Hz–1 kHz mean equals the Decay dial (`surf_loop.py` `phys_ceiling_row`). The live dict does not grow a `phys_ceiling` field. The pack shows up as `surf_on` and `surf_sos` (1440 floats at N 32) when the lock is armed. Two sources keep that pack (`test_physdefault_two_source.py`, `test_f13_phys_preview.py`). The readout sentence "off with two sources" (`app.js` 792) is stale. This run deletes that sentence. The ceiling stays on with two sources.

Rumble filter. Label: "15 Hz rumble cut". Title: "Cuts rumble below 15 Hz on the way into the tank. The direct sound and the early reflections are left as they are."

VERIFIED. Causal 2nd-order Butterworth at 15 Hz, Q `1/√2`, five DF1 floats (`early_field.py` `butterworth_highpass`, `render_pipeline.py` `sub_hp_coeffs`). Section 9. Default on. A missing key is on. Direct and early are never filtered (`live_stereo.c` 62–64).

Off-axis tail. Label: "Darken the tail". Title: "Darkens the reverb tail the way this mic sounds from the side. The direct sound and the early reflections stay as they are. Off until you tick it."

VERIFIED. Default off. Missing or false keeps the empty MD5 and omits section 14 (`test_offaxis_tail.py`). On packs 45 floats, three biquads per bus, layout LS+HS+HS, on the FDN sum after the desk and Bloom and before `fdn_wet` (`live_stereo.c` 74–76). The U87 Ai cardioid model sits between −8 dB and −4 dB at 1 kHz, and 16 kHz is at least 1 dB darker (`test_offaxis_tail.py` `test_u87_cardioid_shape`). The title stays in words. The checkbox id stays `offaxis_tail`.

Files: `software\static\index.html` (the three `<span>`s and a `title` on each label), `software\static\js\app.js` (the stale two-source sentence in `paintPhysReadout`).

Risk: copy only. Defaults stay. Both MD5s hold. The five sha1s hold. `WORKLET_VER` stays 63. No cache bump beyond `app.js` if that sentence moves. QUICK. FULL and two `t19` lines once, flat delta expected.

## 5. Remove Routing and the Host fader. One Bypass button.

VERIFIED, what is there now.

The Host strip (`index.html` 300–307) is the dry bus. Travel 0 is −∞, so boot `fader_dry` 0 posts `dry_gain` 0. Play adds `dry_gain` times the input onto the wet sum (`live_stereo.c` 4118–4120 and `mix_partition` 3905–3906). Render adds `dry_gain * dry_pad` to the wet (`fade_render_tail`, `render_pipeline.py` 380–389).

The Routing panel (`index.html` 326–417) is three strips, Array, Room, and Master, each with a preamp (None, Neve, 610-A), a drive, a compressor (Off, Natural, Glue, Room Crush, Nuke, Swell), and an amount. Boot is None / Off / 0, and `masterScene` / `renderScene` (`routing_scene.js`) post nothing in that state. Master, when on, posts the bloom keys Play already reads (sections 10 and 12). Array and room post only while that strip is on, and the note on the panel says those inserts are Render only (section 13, `live_stereo.c` 69–73). `CURRENT_BRIEF.md` already shelves this DSP: leave the code, default off.

The colour menu already has an option named Bypass (`index.html` 733, value `BYPASS`). That one is the mic pattern with the measured colour off. It stays.

PROPOSAL. Remove the Host strip and the Routing panel from the page. Add one Bypass button on the mix desk, default off.

Off: `dry_gain` stays 0. Direct, FDN, and Early post from their faders, as now. No new key.

On: the post copy sets `dry_gain` to 1 and `direct_wet`, `fdn_wet`, and `early_wet` to 0. The faders on screen stay put. Play's existing sum is then the input, because the wet terms are multiplied by those three gains and the dry term is `dry_gain` times the input. Render's existing tail fade does the same with `dry_gain`. The tank still runs. This button does not skip `process()`.

`heardMix` stops reading `fader_dry`. Solo no longer has a dry bus (`SOLO_BUSES` in `app.js`). A saved scene with the host fader up does not bring that fader back.

Leave the engine. Sections 10, 12, and 13 stay in `live_stereo.c`. `bloom_dsp.py` stays. `routing_scene.js` can stay loaded and unused. The page stops offering the controls, so boot keeps posting nothing for them.

Files: `software\static\index.html` (Host strip 300–307, Routing panel 326–417, the new button), `software\static\js\app.js` (`heardMix`, `SOLO_BUSES`, `bindRouting` / `paintRouting`). Leave `routing_scene.js` unless a dead call has to go.

Risk: bypass off matches today's boot post (`dry_gain` 0, bloom keys absent), so both MD5s hold and the five sha1s hold. No new blob field. `WORKLET_VER` stays 63. Bump `app.js?v=`. The 2.40 ms bench is bypass off and does not gain a stage. QUICK includes `tests\test_routing.mjs` if a routing helper is still imported. FULL and two `t19` lines once, flat delta expected.

## Run order

One goal each. Same two files show up more than once, so the runs stay in this order.

1. Pair buttons (section 3). The heard fault. The click has to change the fold or the gang.
2. Two-mic centre (section 1). Mute C on the six pair presets and paint the strip off. The room-mic spot replaces this run if that is the choice. It does not follow it.
3. Two-mic MS preset (section 2). New menu id. Same `s` / `both` desk as `ms_b`, spare strip muted.
4. The three labels (section 4). Copy only, including the stale two-source sentence.
5. Routing panel, Host fader, Bypass button (section 5).

Each run: QUICK from `software\` after the edit, then FULL and the two `t19` lines once at the end of that run. Known-red acceptance tests are not a stop. A fail names the gate, the margin, and one line on the cause.
