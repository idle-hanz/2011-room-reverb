# UI-TIDY-1 report (2026-10-22)

UI only. `WORKLET_VER` stays 59. No restore. Sound, MD5, golden, wasm, and `live_stereo.c` pins held.

## Phases

| Phase | Status |
| --- | --- |
| 1 Place confirm, honest hint, active chip (U1, U2, U4) | done |
| 2 Physical readout (U7, U8) | done |
| 3 Warnings and failed-fetch toasts (U10, U20) | done |
| 4 Slider max from the room (U11) | done |
| 5 Hadamard 64/128 disabled while Play (U13) | done |
| 6 `:focus-visible` (U24) | done |
| U35 Lattice uses room-mic spots | done |
| 9a U36 Mix/Mic text at least 12 px | done |
| 9b U37 Early double-click resets to −∞ | done |
| 9c U38 Room sidebar link to Mic setup | done |
| 9d U39 Colour filter label | done |
| 9e U40 Chip focus ring and tab arrow keys | done |
| 9f U42 HTTP 500 banner `backend files not found` | done |
| 8 Save / Load / `localStorage` `rr2011.setup.v1` | done |
| 7 Live output meter | skipped |

Phase 7 was dropped from the end of the approved order so the gates and this report could finish. `live_fdn.js` was not edited.

## Versions

- `app.css?v=34` → `35`
- `app.js?v=62` → `63`
- `pack_room.js?v=52`, `live_fdn.js?v=59`, `sl_room_result.js?v=3`, `WORKLET_VER` 59 unchanged
- Bloom's next bump is `WORKLET_VER` 60 and `app.js?v=64`. `BLOOM_*.md` was not edited.

## Files (sha1 old → new)

Old hashes are the bytes inside `software_backup_2026-10-22_preUITIDY1.zip`.

| File | Old sha1 | New sha1 |
| --- | --- | --- |
| `software/static/js/app.js` | `fba5c3a7aaf1ff9428c4936e49ad2fb3ca6237e2` | `fb44577e41daca1c3eccfd0e33e27ddf47560e53` |
| `software/static/css/app.css` | `109c5607b50041adbfe54eab880bdca283d2cf69` | `89f5146ffddb56d3a81dba904154098751dffd0e` |
| `software/static/index.html` | `b9cd686dc012d0c8269ad029a925b69d6e9f9e1d` | `3a56f623b3af107ad67b1fe6ab14ecc1da1e4066` |
| `software/app_server.py` | `ade1b17523e9bff283ab83627dc62b24e49eb8ad` | `974f6403392d752ed8eae47be003474e6715514f` |
| `software/image_geometry.py` | `b790ad0106f7dec983d51bb85a3d1f2dd36e7e79` | `89c5c06d8742c1570c8804bfa58f89322aee17e8` |
| `software/tests/test_quick_pins.py` | `f9cc0cd42d13c7bf76ba76c11e57bc3a7e020ce2` | `e779692c7d127924a8b065a8260fbbb173c497e2` |
| `software/tests/test_b2_render_length.py` | `112930c7c02d01adb25e62dca75b67f66ad3232d` | `b99af50114363719230ddb49e7f928168af0e42a` |
| `software/tests/test_s_audit_ui.py` | `fdbd1d308bfc74041b536386396cedadb2fe592c` | `6e2db4655d729ff7376fbf0bd6a5420c72a2756c` |

`app_server.py` changed on the images route only. `image_geometry.py` gained `mic_override` and passes it through the two-source recursive build. The cache-pin tests now expect `app.js?v=63`. The audit test accepts the place confirm and lists `#saveSetupBtn` and `#roomMicSetupLink` as UI-only.

Unchanged, re-hashed after the edits: wasm `843a6eb8c91a9278ba927f643481f3260766a08c` (279668), `live_stereo.c` `bbdf57994e0996e2c9b77eb8a634550bb71ef3cf` (136434), `render_pipeline.py` `5fb71ad02be38dfb6a7d771e0032d6c959431434`, `surf_loop.py` `7e6e0ef005768a4397babb8870fefb94f2ca6956`, `fdn_worklet.js` `b39ccd9178c7ecf7145b3e267283b0b07aa6749d`, `live_fdn.js` `a936a5f1bfaf62d648c4e8da22d3808a8c73ac11`, `pack_room.js` `d69b4729ad52ca65145f9b6a6d900b3a3524d868`.

Temp DLL `%LOCALAPPDATA%\Temp\live_stereo.dll` was already `181d05cd0616b63c061e72b27900f4c4c331fcc3` (285184 bytes) at the start of the run. The historical pin is `dcde61dfa8ccc17244595244bd3cb7077c7f8433`. This run did not rebuild it.

`software/static/index.html.orig` is still on disk.

## Sound pins (VERIFIED)

- Empty MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88`
- Centre MD5 `b3e6bcd9dfa13ad737d2b15d561f7d30`
- Two-source `std_lock18` key-absent `a5dcacc67a269c234c4b5745899b038e`
- Explicit false `0e94bd03d899b76b43adf31ae87f0cd2`
- GOLDEN_META `a362cf5e490089807b39346ba207633b88511548`
- `play_std_lock18_byp.f32` `d011bafca80f4e46ae768db40becd762e78dcada`
- `play_std_lock18_col.f32` `d9470bfad67211180fedc1a07cd2352eaf4b14c7`
- `play_std_unlocked_byp.f32` `91738c70220b4edce512aebe3548dfdbd894cc41`
- `play_std_unlocked_col.f32` `a0ae72d9fb690cb7b3bbd54632abc466cefa0d24`
- `render_std_unlocked_byp.f32` `2a806e334e06cc475868d4c3da3fc78431c9a0aa` (192008 bytes)
- `d18` / `d4` prefix max-abs 0, from `test_b2_render_length.py`

## U35 capsules (VERIFIED)

Stand-only `/api/images` JSON (`sort_keys`, `default=str`) sha1 `d0cb6664a8b178e7a99b94a997645a1ec258376f`, the same digest as before the edit. Capsules stay on the stand: L (2.915, 1.5, 1.5), C (3.0, 1.5, 1.5), R (3.085, 1.5, 1.5).

Room body, L/C/R on Room at the probe: images returned L (0.5, 1.8, 4), C (3, 2, 7), R (5.5, 1.8, 4). `place_stand` returned the same three points. Delta 0 m on each capsule. Before the edit those room spots drew at the stand (review deltas about 3.5 m, 5.5 m, and 3.5 m).

## Gates

- Selfcheck 45/45.
- `test_quick_pins.py` + `test_physdefault_two_source.py`: 6 passed in 17.61 s.
- `test_b2_render_length.py`: 2 passed in 455.69 s.
- `test_s_audit_ui.py`: 12 passed in 313.88 s.
- Node `--test` was not run. No UI unit file was touched.

The first full audit failed two tests. `test_a2_phone_tabs` saw scrollWidth 456 because Save and Load kept the header on one row. Under 700 px, `.top-actions` now takes the full row and wraps. `test_a12_visible_controls_post_or_are_ui_only` listed `saveSetupBtn`, Studio, Club, Hall, and `roomMicSetupLink` because a dismissed confirm skipped `applyPlace`. The page script in that test now sets `window.confirm` to accept, and Save plus the mic link are on the UI-only list. A later solo run of a12 passed. The full file then passed 12/12. `test_a1_place_orders_match_fresh` accepts the dialog in `_posted` and passed inside that 12.

## Backup

`software_backup_2026-10-22_preUITIDY1.zip`, 102530000 bytes, sha1 `3b805a70ee82f47317ca1fc637ef1cb33d3ed6f6`, 241 files. Excludes `.venv` and `__pycache__`. Includes `renders\out_20261013_115900.wav`. Manifest `software_backup_2026-10-22_preUITIDY1.manifest.txt`.

## Left for Idle

- F4 Hall ramp
- F5 chip write-set (`applyPlace` / `resetToFresh` still wipe the same keys; the new step is the confirm)
- Character
- Phase 7 live L/R meter
- U41 (sound)
- Pre-delay, Width, Output, Advanced panel moves, and Mic-tab B10/B11 were left alone
- The reachable-dial sentence is on the physical readout when the server says the dial cannot be reached
