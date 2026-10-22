# INVESTIGATE Movement CPU (read-only, plan mode, no edits, no builds, no benches that write files)

Context: T11 (EQ-1b Movement) landed forced off. G2 failed: Movement 100%, shared off, median 2.718 ms (max 2.735) vs ceiling 2.40 ms. Movement 0 shared off 2.258 ms passes; Movement 0 shared on 1.748 ms and Movement 100 shared on 1.893 ms pass (ceiling 2.133). Smooth is default ON. Read HANDOVER Current pin, BUILD_RUN_LOG.md T11 entry, and the T11 report numbers first.

Answer from real code and existing bench output, tagged VERIFIED or ASSUMED:
1. Where does the extra ~0.46 ms at Movement 100 (shared off) come from? Name the code in live_stereo.c: the per-sample coefficient update, the allpass state per line, the extra branch or memory reads, the number of modulated lines (order[1::2], 16 of 32). If an existing bench or profile splits it, quote it. Do not run new benches.
2. Why does shared-on pass at Movement 100 (1.893 vs 2.133) while shared-off misses (2.718 vs 2.40)? What differs in the loop between the two?
3. How and when were the ceilings 2.40 ms and 2.133 ms set? Which tree, which wasm, was Smooth on, was the tail correction on? Quote the doc or test. Is 2.40 a real audio-thread limit (and what is it based on: 128-sample block at 48 kHz is 2.667 ms) or a margin chosen for the old tree?
4. List the cheaper options with their expected CPU effect and what each would do to the Movement SOUND: (a) 8 modulated lines instead of 16; (b) coefficient updated every N samples (what N is safe; note EQ_PLAN 4b and the earlier Frenette note said 16-25 samples, the prototype used per-sample); (c) a cheaper allpass form or precomputed eta table; (d) anything else you see. For each, say whether Render (Python FDN.process_block_poly) must change in the same way to keep Play and Render equal (G4).
5. Say what changing the ceiling would touch (BUDGET_MS, --perf-scale, tests) and whether that is a locked decision.

Write nothing. Report findings only. Make no recommendation that changes sound; Idle decides.
