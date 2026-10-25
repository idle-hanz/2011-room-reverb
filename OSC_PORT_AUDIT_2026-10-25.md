# OSC and network-port audit (2026-10-25)

Read-only. No product code, goldens, wasm, or `WORKLET_VER` were edited. Searched `ensemble\`, `findings\`, `software\engine\early_field.py`, and `software\` (`app_server.py`, static JS, the worklet).

## Answer

The live tweak app speaks HTTP on `127.0.0.1:7860`. It does not speak OSC. It does not open a WebSocket. The Play worklet has no socket: the page posts a packed blob on an in-process AudioWorklet `MessagePort`.

One OSC port for this layer would be a new program. It would not, by itself, move the goldens, `WORKLET_VER`, or the 2.40 ms Play ceiling, as long as the same scene still reaches `params_from_body` / `live_fdn_params` / `render` and the worklet `process()` path stays as it is.

## Port table

| Port | Who talks | File:line | Tag |
|------|-----------|-----------|-----|
| **7860** TCP, HTTP, `127.0.0.1` | Browser page ↔ FastAPI (`uvicorn`). This is the live app. | `software\app_server.py:1774`–`1775` (`host="127.0.0.1"`, `port=7860`). Static mount `software\app_server.py:65`. Launcher `software\Launch Tweak App.bat:28`–`44` starts `python app_server.py` and opens `http://127.0.0.1:7860/`. | **VERIFIED** |
| **7860** TCP, HTTP | Old Gradio UI, same number, not what the launcher starts. | `software\tweak_app.py:599`–`604` (`server_name="127.0.0.1"`, `server_port=7860`). | **VERIFIED** code. **VERIFIED** unused by `Launch Tweak App.bat:44`. |
| *(none)* | Playwright test asks the OS for a free TCP port, then runs the same FastAPI app on it. | `software\tests\test_s_audit_ui.py:28`–`29` (`bind(("127.0.0.1", 0))`), boot string `:72`. | **VERIFIED**. Not a product port. |
| *(no number)* | Page ↔ worklet. `MessagePort`, not a network port. | `software\static\js\fdn_worklet.js:6`–`7` (“This thread has no fetch.”), `:36` (`this.port.onmessage`), `:435` in `live_fdn.js` is the page post (`node.port.postMessage`). Status posts back: `fdn_worklet.js:47`, `:128`, `:162`, `:237`. | **VERIFIED** |

No other `server_port`, `uvicorn.run`, `WebSocket`, `ws://`, or `socket.bind` in `software\*.py` / `software\static\js` except the rows above. `software\requirements.txt` lists FastAPI, uvicorn, numpy, scipy, python-multipart. No `python-osc`.

## HTTP on 7860 (the only data exchange)

All page calls are relative URLs, so they hit whatever host served the page. The launcher’s host is port 7860.

| Path | Server | Page caller | What moves |
|------|--------|-------------|------------|
| `GET /` | `app_server.py:935` | browser navigation | `static\index.html` |
| `GET /static/…` | `app_server.py:65` | script tags; wasm `live_fdn.js:181`; worklet module `live_fdn.js:184` | JS, css, `live_stereo.wasm` |
| `GET /api/defaults` | `:940` | `app.js:4138` | boot scene |
| `POST /api/geometry` | `:946` | no `fetch` in `software\static` | geometry JSON if a client posts |
| `POST /api/live_params` | `:952` | `app.js:1399` (decay readout), `:1427` (`pushLiveParams`), `:4015` (Play start) | scene in, live coefficients out. Page then `postMessage`s the pack. |
| `POST /api/images` | `:1006` | `app.js:1591` | early lattice / paths |
| `GET /api/source_presets` | `:1059` | `source_desk.js:449` | radiation catalogue |
| `POST /api/source_preview` | `:1064` | `source_desk.js:327`, `:340` | polar + direct dB |
| `POST /api/render` | `:1351` | `app.js:3795` (multipart WAV + `params_json`) | WAV out; JSON includes `preview_url` |
| `GET /api/preview` | `:1365` | `app.js:3816` sets `previewAudio.src` | rendered WAV bytes |
| `GET /api/mic_presets` | `:1387` | `app.js:2752` | catalogue |
| `GET /api/mic_presets/{mic_id}` | `:1393` | no `fetch` in `software\static` | one preset |
| `GET /api/surfaces` | `:1411` | no `fetch` in `software\static` | default cards |
| `GET /api/surface_materials` | `:1417` | `colour_surfaces.js:1262` | library |
| `POST /api/room_result` | `:1429` | `sl_room_result.js:419` via `post` at `:42` | T(f) model, no audio write |
| `POST /api/auto_treat` | `:1453` | `sl_room_result.js:352` | suggested rows, scene not written |
| `POST /api/make_panel` | `:1478` | `sl_room_result.js:330` | one treatment row |
| `POST /api/surf_calibrate` | `:1509` | `sl_room_result.js:400` | seven `surf_cal` factors |
| `POST /api/phys_preview` | `:1559` | `app.js:777` | octave ceiling readout |
| `POST /api/colour` | `:1597` | no `fetch` in `software\static` | short-IR colour |
| `POST /api/polar` | `:1715` | `app.js:2722`, `polar_field.js:366` | mic polar plot |

Four routes are on the server and have no caller in `software\static`: `/api/geometry`, `/api/mic_presets/{mic_id}`, `/api/surfaces`, `/api/colour`. They still listen on 7860. **VERIFIED** by search of `software\static`.

## Ensemble

`ensemble\2011-room-reverb.ens` and `ensemble\20 October 2011 room reverb.ens` are the same file (887330 bytes, sha1 `65130dd5e8d9bea948dddfdeb445bd466075f1f0`). **VERIFIED** this run. No notes file sits in `ensemble\`.

Raw bytes, ASCII and UTF-16: `OSC`, `UDP`, `http`, `7860`, `localhost`, `127.0.0.1`, `socket`, `OSC Receive`, `OSC Send` — count 0. **VERIFIED**.

The 24 `bilz` blobs (zlib, header `78 9c`) inflate to about 5.9 MB. Same needles: count 0. The twelve `Send` hits are the Reaktor help string “Sends an event with a latest”, not OSC Send. **VERIFIED**.

Cleartext `port` hits are `KInPort` / `KOutPort` and the built-in Terminal In Port / Out Port blurbs. Those are module terminals. **VERIFIED**.

## Structure notes

`findings\` has no `OSC`, `UDP`, `localhost`, or `WebSocket`. The word port in those notes is a Reaktor terminal (`findings\ens-binary-notes.md:54` “Panel port names”, and the Structure batches). The only network port written there is historical Gradio:

`findings\screenshot-catalog.md:92` — “Click-to-place matplotlib UI at `:7860`.” That is the old app, not this Canvas app. **VERIFIED**.

## Early-field prototype

`software\engine\early_field.py:1`–`3` is the image-source prototype. `parse_args` at `:2455` is a CLI (room metres, `--sr`, `--c`). `__main__` at `:2627` calls `main()`, which writes a WAV. No socket, HTTP, or port. **VERIFIED** (search of that file).

## What one OSC port would involve

**PROPOSAL**, not a change in this run.

OSC here means UDP (or TCP) Open Sound Control, one port, carrying UI ↔ engine messages.

1. Nothing in this tree receives OSC. A listener would be new Python beside `app_server.py`. `requirements.txt` has no OSC library.
2. The page is a browser. A browser cannot open a UDP OSC socket. `fetch` in `app.js` cannot be pointed at an OSC port. A single OSC port does not serve `index.html`, the JS, or `live_stereo.wasm`. Those stay on HTTP, or the UI stops being this page.
3. `POST /api/render` uploads a WAV and `GET /api/preview` returns a WAV (`app.js:3795`, `:3816`). OSC datagrams are a poor fit for that file. Control JSON can move. The file transfer cannot, without a second channel or a size scheme this app does not have.
4. Play’s live hop is HTTP JSON (`/api/live_params`) then `packRoom` on the main thread then `MessagePort` (`live_fdn.js:435`) then `fdn_worklet.js` copying the blob into wasm (`fdn_worklet.js:9`–`10`). An OSC message that becomes the same `live_fdn_params` dict, off the audio thread, leaves that hop alone.
5. The ensemble has no OSC Receive / OSC Send module, so Reaktor is not already the other end of a port. Wiring the 2011 panel to this engine would add those modules in Reaktor. This run does not edit the `.ens`.

## Goldens, WORKLET_VER, 2.40 ms

- **Goldens.** They hash Render audio. The transport is not in the hash. Same body into `render()` keeps the five goldens. A parser that drops or retunes a key would move them. The port change itself does not. **VERIFIED** that today’s audio does not read a socket; **PROPOSAL** that a faithful OSC copy of the same JSON would not re-pin.
- **`WORKLET_VER`.** `software\static\js\live_fdn.js:20` is `63`. It only busts the cache on `fdn_worklet.js` and `live_stereo.wasm` (`live_fdn.js:181`, `:184`). OSC in Python does not touch that number. It changes if the worklet, the wasm, or the posted blob layout changes.
- **2.40 ms.** `handoff_build_support_2\3_phase_acceptance_tests\harness\run_all.py:29` sets `BUDGET_MS = 128 / 48.0`. t19’s shared-off ceiling is `0.90 * BUDGET_MS` (2.40 ms) at `:377`. That is the audio block in `process()`, not a socket. `fdn_worklet.js:31` says `process()` must not allocate. OSC parsed on the main thread or in Python, then the same `postMessage`, stays outside that budget. OSC read inside `process()` would spend it.

## Method

Byte scan of both `.ens` files (ASCII, UTF-16, and all 24 inflated `bilz` blobs). Ripgrep over `findings\`, `software\*.py`, `software\static\js`, `software\*.bat`, `requirements.txt`, and `early_field.py` for `OSC`, `WebSocket`, `uvicorn`, `server_port`, `7860`, `fetch(`, `/api/`. No app was started. QUICK was not run: no engine, JS, or golden file changed.
