# Mirror physics — build diagnosis

Date: 2026-10-19. STOP stands. Read-only. No edits to software, the harness, or tests. PHYSDEFAULT has not landed. HANDOVER, BUILD_RUN_LOG, and OPEN_FAULTS were not rewritten.

Scratch scripts lived in `%TEMP%`. The tree was not monkeypatched. Claims are tagged VERIFIED, LIKELY, ASSUMED, PROPOSAL, or UNKNOWN.

## Verdict

The four new audio failures are Play only. With `phys_ceiling` absent, Play builds one physics section pack from source A's taps and runs that same pack on both tanks. Source B's line delays are different, and the sections depend on those delays, so the mirror breaks. Passing `phys_ceiling: false` into `play_ir` (no tree edit) makes all four pass.

Render designs each tank from that tank's own delays. A real two-source `render()` with physics on passes the mirror tolerances. Single-source Play and single-source Render pass with physics on.

`test_p6_two_source_cpu`'s silence-late median of 2.663 ms does not reproduce on an idle machine. The same bench, idle, is 1.617 ms. A 20-core burn lifts play and silence together. That row is a hitch during the long acceptance run, not a denormal in the physics filter, and not a reason to raise the ceiling.

## Explicit `phys_ceiling: false`

Same bodies and tolerances as the tests. Key absent is the product default (physics on). Explicit false omits the pack. Play, via `play_ir(..., extra={"phys_ceiling": false})`.

| Case | Key absent | Explicit false | Gate |
| --- | --- | --- | --- |
| `test_mirror_play_two_sources_hard` FDN BYPASS | null 1.166 dB, band 10.86, ILD 3.00, ic 0.176, early 0, T30 289.7% | null −2961.3 dB, other metrics 0 | fail → pass |
| same, FDN MEASURED_SHELF | null 0.685 dB, band 11.57, ILD 6.35, ic 0.212, early 0, T30 207% | null −2960.6 dB, other metrics 0 | fail → pass |
| `test_mirror_play_two_sources_centre_is_self_mirror` | null −31.46 dB, band 0.172, ILD 0.344, ic 0, early 0.0018, T30 373% | null −2999.1 dB, other metrics 0 | fail → pass |
| `test_sh_p7_mirror` | swap null −47.9 dB, max abs 1.656e-4 | swap null −600 dB, max abs 0 | fail → pass |
| Play one source, oneA vs oneB, FDN BYPASS | null −2973.0 dB | null −2967.3 dB | pass both |

VERIFIED. These match the acceptance numbers on the failing side. Log `%TEMP%\mirror_phys_diag\report.json`.

Centre's early figure is already inside 0.1 dB with physics on. The centre failure is the FDN lane (null, band, ILD, T30). Early and direct lanes of `test_mirror_play_two_sources_hard` were absent from the acceptance fail list. Those lanes do not run `surf_batch`.

## Mechanism

VERIFIED in code and in the packed delays.

Play, key absent:

1. `app_server.py:641` — a missing `phys_ceiling` becomes true.
2. `render_pipeline.py:3180` — `surf_pack = _live_surf_pack(..., taps, ...)`. The call passes source A's taps. `taps_b` is not an argument.
3. `render_pipeline.py:2699-2703` — lock armed, N = 32, `phys_ceiling` true: `_ceiling_spec` then `_sos_from_spec`. The live dict does not grow a `phys_ceiling` key. Measured on the hall pack: `surf_on` 1, `surf_sos` length 1440, `has_phys_key` false, `line_t60` 0.71.
4. `render_pipeline.py:2679-2684` — flat physics calls `phys_ceiling_pack` with `directional=False`.
5. `surf_loop.py:129-130` — non-directional `line_rates` tiles one room loss curve onto every line. This is not a per-face hit mismatch.
6. `surf_loop.py:155-163` — `design_bus` still builds each section from that line's delay (`tau = delay / sr`) and from `lg`. Same room curve, different delay, different coefficients.
7. `render_pipeline.py:2636-2656` — `_sos_from_spec` does that design once per bus (`l`, `c`, `r`) from the taps it was given.
8. `live_fdn.js:395-396` and `fdn_worklet.js:148-154` — one `Float64Array` of 1440 coefficients is copied.
9. `live_stereo.c:211-212` — `slC[3][SL_SEC][5][N]` has no bank dimension. `slZ[3][2][SL_SEC][2][N]` does: state is per tank, coefficients are not.
10. `live_stereo.c:1036-1037` — `live_load_surf` writes `slC[b][k][j][i]` from that one buffer.
11. `live_stereo.c:2235-2249` — `surf_batch` applies `slC[b]` to `slZ[b][bankB]`. The bank index selects state only.
12. `live_stereo.c:2690-2692` — tank A reads `line->delay`, then `surf_batch(..., 0, ...)`.
13. `live_stereo.c:2752-2754` — tank B reads `line->delayB`, then `surf_batch(..., 1, ...)` with the same `slC`.
14. Shared tail only replaces the inject (`shInjS` / `shInjSB` at `live_stereo.c:2695-2696` and `2757-2758`). Both tanks still run `delay` versus `delayB` through one coefficient set.

There is one pack, fitted to A. Tank B receives that pack. It does not receive a second pack fitted to B.

### Delays and coefficients

Hall two-source body, physics pack on. VERIFIED.

- A's L delays equal A's R delays (max abs 0 ms). A's L coefficients equal A's R coefficients (max abs 0). A bus swap of the pack changes nothing on this hall.
- B's L differs from A's L on 20 of 32 lines, max 90.0417 ms. B's delay multiset is a permutation of A's (30 unique values each). The shipped coefficients stay indexed to A's line `i`. They do not follow that permutation.
- A's centre delays differ from B's centre delays.
- A pack designed as a one-source scene at B's position (`sx = W − sx`) differs from the two-source pack on every bus, max abs coefficient 6.29344. B's correct sections are a fresh `design_bus` on B's taps. They are not a swap of A's buses.

`test_sh_p7_mirror` body (boot room, `shared_tail` true, balance −1 vs +1, Flat, lock 1.8 s). VERIFIED.

- `surf_on` 1. A's L delays differ from A's R delays.
- 31 of 32 L lines differ between A and B, max 2.0833 ms.
- B's delay multiset is not a permutation of A's. No reindexing of A's sections can supply B's sections.
- Peaks inside the designer follow the line index modulo 3 (`render_pipeline.py:2627-2632`). A delay-only permutation would still miss the axis peak when the index changes. Render avoids that by designing on the tank's own delays.

### Render

VERIFIED in code. Measured on a direct `render()` call, 1000 ms request, FDN only, colour BYPASS, 1-sample impulse on both dry channels, `two_sources=True`, `dry_l` and `dry_r` set. The harness helper was not used for this pair.

- `render_pipeline.py:2460` — `render()` pops `phys_ceiling` defaulting to false for a direct caller that omits the key. This probe passed the key through from `params_from_body`, so absent in the scene body arrived as true.
- `render_pipeline.py:2504-2515` — one room spec is stored in `_SURF_CTX`.
- `render_pipeline.py:1145` and `1179` — `render_fdn_ir` discards the `delays` argument and rebuilds line lengths from the taps of that call.
- `render_pipeline.py:1996-1997` — tank A and tank B each call `render_fdn_ir` on their own taps.
- `render_pipeline.py:1074-1089` — `_surf_bus` attaches that tank's hits to the shared spec.
- `fdn.py:1011-1013` — `_init_surf` calls `rates_for(self.delays)` and `design_bus(self.delays, ...)`.

Flat physics rates ignore the hits and tile one curve (`surf_loop.py:397-398`). The sections still follow that tank's delays. Each tank therefore gets its own fit.

| Render, two-source hall, FDN BYPASS | null | band, ILD, ic, early, T30 | phys in `info` | length |
| --- | --- | --- | --- | --- |
| Key absent | −215.11 dB | all 0 | true | 55441 samples |
| Explicit false | −235.17 dB | all 0 | false | 55441 samples |

Both pass the test tolerances (null ≤ −60 dB, band and ILD ≤ 0.1 dB, ic ≤ 0.01, early ≤ 0.1 dB, T30 within 2%). Log `%TEMP%\mirror_phys_diag4.log`.

`handoff_build_support_2\3_phase_acceptance_tests\harness\lib\render_ir.py:44` hardcodes `two_sources=False` and `dry_l=dry_r=None`, and lines 91-92 forward `phys_ceiling` only when the key is truthy. A two-source body sent through `ctx.render_ir` never enters the two-source branch (`render_pipeline.py:1863-1869` requires `two_sources` and both dry channels). An earlier scratch reported two-source Render nulls near −0.76 dB (physics on) and −0.80 dB (explicit false). Those figures are invalid. The single-source `ctx.render_ir` result is valid: oneA vs oneB, physics on, FDN BYPASS, null −186.8 dB, other metrics 0. Pass.

## Who it affects

- Play: the four audio tests fail with the key absent and pass with explicit false. VERIFIED.
- Render: two-source physics on passes. VERIFIED by the in-process render above. The slow acceptance mirror tests are Play. `render_ir.py` cannot see a two-source Render.
- Single source: unaffected. Each scene packs from its own taps. Play null −2973 dB. Render null −186.8 dB. VERIFIED.
- Surfaces two-source Play uses the same `_live_surf_pack(..., taps)` call. The shared-coefficient bug is in that call for every pack, physics or Surfaces. These five acceptance rows are Flat (`decay_lock`, no `decay_mode`). A numeric Surfaces mirror null was not measured this session. UNKNOWN as a number. VERIFIED as the same designer call.
- Early and direct: they stay off `surf_batch`. The hard-test failure list was FDN only.

## `test_p6` CPU

The gate is `run_all.py:434-435` inside `t19_two_source_radiation_cpu`, surfaces shared-off: silence-late median within 1.3× the play median and within 0.90 × `BUDGET_MS` (2.40 ms). `wasm_run.js:95-108` defines silence-late as the median of the second half of the silence blocks. The bench is `bench 4 10` (4 s of noise, 10 s total). `t19` does not post `phys_ceiling`, so the default pack is on. Surfaces mode posts `decay_mode: surfaces`, so this row has sections either way.

`surf_batch` (`live_stereo.c:2242-2246`) does not call `ls_flush`. `surf_step` does (`live_stereo.c:561-574`). That is the input cascade, not the per-line physics state.

| Run | Play median | Silence-late median | Ratio | Limit 2.40 and 1.3× |
| --- | --- | --- | --- | --- |
| Acceptance, surfaces shared-off, inside the long suite | 1.611 ms | 2.663 ms (mean 2.418, spikes 0) | 1.65 | fail |
| This session, full `t19`, machine idle | surfaces shared-off 1.599 ms | 1.617 ms (mean 1.767, spikes 1) | 1.01 | pass |
| Idle, shared off (no Surfaces) | 1.608 | 1.650 | 1.03 | pass |
| Idle, shared on | 1.785 | 1.792 | 1.00 | pass (ceiling 2.133) |
| Idle, surfaces shared on | 1.745 | 1.770 | 1.01 | pass (ceiling 2.133) |
| This session, surfaces shared-off, 20 cores spinning | 2.834 | 2.842 | 1.00 | fail the 2.40 ceiling on both medians |

VERIFIED this session. Log `%TEMP%\mirror_phys_cpu.log`.

The acceptance shape is play at the idle cost (1.611 vs 1.599) and silence-late alone at 2.663. An idle repeat of the whole of `t19` passes. A saturated machine lifts play and silence together (2.834 and 2.842) and the 1.3× rule holds. A denormal grow in `surf_batch` would show up on the idle repeat as silence above play. It does not. LIKELY a scheduling hitch in the silence half of that one bench during the acceptance suite. The 2.663 ms figure is not a standing cost of the physics pack.

Do not add a flush to fix the mirror. Do not raise 2.40 ms. A flush is a C and wasm change and can move tails once state is tiny, so single-source goldens would need a re-pin.

## Ranked fixes

PROPOSAL. None of these were applied.

### 1. Design a second pack from `taps_b` (product fix)

Give tank B coefficients from `_sos_from_spec` / `design_bus` on `taps_b`, and give `slC` a bank index (or a second buffer) so `surf_batch` for bank 1 reads them. Single-source keeps today's 1440-value blob and bank 0.

| | |
| --- | --- |
| Files | `software/render_pipeline.py` (`_live_surf_pack` and the call at 3180, pack fields), `software/engine/live_stereo.c` (`slC` at 211, `live_load_surf` 1027-1044, `surf_batch` 2235-2249, bank-1 call 2754), `software/static/js/fdn_worklet.js` (1440-length copy at 148-156), `software/static/js/live_fdn.js` (395-396 and `WORKLET_VER` at line 20). Rebuild `live_stereo.wasm`. |
| DSP or wasm | Both. Python designs the second pack. The wasm loop has to read bank-1 coefficients. |
| Pins that move | `live_stereo.c` sha1, wasm sha1, `render_pipeline.py` sha1. `fdn_worklet.js` sha1 and `WORKLET_VER` 58 move when the message gains the second pack. Tests that pin `WORKLET_VER = 58`: `test_quick_pins.py`, `test_mic_colour_relative.py`, `test_live_stereo.py`. |
| CPU | No added biquad per sample. Bank B already runs `SL_SEC` sections. Param-time design runs twice on two-source scenes. One extra 1440-double buffer (11.25 KiB) plus the bank dimension on `slC`. Idle surfaces silence-late stays about 1.62 ms. This does not explain or remove the 2.663 ms hitch. |
| Single-source default goldens | Bit-exact when the one-source `surf_sos` values and the bank-0 sample path are unchanged. Lock18 play, empty, centre, and the unlocked goldens are single-source. Two-source Play audio changes. That is the fix. The wasm sha pin moves even though those audio files stay. |

A bus swap is the wrong patch on the hall: L and R coefficients already match. A line permutation is the wrong patch on `test_sh_p7_mirror`: B's delays are not a permutation of A's, and axis peaks follow the line index.

### 2. Omit the physics pack when `two_sources` is set

Python only, at `_live_surf_pack` or at line 3180. Flat two-source Play returns to the section-free loop and the four audio tests go green. Those Play rooms lose the physical ceiling. Render still designs per tank, so Play and Render would disagree on two-source Flat physics. Surfaces two-source Play would still share A's pack.

| | |
| --- | --- |
| Files | `software/render_pipeline.py` only. |
| DSP or wasm | Python DSP. Wasm unchanged. |
| Pins | No C, wasm, or worklet pin. `render_pipeline.py` sha1 moves. |
| CPU | Flat two-source Play drops the section cost. The `t19` Surfaces row still runs sections. The 2.663 ms row is untouched. |
| Single-source default goldens | Bit-exact. The omit is two-source only. |

### 3. Pin the four audio tests to explicit `phys_ceiling: false`

| | |
| --- | --- |
| Files | `test_mirror_symmetry.py` (three Play tests), `test_shared_tail.py` (`test_sh_p7_mirror`). Leave `test_p6_two_source_cpu` alone. Explicit false does not change a load hitch, and idle `t19` already passes. |
| DSP or wasm | Neither. |
| Pins | None. |
| CPU | Unchanged. |
| Single-source default goldens | Bit-exact. The product Play bug remains, and these tests would stop watching two-source physics. |

### Rejected

- Denormal flush inside `surf_batch`. Idle ratio is 1.01. A flush is C and wasm, and it can move single-source tails, so the default goldens would not stay bit-exact.
- Raising the 2.40 ms silence ceiling. Idle surfaces silence-late is 1.617 ms.
- Reindexing or bus-swapping A's coefficients. Measured above.

## Suggested order

Land fix 1, then rerun the four Play tests with the key absent, plus one idle `t19`, before any HANDOVER rewrite. Rerun `test_p6` on a quiet machine. Expect it to pass near 1.6 ms. Keep 2.40 ms. Fix 2 and fix 3 are mitigations if the wasm change has to wait. They leave a two-source Play ceiling hole or a blind test.

Single-source default goldens are expected to stay bit-exact under fix 1. Confirm with the existing explicit rule: one-source lock18 play max-abs 0 against the PHYSDEFAULT pins (`GOLDEN_META` `a362cf5e490089807b39346ba207633b88511548`, lock18 byp `d011bafca80f4e46ae768db40becd762e78dcada`, col `d9470bfad67211180fedc1a07cd2352eaf4b14c7`). Wasm and C prefixes will move and must be re-recorded. Do not treat that audio match as a wasm-pin match.
