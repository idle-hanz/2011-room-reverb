# TLAW distance law — locked by Idle, 10 Oct 2026

The software distance gain is amplitude 1/r (about 6 dB per doubling) for Play and Render.

This overrides the earlier software lines that said do not retune 1/r², the durable-lock note that the running engine used Air Abs 1/r², D22 (the later opt-in "Physical" 1/r), the 1/r² wording in D-MAKEUP-FREEZE, and the 30 Sep 2026 binaural exponent. Binaural still takes `geometric_level(r_h)` from the head centre, and both ears stay equal.

The Structure Air Abs graph remains 1/r² (shot 256: Dis×Dis then 1/x). Idle chose 1/r on 2026-10-10: AGC balance, close mics too loud, and the physical pressure law.

D-MAKEUP-FREEZE stays. Makeup is still frozen at the stand. Direct stays as it was: pattern spikes, 0.55 fold, delays follow distance. No distance law on the Direct bus.

`geometric_level` in `software/engine/early_field.py` returns `1.0 / distance`. A distance at or below 1e-9 stays 0.

## What was not touched

`live_stereo.c`, the wasm, the limiter, the 0.7 makeup target, and `makeup_at_stand`. `WORKLET_VER` stays 52. No app.js string names the distance law, so the page cache was left alone. Wasm sha1 `65949a98c1212a29d252b8c075e7ff5946c7f8d2`. `live_stereo.c` sha1 `3e3007f3586af26224470f6d207a2e7310d5a70f`.

Backup before the edit: `software_backup_2026-10-10_preTLAW.zip`, 339374491 bytes.

## Proof the goldens moved only from this law

The live-parameter blob, old law versus new law, differs in inject levels, the makeup scalar, and the unwired `direct_makeup` field. Delays, loop `g`, `g_decay`, and `direct_wet` match. Each changed inject sample matches distance within 0.12 percent (delay quantisation). A direct-only render is max-abs 0 between the two laws.

## Goldens

`GOLDEN_META.json` reason is `TLAW 1/r, Idle decision 2026-10-10`, sha1 `883cc7329582c21532fb44dbd040145e0ce7bc6e`, written 2026-10-10 19:36:28. Lengths unchanged.

| File | Old sha1 | New sha1 | Peak | RMS |
|---|---|---|---|---|
| `play_std_lock18_byp.f32` | `2ff13a7823b73108d77c3eeeed949f17fb6b697e` | `34bf6e6626bbb387d4f021bc5c1a7c92f1cfc230` | 0.000 dB | +1.403 dB |
| `play_std_lock18_col.f32` | `2b7cd581a643ec9a605da946ebc017ce7d6e19c5` | `827aa712d63a8f6870e9474f3ea9036fb16f8107` | 0.000 dB | +1.201 dB |
| `play_std_unlocked_byp.f32` | `a6136143ae1a1fcb7d6a747c659e219145f7477b` | `92ccae8962d252026fd9a702e7e0c9b2b703b9b5` | 0.000 dB | +2.971 dB |
| `play_std_unlocked_col.f32` | `3be174d45ca14ae4913961a80f5daff7add825e6` | `266d8429a94f2266bf0c87f92593930a98084155` | 0.000 dB | +2.248 dB |
| `render_std_unlocked_byp.f32` | `7668100a77e4b49d34f2a3aab1d027c0ec4ef6fa` | `7d0a1f4b1208bac1cffbec9f11e42ec23791f6f3` | 0.000 dB | +2.073 dB |

Harness t03 nulls −3008.2, −3005.6, −3005.2, −3002.2 dB, max-abs 0. t04 null −3007.0 dB, max-abs 0.

## Other pins that moved for this same cause

- Empty-body live MD5 `4bd18877a1a80396108bcafd17d4d762` → `af2b154a1e8f806d98a87e5e2e846022` (`test_b6_heights.py`, `test_s_audit_api.py`).
- Stored centre live MD5 `16bc17806a12f9c0ad3db32d104eaaaf` → `f30665f446a3c5163cafb8331909e1db`.
- `test_any_strip_route` residuals −33.30 dB → −39.00 dB, and −42.50 dB → −47.52 dB. One gain still brings the nulls to about −308 dB and −305 dB. The gain residuals are −0.098 dB and −0.037 dB.
- Smooth-off `d18.f32` and `d4.f32` heads (72001 frames) were regenerated. Head max-abs versus the old heads: 0.0969 and 0.0698. Full render lengths stay 133921 frames (1.8 s) and 292321 frames (4 s).

## Measurements (this tree)

Solo C on a room spot. Makeup is the frozen stand value. Pre-limiter peak steps are per doubling.

| Distance | Makeup dB | Pre-limiter peak dB | Step dB | Limiter dB | Limiter samples |
|---|---|---|---|---|---|
| 0.5 m | 17.267 | 11.828 | | 11.84 | 7090 |
| 1 m | 17.296 | 4.280 | −7.55 | 4.28 | 548 |
| 2 m | 17.355 | −0.887 | −5.17 | 0 | 0 |
| 4 m | 17.482 | −6.970 | −6.08 | 0 | 0 |
| 8 m | 17.753 | −13.009 | −6.04 | 0 | 0 |

The 2 m to 8 m steps are about 6 dB. The closer steps sit next to the Direct spike, which has no distance law.

Screenshot cases on this tree: far makeup 2.329 dB, peak −10.01, limiter 0. On the source, makeup −2.976 dB, peak −11.24, limiter 0. 0.30 m above the source, makeup −2.981 dB, peak −6.50, limiter 0.

Default scenes, noise, limiter amount 0: Studio peak −7.60 dB, Club −10.66 dB, Hall −2.19 dB, boot −10.04 dB. Stand impulses are max-abs 0.

Play versus Render makeup gap, same `g` split as before FIX-B: boot +0.0001 dB, solo centre at 0.5 m +0.485 dB, solo at 8 m 0.000 dB, far −0.427 dB, on-source +0.816 dB, two sources +0.0001 dB.

## Source moved, stand mics (report only)

Makeup was not changed. A closer source is still the softer makeup. Limiter 0.

| Source distance | Makeup dB | Peak dB | RMS dB |
|---|---|---|---|
| 0.5 m | −8.50 | −14.97 | −36.63 |
| 1 m | −3.02 | −13.76 | −36.55 |
| 2 m | 2.75 | −13.60 | −36.25 |
| 4 m | 8.62 | −12.99 | −35.60 |
| 8 m | 14.54 | −12.70 | −34.88 |

## Suite

pytest 125 passed, 25m16s, 1 warning. Node 38 passed, 0 failed. Selfcheck 45/45. `test_a12` and `test_a5` passed in the full pytest run.

Numbers file: `handoff_build_support_2/roadmap/fix_b/measure_tlaw.json`. The earlier `measure_fix_b.json` is the 1/r² record and was left in place. The measure script's "before" column loads the pre-FIX-B `render_pipeline.py`, which imports the live `geometric_level`, so that column is also 1/r. The tables above are the after column.

## Open

Idle listens before this is accepted. The stand-mic source move is still the open makeup question from D-MAKEUP-FREEZE. Close room-spot mics at 0.5 m and 1 m still reach the limiter.
