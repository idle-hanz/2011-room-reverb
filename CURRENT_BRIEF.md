# Current brief (2026-11-15)

A Thursday run starts here and at `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md`. Do not open `HANDOVER.md` for that run. One goal per run. Prompts give only the delta. This page wins over an older pin list inside it. A prompt's own pin list wins over this page when the prompt says so.

## App

Desktop room reverb. Play is the live preview (2.40 ms ceiling). Render writes the WAV and has no CPU ceiling. Open `software\Launch Tweak App.bat`, then http://127.0.0.1:7860/.

The page is Room, Mic, Mix, Surfaces, and Polar. The image view sits on the room page.

Eight HTTP routes:

- `GET /`
- `GET /api/settings`
- `POST /api/render`
- `GET /api/render`
- `POST /api/params/{kind}` (live, images, phys, source)
- `POST /api/display/{kind}` (polar, field)
- `POST /api/room/{kind}` (result, treat, panel, calibrate)
- `GET /api/catalogue/{kind}` (mics, sources, materials)

Software geometric level is 1/r. The Structure Air Abs graph stays 1/r². `c` is 340.

Shoebox faces stay A–F: A left, B front, C right, D back, E floor, F ceiling. A polygon split is that letter plus a number (F1..Fn, and the same pattern on A–E). Bare F covers F1, F2, and F3.

`WORKLET_VER` is 65 in `software/static/js/live_fdn.js`. Cache queries are the `PIN_TABLE` in `software/tests/test_quick_pins.py`.

There is no preamp, no compressor, and no bloom in the product. There is no Mix routing panel. `RR_SL_STAGE` is not a live switch. Old preset keys of those features strip on load. The Movement knob stays. Default is 0.

## Pins

Live MD5 is `md5(json.dumps(live_fdn_params(params_from_body(body)), sort_keys=True, default=str))`.

| Pin | Value |
|---|---|
| Empty live MD5 | `06bb1aaa0f59d67402b160224e155089` |
| Centre live MD5 (`third_mic` centre, `mic_gain_c` 1) | `64f8319d8bf4e33353f8681ec31140de` |
| Two-source, `phys_ceiling` absent | `325a47d37bc34a1b1959a962f959a673` |
| Two-source, `phys_ceiling` false | `61277ba9bfc3f90cf1de3702e3a57125` |
| Splay live MD5 | `6d996c03137772aaca9cebecab3358ac` |
| `software/tests/data/quiet.f32` MD5 | `e38862e337b2b5ebf394c9a09f93212b` |
| `GOLDEN_META.json` SHA1 | `fd356749d18eacb7e4768ea798061f5b1b8ec030` |
| `play_std_lock18_byp.f32` SHA1 | `f5e9ebce2759262bc63a6fa67f30caecee2375ff` |
| `play_std_lock18_col.f32` SHA1 | `a3a796a516436c682e9af71deaf77081a5509939` |
| `play_std_unlocked_byp.f32` SHA1 | `778a241ce39842a3252e37617cb3a8f196f547eb` |
| `play_std_unlocked_col.f32` SHA1 | `c2a74eec10c0a12c1747ceabd7993f0db93a5e12` |
| `render_std_unlocked_byp.f32` SHA1 | `135c41ce546c390ef048a28713338259db07bd0a` |
| `d18.f32` SHA1 | `8d7b4859d984ac7455ed5e9ef540470abaf415d9` (576008 bytes) |
| `d4.f32` SHA1 | `ddb712596a54bbccdf7c9dfe066f1df59a569ad0` (576008 bytes) |
| `software/listen/rk1/B.wav` | 24-bit round-trip max-abs 0, peak `0.110000371933`, 48000 Hz, 325920 frames |
| `WORKLET_VER` | 65 |

Two-source uses harness `run_all.SCENES["std_lock18"]` with `two_sources` true. Goldens live in `handoff_build_support_2\3_phase_acceptance_tests\harness\golden\`. `d18.f32` and `d4.f32` live in `handoff_build_support_2\research_ui_wishlist\s_audit\b2_pre_item\`.

## Do not touch

Do not retune 1/r, the 0.55 Direct fold, the desk, makeup, the limiter, or the decay lock. Do not retune the Movement curve. The knob default stays 0. `c` stays 340. Do not flip L/R or floor X. Do not fold B into A's tank. Do not edit the original `.ens` files. Do not wire A–F bit tables into the audio path. Do not put the preamp, the compressor, or bloom back. Do not re-pin the goldens on a bare continue.

## Where files live

Canonical root is this folder (`ensemble\`, `software\`, `findings\`). Python is `software\.venv\Scripts\python.exe`. Goldens are under the harness path above. Backlog: `handoff_build_support_2\roadmap\IDEAS_BACKLOG_2026-10-19.md`. Screenshots stay in `C:\Users\IdleHanz\Pictures\Screenshots\`. Do not treat `2011-Room-Reverb-publish\`, Desktop zips, or `docs-*-tmp\` as the live tree.

## QUICK (after each step)

From `software\`:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
node --test (Get-ChildItem tests\*.mjs | % FullName)
```

PowerShell does not expand the glob. Add pytest for the test file you touched. `@pytest.mark.slow` is not QUICK.

## FULL (once, at the end)

`software\pytest.ini` addopts are `-n auto --dist loadscope -m "not slow"`. `-m slow` overrides that mark.

From `software\`:

```
.\.venv\Scripts\python.exe -m pytest -n auto -m "not slow"
.\.venv\Scripts\python.exe -m pytest -n auto -m slow
.\.venv\Scripts\python.exe -m pytest tests\test_golden_rerender.py
.\.venv\Scripts\python.exe -m pytest tests\test_s_audit_ui.py -m slow
```
