# S4b final verify — box, 2 Oct 2026 16:28–17:30 BST

Snapshot: `snapshot_2026-10-02_1630` (read-only robocopy of the PC `software\` at 16:30 BST; PC not modified, app not restarted).
Method: as `roadmap/s4_verify_1140`. Everything here was run on the box (VERIFIED) unless marked ASSUMED.

| File | What |
|---|---|
| `live_stereo_c.diff`, `py_js.diff`, `build_test_edits.diff` | 11:40 → 16:30 source diffs; Build's edits to our acceptance tests |
| `measure/passivity.py/.json` | peaking biquads as Play sees them (float32 + C b2 restore), 0 Hz–Nyquist + 0.001 Hz grid to 20 Hz, all axes, 6 scenes × 44.1/48 k |
| `measure/bitexact.py/.json/.log`, `bitexact_dc.py/.json` | Play bit-exactness (shipped wasm = box build; signs off = 11:40; parity = 11:40; skip-centre = no-skip) and the DC-restore attribution |
| `measure/s4b_measure.py/.json/.log` | Solo/Mute early-only (D15/D16/D11), FDN untouched, Render parity, tail levels, comb index on Idle's scene (48/44.1 k), 44.1 k decay-20 runaway |
| `ui_s4b.py/.json`, `shots/` | headless Chrome D12 / D17 click test with Play live running |
| `cpu/bench_s4b.py/.json`, `cpu/t19_x3.log` | skip-centre CPU and stereo default CPU (alternating, 6 rounds) |
| `audit/binaural_ic_audit.*` | binaural IC gate audit (signs on/off/11:40, 7 scenes) |
| `audit/t30_dffs_audit.*` | P0.2 Dffs=0 T30 audit (signs on/off/11:40) |
| `audit/golden_audit.*` | Build's regenerated goldens: 16:30 = new goldens; 16:30 with signs off = old goldens |
| `phase_slow_boxtests.*` | phase suite --slow with our pre-S4b test files (+ Build's pack.py/wasm_run.js) |
| `phase_slow_adopted.*` | phase suite --slow after adopting Build's test edits + goldens + our 2 additions |
| `suites.log`, `run_all.*` | software tests, selfcheck, binaural suites, run_all --quick (old goldens) |
