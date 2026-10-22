# Code structure review (read-only), 2026-10-21

Scope: `software\` excluding `.venv`, `vendor`, `__pycache__`. Nothing was edited, and no pytest was run. Line numbers are as of 2026-10-21 08:15 (UTC+1).
Cross-references: PROGRAM_REVIEW_2026-10-20.md (PR-B1..B4, PR-R1..R6) and AUDIO_QUALITY_AUDIT_2026-10-21.md (AQ-1..4). Findings already in those reports are only pointed to, not repeated.

## Verdict (plain)

It is not spaghetti. The DSP inner loops (C engine, fdn.py, surf_loop.py) are tidy and heavily commented, and the tests pin behaviour well. The tangle sits in three places:
1. Two giant Python functions that every feature gets bolted onto.
2. The parameter blob, whose layout is written out by hand three times (Python, JS and C).
3. A growing pile of "force off / parity / legacy" exceptions that each feature has to re-check.

All of it can be untangled without changing a single output sample.

## Size

100 source files and 44,758 lines. The biggest files are:

| File | Lines |
|---|---|
| static\js\app.js | 3724 |
| engine\live_stereo.c | 3696 |
| render_pipeline.py | 3434 |
| engine\early_field.py | 2628 |
| static\js\mic_desk.js | 1623 |
| engine\fdn.py | 1613 |
| app_server.py | 1516 |
| engine\bloom_dsp.py | 1087 (unused) |

The longest functions are:

| Function | Lines | Arguments |
|---|---|---|
| render_pipeline.py:1634 `_render_core` | 801 | **109** |
| render_pipeline.py:2759 `live_fdn_params` | 445 | 2 |
| polar_field.py:425 `compute_polar_field` | 380 | 43 |
| tweak_app.py:249 `build_ui` | 348 | 0 |
| engine\early_field.py:1845 `compute_taps` | 240 | 11 |
| app_server.py:484 `params_from_body` | 225 (97 `.get(` defaults) | 1 |
| live_stereo.c:3277 `mix_partition` | 182 | |
| app_server.py:1022 `_render_impl` | 181 | |
| live_stereo.c:3486 `run_partition` | 166 | |
| render_pipeline.py:1453 `combined_ir` | 150 | **51** |

## Problems

### S1. `_render_core` is an 801-line function with 109 arguments (render_pipeline.py:1634-2434)
It holds the still path, the moving path and the hop path, with 18 if/elif branches and 71 bare numeric literals. Every new feature (Movement, prox, makeup grid, surfaces) becomes another keyword argument plus a branch inside it. PR-B2 (capsule missing on the moving path) is a direct symptom.
**Refactor:** bundle the arguments into a frozen `RenderSpec` dataclass built once from the params. Split the function into `_plan()`, `_render_still()`, `_render_moving()` and `_render_hops()`. This is a pure move, so check that the goldens are byte-identical.

### S2. `combined_ir` (51 arguments) is called by hand in 4 production places and 6 test/demo places
The call sites are render_pipeline.py:2118, 2167 and 2340, app_server.py:1412, engine\selfcheck.py:770-773 and engine\moving_room_demo.py:208 and 306. app_server.py:1410-1411 also re-derives `early_ms = min(90, ...)` and `fdn_ms = max(early_ms, min(len, 1000))` inline instead of using `planned_fdn_ms` (render_pipeline.py:2113), so the colour preview can plan differently from Render.
**Refactor:** add `combined_ir_from_spec(spec, taps, prep, delays)` and make every call site use it. One place then owns the defaults, which fixes the class of bug behind PR-B2 for good.

### S3. The live parameter blob is written out by hand three times
- Python: render_pipeline.py:3290 onwards, the packer inside the `live_fdn_params` area (445 lines).
- JS: static\js\pack_room.js:40 onwards.
- C reader: live_stereo.c:1222 `load_core_body`, with 58 positional `rf(&r)` reads.

The order is only enforced by matching comments (live_stereo.c:25) and by tests. Defaults already drift between them: the snap default is PR-R4, and pack_room.js:53 writes the pan default as a nested ternary while Python writes it as a tuple. The C side also re-clamps values on its own (live_stereo.c:1238-1245, 1249-1251).
**Refactor:** write one `blob_schema.json` with name, default, clamp and type for each float. The Python packer, the JS packer and a generated C header of offsets would all read from it. Add a test that packs the same scene in Python and JS and compares bytes, then hard-errors on any default that differs. Bit-exact as long as the current defaults are copied in as they are. **Do this before BLOOM**, because BLOOM adds a whole new section to this blob.

### S4. Exception flags are re-checked everywhere ("rules upon rules")
- `reaktor_parity` appears 31 times in render_pipeline.py, 9 in app_server.py, 7 in early_field.py, 10 in app.js, 4 in room_editor.js, 2 in live_stereo.c, and more in fdn.py, mic_display.py, room_3d.js and room_math.js.
- app.js:170 adds a second, JS-only twin, `hallSnapshot`, and folds it in at app.js:656.
- `movement_peak_ms` (render_pipeline.py:815-835) re-lists the same "force to 0" cases as `smooth_active` (line 783): parity, flat cards, mirror/null and direct-only. Its docstring says as much.
- `MOVEMENT_FORCED_OFF = True` (line 812) sits on top of all of that.

**Refactor:** add a single `resolve_mode(p) -> Mode` with fields such as `parity`, `flat`, `movement_allowed` and `smooth_allowed`. Compute it once in `params_from_body` and pass it down. Each feature then asks the Mode object instead of re-deriving the rule. Turn `MOVEMENT_FORCED_OFF` into `Mode.movement_allowed = False` with the G2 reason attached. That is also the clean place to later allow Movement in Render only (backlog Character idea).

### S5. Dead and stale code
- **BLOOM leftovers.** `engine\bloom_dsp.py` (1087 lines) is imported only by `tests\test_bloom_off.py:14`. `engine\bloom_live.inc` (475 lines) is `#include`d nowhere: live_stereo.c's only includes are lines 589 and 592, both SIMD headers. These are exactly the files the BLOOM retry will rewrite.
- **16-bit WAV writers** in CLI/demo code: early_field.py:2445, fdn.py:1364 and moving_room_demo.py:112 (`setsampwidth(2)`). The shipped writer is 24-bit (render_pipeline.py:322). The precision side of this is covered in AQ-1, so this is only about tidiness.
- **Legacy paths kept for tests.** fdn.py:307 (the Hadamard-column inject) and render_pipeline.py:517 (integer-sample placement, "Prefer _apply_ir_at").
- **Deprecated no-op** at surface_colour.py:723.
- **Back-compat shims.** The `diffusion` to `jitter_D`/`structure_dif` mapping is done twice, at surface_colour.py:217-233 and colour_surfaces.js:108-110.
- **Back-compat toe-in CLI flags** marked "ASSUMED legacy" at early_field.py:2470/2558 and fdn.py:1487.
- **Listen-script global** `HARM_DB_OVERRIDE` at early_field.py:71 and 1452-1455. This is a module global that scripts mutate.

**Refactor:** let the BLOOM retry *replace* bloom_dsp.py and bloom_live.inc rather than adding next to them. Move the legacy test-only paths into `tests\_legacy_ref.py`. Make the CLI writers call the one 24-bit writer. Do the diffusion back-compat mapping in one place, on load (Python), and have JS trust the server. Turn `HARM_DB_OVERRIDE` into a function argument.

### S6. Parameter wiring is spread wide
`humidity` alone is touched in 20 files, including render_pipeline.py (32), early_field.py (42), selfcheck.py (27), app.js (16), air_iso.py, surf_target.py and surf_loop.py. `params_from_body` (app_server.py:484, 225 lines) has 97 separate `.get(...)` defaults, and those defaults are typed again in `_pb_num` calls (render_pipeline.py:3294-3302) and in pack_room.js.
**Refactor:** a `params_schema.py` table (key, type, default, range, UI-only?) that `params_from_body`, the blob schema from S3 and `test_s_audit_ui` (test_a12, 233 lines) all read. This has the same root as S3 and should be done together with it.

### S7. Magic numbers
There are 296 float literals in live_stereo.c against 14 `#define`s, about 71 in `_render_core` and 68 in `live_fdn_params`. Examples:
- `min(90.0, ...)` and `1000.0` (app_server.py:1410-1411)
- `0.03` default g, `1000` max delay, `31` direct-index clamp (render_pipeline.py:3292-3299 and pack_room.js:44-50)
- `256` minimum delay and `16.0` mic-gain clamp (live_stereo.c:1244, 1249)

**Refactor:** name them in the schema (S3/S6) or as module constants. There is zero sound risk if the values are copied exactly.

### S8. Duplicated DSP between Render (Python) and Play (C)
This is by design: Render is float64 and Play is C/wasm. The duplication itself is acceptable and protected by parity tests (test_s5_surf_tail.py:321 `assert_surf_parity`, test_mic_colour_relative.py:805). Two places where it already shows:
- Live-only fixes, e.g. the b2 DC restore at live_stereo.c:1258-1260 ("Render stays float64 and does not need this").
- Different delay sources (PR-R3).

**Refactor:** don't merge the two. Add a short "twin map" comment table (Python function to C function) and make every twin pair have a named parity test. This is documentation plus tests, with no code change.

### S9. Giant UI files
app.js (3724 lines) holds state, routing, the snapshot loader (applyReaktorSnapshot, app.js:229) and stand snapping. tweak_app.py:249 `build_ui` is 348 lines.
**Refactor:** split app.js into modules (state, scene I/O, transport, panels). There is no sound risk, but there is UI-test churn, so it is low priority.

### S10. Version pins spread across tests
`WORKLET_VER = 59` is asserted literally in three tests (test_live_stereo.py:614, test_mic_colour_relative.py:989, test_quick_pins.py:73) besides live_fdn.js:20.
**Refactor:** keep one pin test. Small, but each bump currently touches four files.

## Ranked refactors (value against risk; all keep goldens bit-exact)

| # | Refactor | Value | Risk | When |
|---|---|---|---|---|
| 1 | S5 BLOOM leftovers: retry replaces them, nothing new beside them | High | None | **Before/with BLOOM** |
| 2 | S3+S6 one blob/params schema, Python and JS byte-compare test, generated C offsets | Very high | Low-medium | **Before BLOOM** (BLOOM adds a blob section) |
| 3 | S2 `combined_ir_from_spec` and one planner for app_server colour preview | High | Low | **Before BLOOM** (pairs with PR-B2 fix) |
| 4 | S4 `resolve_mode()` single exception resolver; MOVEMENT_FORCED_OFF moves into it | High | Low | Before BLOOM if cheap, otherwise straight after |
| 5 | S1 split `_render_core` into RenderSpec plus still/moving/hop functions | Very high | Medium (big diff) | **After BLOOM**, in its own run, goldens checked byte-for-byte |
| 6 | S7 name magic numbers (mostly falls out of #2) | Medium | None | With #2, then after |
| 7 | S8 twin map and named parity test per pair | Medium | None | After BLOOM |
| 8 | S5 rest: legacy test-only paths, 16-bit CLI writers, HARM override, diffusion shim | Low-medium | None | After BLOOM |
| 9 | S10 single WORKLET_VER pin | Low | None | Any time |
| 10 | S9 split app.js / build_ui | Medium | Medium (UI tests) | Last |

Gate for every step: goldens and the out_20261013_115900.wav stamp sha1 unchanged, the harness at max-abs 0, selfcheck 45/45, and the wasm and DLL hashes unchanged for Python-only and JS-only steps.
