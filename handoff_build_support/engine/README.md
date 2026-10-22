# Engine support pack for Grok Build (2026-09-27)
- findings/bug_denormal.md: Bug 1 (silence CPU blow-up): root cause, fix, numbers
- findings/bug_tail_length.md: Bug 2 (tail too long, slow 9/11 kHz residue, Render check, positive-Dffs instability) + findings/t60_sweep_raw.txt
- findings/play_vs_render_parity.md: divergence table (cause, severity, fix)
- briefs/GROK_BUILD_BRIEF_Engine_fixes.md: what to change, order, acceptance tests, all diffs inline (+ separate .diff files; verified to apply cleanly to the snapshot with patch -p1)
- tests/: run_all.py regression/acceptance pack + goldens + README (run on a machine with node, i.e. the box)
- bench/: live_stereo_cpu_bench.html, open it in a browser on the PC and press Run
- tools/: harnesses used for the analysis (native runner, wasm-in-node runner, packer, analysis scripts)
Analysis snapshot: box /workspace/build_support/snapshot_2026-09-27/software (patched test trees are in box work/, not copied).
