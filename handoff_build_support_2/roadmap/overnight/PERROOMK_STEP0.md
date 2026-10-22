# PERROOMK Step 0 (overnight, 2026-10-20)

Read-only review of `thursday_prompts\PERROOMK_RUN_2026-10-19.md` against the F13 SECOND PACK pin. Scratch probe: `%TEMP%\perroomk_step0\step0.json` (119 s, exit 0) plus `%TEMP%\perroomk_hall_bin.py` for the three exact hall acceptance bodies. No product file was edited during the probe.

This note is written after Step 1 had already landed `surf_loop.py` and `app_server.py`. The boot k floats and the six live MD5s were re-checked on that tree (`%TEMP%\perroomk_proof_fast.py`, exit 0) and still match. The accepted factual block is already on the prompt. It is not repeated here as a new decision.

No Step 0 STOP. Worst per-bank loop gain is −0.00034 dB (under 0). Boot k is bit-equal. No worklet or C change.

## 0. Live pins vs the F13 pin

VERIFIED at Phase 0, before the Step 1 edit. `live_stereo.c`, wasm, the Temp DLL, `fdn_worklet.js`, `live_fdn.js`, `pack_room.js`, `app.js`, and `index.html` were not edited in Step 1.

- WORKLET_VER 59. `index.html`: `pack_room.js?v=52`, `live_fdn.js?v=59`, `app.js?v=62`, `sl_room_result.js?v=3`.
- wasm sha1 `843a6eb8c91a9278ba927f643481f3260766a08c` (279668 bytes).
- `live_stereo.c` sha1 `bbdf57994e0996e2c9b77eb8a634550bb71ef3cf` (136434 bytes).
- Temp DLL sha1 `dcde61dfa8ccc17244595244bd3cb7077c7f8433` (285184 bytes).
- GOLDEN_META sha1 `a362cf5e490089807b39346ba207633b88511548`.
- Play goldens: `play_std_lock18_byp` `d011bafca80f4e46ae768db40becd762e78dcada`, `play_std_lock18_col` `d9470bfad67211180fedc1a07cd2352eaf4b14c7`, `play_std_unlocked_byp` `91738c70220b4edce512aebe3548dfdbd894cc41`, `play_std_unlocked_col` `a0ae72d9fb690cb7b3bbd54632abc466cefa0d24`.
- Render golden `render_std_unlocked_byp` `2a806e334e06cc475868d4c3da3fc78431c9a0aa`.
- Empty MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88`. Centre `b3e6bcd9dfa13ad737d2b15d561f7d30`. Explicit-false empty `ce009a4ccc3d85f87aa6547f59eda0e4`. Explicit-false centre `35972c29a63dbe5b33d228b68e6e575b`.
- Two-source `std_lock18` key-absent `a5dcacc67a269c234c4b5745899b038e`. Explicit false `0e94bd03d899b76b43adf31ae87f0cd2`.
- Harness `lib\wasm_run.js` sha1 `c505825f5dbbd5ec74780696ecbfd7217ebacf59`.

VERIFIED after the DSP edit: the six MD5s above still match (`perroomk_proof_fast.py`).

## 1. Callers, and the cards Render and Play pass

VERIFIED on the pre-edit map (accepted block) and re-read after the edit.

Pre-edit, `k_for_dial` lived at `surf_loop.py:304` and `phys_ceiling_row` called it. No other Python file called `k_for_dial(`. After the edit the live path is `_k_cached` → `k_for_room`. `k_for_dial` is the boot wrapper at `surf_loop.py:385`. Still no other caller.

- `phys_ceiling_row` `surf_loop.py:397` (after the edit). `phys_teff_bands` calls it. `phys_ceiling_pack` calls it at `surf_loop.py:441`.
- Render packs: `render_pipeline.py:2493` (surfaces on) and `:2505` (lock armed, surfaces off). Both pass `cards = cards_with_treatment(surfaces, surf_treatment)`.
- Play: `_ceiling_spec` at `render_pipeline.py:2701` builds the same `cards_with_treatment(surfaces, surf_treatment)` and calls `phys_ceiling_pack` at line 2710.
- Preview: `app_server.py` `api_phys_preview` calls `phys_ceiling_row`.
- Test-only: `software\tests\test_s5_surf_tail.py:539` calls `phys_ceiling_row` on the carpet scene.

VERIFIED: Render and Play pass the same card builder, so they get the same k for the same room.

## 2. Boot k and the scratch per-room table

Today's boot k, full repr, bit-equal to `k_for_dial` and to `k_for_room(6, 3, 8, boot cards, dial)` after the edit. VERIFIED.

| dial | k |
| --- | --- |
| 1.8 | `0.7757907003265825` |
| 4 | `0.333072595001391` |
| 8 | `0.15200528288314788` |

Scratch solve (70 steps, `lo, hi = 1e-5, 4.0`, return `hi`, humidity 0.35). Bands are 63, 125, 250, 500, 1k, 2k, 4k Hz. `small_page_engine` is `(W, H, L) = (4.5, 2.8, 6)`. `small_as_written` `(4.5, 6, 2.8)` produced the same k and the same T (VERIFIED). The new test uses `(4.5, 2.8, 6)`.

Boot, all three dials reachable, mid on the dial:

- 1.8: k `0.7757907003265825`, T `2.142433, 2.340002, 2.299671, 2.010194, 1.589806, 1.111344, 0.79752`
- 4: k `0.333072595001391`, mid 4
- 8: k `0.15200528288314788`, mid 8

Small engine `(4.5, 2.8, 6)`, all reachable, mid on the dial:

- 1.8: k `0.6499310388374295`, T `2.005248, 2.215824, 2.234048, 2.010194, 1.589806, 1.111344, 0.79752`
- 4: k `0.2790368814506333`
- 8: k `0.12734485135157309`, T `3.445836, 4.118392, 5.589732, 9.08925, 6.91075, 4.508894, 2.616859`

Hall 57 × 34.2 × 97:

- 1.8: k `4.0`, mid `3.6722894977531766`, relative error about 1.04, `at_bound` true, reachable false. T `6.344799, 6.424299, 5.442685, 4.122691, 3.221888, 2.20396, 1.469826`. This is the clamp. The dial cannot be 1.8 s in this hall. ALPHA_MAX stays 0.99.
- 0.3: same clamp, reachable false.
- 4: k `3.6461689105649904`, mid 4.0, reachable true. T `6.893602, 6.987551, 5.928526, 4.4947, 3.5053, 2.388937, 1.574352`
- 8: k `1.6640124255430147`, mid 8.0, reachable true. T `13.374002, 13.7322, 11.858475, 9.08925, 6.91075, 4.508894, 2.616859`

Cube side 340/60 m, all reachable, mid on the dial:

- 1.8: k `0.9158640212188819`
- 4: k `0.3932107024321975`
- 8: k `0.17945068118149424`, T `4.850982, 5.779018, 7.453022, 9.08925, 6.91075, 4.508894, 2.616859`

Closet:

- 1.8: k `0.32324612513607615`, reachable true
- 4: k `0.13878024791724597`, reachable true
- 8: k `1e-5`, mid `4.823141927886527`, rel 0.397, reachable false
- 0.3: k `2.00032037167365`, mid 0.3, reachable true

Mid-size 12 × 5 × 18, all reachable, mid on the dial:

- 1.8: k `1.4307615374875489`
- 4: k `0.6142732284861716`
- 8: k `0.28033761187465794`

Boot reachable span from the scratch (dial, reached mid, k): 0.5, 0.8, 1.0, 1.8, 4, 8 all on the dial. Unreachable: 0.2 and 0.3 pin k=4, mid 0.3596 s; 12, 20, 30 pin k=1e-5, mid 10.1548 s.

`small_lock08` is 4 × 2.5 × 5. At dial 8 the scratch pinned k=1e-5 with mid 7.9055 (rel 0.0118, under 0.08) but `at_bound` true, so reachable is false. The harness scene uses dial 0.8. A nearby small room at 0.8 was reachable. Dial 0.8 on this exact room was not in the table. LIKELY reachable. If the T60 test fails, that is a later STOP. Do not widen T60_TOL.

## 3. What stays and what moves

VERIFIED. `std_lock18` in `run_all.py` is decay lock 1.8, humidity 0.5, early wet 1. Width, height, and length stay the server defaults 6 × 3 × 8. Cards stay `default_surfaces()` with no treatment. The k solve uses humidity 0.35. It is the boot room. Its two-source key-absent MD5 stays `a5dcacc67a269c234c4b5745899b038e`. Explicit false stays `0e94bd03d899b76b43adf31ae87f0cd2`. Both were re-checked after the edit.

Stay (boot room, default cards, physics on or the off path): the four play goldens, the render golden, empty and centre MD5s, explicit-false empty and centre, d18/d4 prefixes (boot body, centre mic, smooth false, BYPASS), GOLDEN_META, T14 pin −26.71 dB (boot scene; tolerance stays ±0.5 dB). The live max-abs proof is the Step 1 gate, not this review.

Move (physics on, not boot default cards): hall scenes, the cube, the 4.5 × 2.8 × 6 room, `small_lock08` when physics is on, the 0.71 mirror hall, preview k for non-boot bodies, and any boot room whose cards or treatment are not the default. Carpet (`test_s5`) is the known suite case with non-default cards and physics on. A scratch treated card moved boot k at dial 1.8 from 0.77579 to `0.5650869462707905` and at dial 8 to `0.09478934609372588`, with mid still on the dial. LIKELY the carpet ratio gate (measured T30 ratio ≤ 1.03) still passes. Not a design STOP.

## 4. Loop gain

VERIFIED on the scratch solve, same 70-step return-`hi` arithmetic as `_k_solve`. Worst `max_loop_db` is **−0.00034 dB** on the exact `hall_binaural_decay8` body (57 × 34.2 × 97, sx_b 33, sz_b 60, decay 8, two sources, mirror B, binaural, tail only). Both banks −0.00034. `surf_on` 1, not refused, 1440 biquads. Under 0 dB, so it is not a Step 0 STOP. The margin is tiny.

Exact hall bodies: `hall_2src_decay8` −0.38897 (ORTF). `hall_binaural_decay4` −0.00068. Cube decay 8 two-source −0.05053 / −0.05056 (was the tight cube; it gained margin). Place 2 × 2.2 × 2.5 dial 8 two-source −0.0085. Closet dial 8 −0.01541. Boot two-source dial 1.8 −0.12802 both banks.

The full table is in `step0.json` key `loop`. A re-check through the shipped `_k_cached` is part of Step 1 before the hall slope tests are called safe. If any suite scene reaches 0 dB, that is STOP rule 3.

## 5. Solve time

VERIFIED. Hall dial 8 first solve 24.94 ms. Five misses 24.96, 24.94, 25.14, 25.18, 25.03 ms. Under the 50 ms line, so the bracket stays `1e-5` to `4.0`. The shipped path solves once per cache miss (`_k_cached`). An earlier draft of `phys_ceiling_row` solved twice; that draft is not in the tree.

## 6. Slope bounds and the line-0 comb

Slope bounds are from the designed per-band T, not from a 20 s IR. LIKELY the three hall params sit inside the band. The acceptance IR is the proof.

- `hall_2src_decay8` and `hall_binaural_decay8`: T_max 13.7322 s (125 Hz), T_min 2.616859 s (4 kHz). Lower slope `0.5*60/T_max` = 2.185 dB/s. Upper `2*60/T_min` = 45.86 dB/s. Longest-band slope 4.369 dB/s, inside.
- `hall_binaural_decay4`: T_max 6.987551, T_min 1.574352. Lower 4.293 dB/s, upper 76.22 dB/s. Longest-band slope 8.587 dB/s, inside.

Line-0 comb: the scratch probe did not re-render the IR. The stored PHYSDEFAULT / F14 number is 0.2126 against the old 0.20 limit. LIKELY unchanged, because this scene is the boot room and boot k is bit-equal. Step 1 re-measures it before the test edit. Above 0.23 is STOP rule 5. The explicit-false row stays at 0.20.

## 7. Audio thread and versions

VERIFIED. No C, wasm, worklet, or `app.js` change is required. The coefficient count does not change. WORKLET_VER stays 59. `app.js?v=` stays 62. BLOOM keeps 60 and `app.js?v=63`. `BLOOM_RUN_2026-10-19.md` is not edited by this run.

## 8. Sound and locked decisions

No locked value is moved. `BASS_S` stays 0.106194. `ALPHA_MIN` / `ALPHA_MAX` stay 0.01 / 0.99. `room_target`, makeup, `g_decay`, `line_t60`, decay lock, and T60_TOL 0.08 stay. The only intended sound change is k in rooms that are not the boot room with default cards.

Hall dial 1.8 cannot hit 1.8 s. The designed mid is 3.672 s at k=4. STOP rule 4 still says a measured T30 more than 15% off the dial at 1.8 is a stop. The prompt also requires the clamp and names dial 8 as the gate that must pass ("Mid must be within 15% of 8 s"). Rewriting STOP 4 was not self-accepted. Step 1 measures dials 1.8, 4, and 8. A measured dial-1.8 mid near 3.67 s is the required clamp. A measured mid far from 3.67 s is a real STOP. Dial 4 and dial 8 must hit 15%.

Open questions stay open. Cards are the room's actual cards (decision default). The page does not grow a "max reachable" line.

## Self-accepted (already on the prompt)

Three factual items, no sound, no tolerance, no golden move: the pre-edit line numbers still matched; axis order `(4.5, 2.8, 6)` is the engine tuple and the swapped tuple is the same k; `std_lock18` is the boot room so its two-source MD5 is not a mover.
