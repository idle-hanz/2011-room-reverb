# R18 · New finding: the direct sound ignores the mic pattern (one source)

**What (VERIFIED in code and in an offline render on the box, build 51):** render_pipeline.py `direct_capsule_spikes` (1050–1063) says "One source stays (1, 1, 1)". With one source, every capsule gets the direct sound at amplitude 1 whatever its pattern or aim. Patterns act only on the early reflections and the tail.

**Effects:**
- **MS:** the Side strip (route s) adds +1 to L and −1 to R for every source angle. Direct-only MS classic measured **11.2 dB louder in L at every source position** (sx 0.8 and 5.2 m give identical results; `proto/ms_direct_image.json`, real UI body). A front source should be centred.
- **Coincident pairs (XY, Blumlein):** the direct sound has no level difference, so no direct-sound image at all (ORTF direct-only L−R = 0.00 dB at every source position, measured). Spaced pairs still get time differences.
- Play: the live direct fold uses the same spikes (`LIVE_DIRECT_FOLD = 0.55`, line 1047), **ASSUMED** the same behaviour.

**Why it may be intended:** the docstring tags it ASSUMED (2011 parity: the 2011 dump had a pattern-free direct). Two sources already use pattern spikes normalised so the hottest capsule = 1.

**Recommendation:** when any strip is on route s, or a coincident pair is chosen, use the pattern spikes (the existing two-source path, `spikes=`), hottest capsule = 1. Ship it as part of D5 "Physical" realism, or at minimum for MS (where today's result is plainly wrong).

**Touch points:** render_pipeline.py 1050–1063 and the `spikes=` argument of `render_listen_direct_ir` (1066); the live direct fold (render_pipeline.py 1047 and live_stereo.c direct section).

**Tests / goldens:** MS-only fix: MS references only. For all setups: **main golden YES** (ORTF direct levels would differ by a few dB with source angle; ASSUMED, not measured). The strict xfail `prebuild/tests_py/test_t3_ms_presets_draft.py::test_ms_direct_sound_is_centred_for_a_front_source` pins it.

**Decision for Idle:** **Q-MS-DIRECT**: (a) fix for MS only now (recommend); (b) fix for all setups as part of D5; (c) keep the 2011 behaviour.
