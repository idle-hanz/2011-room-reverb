# Grok Build brief: linked Studio One plug-in prototype (P0–P3)

Read `DESIGN.md` first: architecture A (Source inserts + host send → one Room on an FX channel; shared state through an in-process registry; the web app as editor). Tags follow the same VERIFIED/ASSUMED rules.

## Ground rules
- Put the new code in a **new folder** (suggestion: `2011 Room Reverb\plugin\`), **not** in `software\`. Do not stop or restart the running tweak app. Add the FastAPI endpoint as a **separate new module** (e.g. `plugin_bridge_server.py`, a sibling FastAPI app on its own port) until Idle approves merging into `software\`.
- Toolchain on Windows: CMake + MSVC 2022, **VST3 SDK 3.8.x** (MIT) as a git submodule, and no JUCE. Build the x64 `.vst3` bundle and copy it to `C:\Program Files\Common Files\VST3\`. Run the SDK's own `validator` on every build.
- DSP comes from the existing C core (`engine/fdn_core.c`, `engine/live_stereo.c` lineage, with the F1–F3 fixes from `build_support/engine/work`). The plug-in shell must not change DSP behaviour.
- Real-time rules (DESIGN §5) are acceptance criteria, not suggestions: no locks, allocation, I/O or logging in `process()`; FTZ/DAZ on.

## P0: singleton proof (smallest possible)
Build one VST3 effect, **"RR Link Test"**, stereo in/out.
1. A process-wide registry (a function-local static in the DLL) holds `std::atomic<float> roomSize` and `std::atomic<uint64_t> revision`.
2. Parameter 0, "Room size (m)" (1–30), is exposed on every instance. When the host or UI changes it on instance X, X writes the registry and bumps the revision.
3. Every instance compares the revision in `process()`. If it changed, it adopts the value and updates its own parameter display. To tell the host, call `IComponentHandler::performEdit` from the **controller (UI thread)** via a timer, never from `process()`. Mark the document dirty (IComponentHandler2::setDirty; ASSUMED API name, check the SDK headers).
4. Audio proof: each instance adds a quiet sine at `100 * roomSize` Hz to its input, so the change is audible on both tracks.
5. Implement the PreSonus `IContextInfoProvider` query (header from github.com/fenderdigital/presonus-plugin-extensions, public domain). Log the channel name, type and **kDocumentID** to `%LOCALAPPDATA%\RR2011\p0.log` from a non-RT thread.

**Acceptance tests (in Fender Studio Pro 8 / Studio One 7):**
- two tracks with RR Link Test; changing size on track 1 changes track 2's display and tone within one block
- save, close and reopen the Session: the value is restored and both instances agree
- open a second Session in the same process if the host allows it (H9): record whether it shares the value (expected with a plain static) and what kDocumentID reports
- record-arm a track with monitoring on (Dropout Protection active): record in the log whether `ISlaveControllerHandler` reports a low-latency clone and whether the clone also receives the change
- run the VST3 validator: pass

## P1: registry + web bridge
1. Registry v1 per DESIGN §4: key `(documentID, roomId)`; `atomic<RoomState*>`; fixed slots for 128 `SourceState*`; epoch-based reclamation on a worker thread. There are two plug-in classes in one DLL: **RR Source** and **RR Room**.
2. The Room creates the roomId, saves RoomState in `getState` (magic `RR2011`, schema, CRC32, JSON) and restores it in `setState`. Each Source saves source_id, room_id, its SourceState and a cached RoomState.
3. The bridge thread (one per process, reference-counted) is a WebSocket client to `ws://127.0.0.1:<port>/ws/plugin`. It reads the port and token from `%LOCALAPPDATA%\RR2011\bridge.json`, which the server writes. Messages are JSON:
   - `hello{token, document_id, document_name, instances[]}`
   - `room_snapshot{room}`
   - `sources{list}`
   - `patch_room{base_revision, fields}`
   - `patch_source{source_id, base_revision, fields}`
   - `ack{revision}` / `reject{reason, current}`
4. Server side, as a new module: accept plug-in connections, keep the latest room and sources per document, serve a minimal page listing the sources with XY drag for position and a room-size field, and check the token and `Origin`.

**Acceptance:**
- dragging a source in the browser moves that Source's position in the plug-in within 100 ms
- changing room size in the browser updates every Source and the Room
- with the app closed, the plug-ins still load and play from the saved state
- no allocation on the audio thread: instrument a debug build with an allocation hook that asserts on the audio thread

## P2: audio engine split
1. **RR Source**: mono sum → direct + early images for its position using the room and mic snapshot. The mode is the C early field with per-hit serial filters and the L/C/R capsule fold, output stereo. Options: dry passthrough, early law (2011 1/r² or physical 1/r; see `research/room_validation/VALIDATION_REPORT.md` §5).
2. **RR Room**: stereo in (from the sends) → inject into the shared FDN with room-fixed delays (LIVE_32 image delays of a reference source at the room centre) → L/C/R mic fold + colour → stereo out. **Fix the t=0 allpass leak** (VALIDATION_REPORT §3.5): the output must not contain `-g*inject` at zero delay.
3. Heavy recompute (images, filters, delays) happens on a worker thread and is published as an `EngineConfig`. The audio thread crossfades configs over 20–50 ms.
4. **"Solo" mode** (option B): one Source runs the full 2011 structure (image = FDN line). It is used to A/B the shared-FDN approximation: render the same scene both ways offline, compare EDC, C80 and spectra with `research/room_validation/analysis.py`, and listen.

**Acceptance:**
- CPU with 1 Room + 16 Sources at 48 kHz / 256 samples; report per-instance µs per block
- real-time playback and offline bounce are equal within −90 dB (null test)
- a frozen Source track still feeds the Room
- no denormal CPU spikes after stopping the transport (let the tail decay for 60 s and watch CPU)

## P3: Studio One hardening checklist
- **Clones**: an instance in `kSlaveModeLowLatencyClone` does not create a new source; it mirrors its master.
- **Duplicate track**: the copy gets a fresh source_id but keeps its position.
- **Missing Room**: Sources still output direct + early and show "no room".
- **Two Rooms with the same roomId**: the second becomes a mirror.
- **Several Sessions**: kDocumentID isolation; if the host only processes the active Session, check that switching Sessions does not cross-link.
- **PDC**: all instances report 0 latency. Test a post-fader send to an FX channel, then the sidechain variant on a bus. Record any misalignment (FORUM reports suggest checking bus sidechains).
- **Dropout Protection**: all instances add < 3 ms so they stay on the monitoring path (H6).
- **Automation**: Room parameters are automated on the Room only, and a Source's position on that Source. Verify automation in an offline bounce.
- **Crash safety**: the bridge thread dying never affects audio.

## P4 (later)
- CLAP entry point, in the same binary or with the registry in process-scoped named shared memory. There is no documentID in CLAP: match on roomId only.
- `session_room.json` export plus a stems workflow for the heavy Python Render (DESIGN §6).
- AU (mac).

## Deliverables per phase
Code, a build script, a short `TESTLOG.md` with each acceptance item marked pass/fail and the host version, and CPU numbers.
