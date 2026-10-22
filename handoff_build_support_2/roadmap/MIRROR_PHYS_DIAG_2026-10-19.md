# MIRROR_PHYS_DIAG (2026-10-19), read-only

Scope: the 5 new acceptance failures after PHYSDEFAULT (and the sh_p1 drift). Nothing under software\, the harness or the tests was edited. Scratch, scripts and logs are in %TEMP%\mirror_diag\ (diag_plugin.py, sections.py, play_probe.py, cpu_probe.py, render_two.py, loopgain2.py, *.log, work\*.json).

## Answer in one line
This is a real **Play-only DSP bug**, not a stale test. In two-source Play, source B's tank runs the physics sections that were designed for **source A's delay lengths**. Python sends one 3x32x3x5 section set, and the C engine applies it to both banks. Single-source scenes never run bank B, so the default scene, the goldens and Idle's listen files are not affected. In a big room the mismatch makes bank B **run away**: the hall twoB Play IR climbs to -0.7 dB RMS at 12 s. **Confidence: high.**

## Q1. Explicit phys_ceiling:false
Method: a scratch pytest plugin (-p diag_plugin) wraps run_all.Ctx.params and adds phys_ceiling False when the key is absent. Tree untouched; basetemp and cache in scratch.

| test | key absent | explicit false |
|---|---|---|
| test_mirror_play_two_sources_hard[fdn-MEASURED_SHELF] | FAIL null +0.685 dB, band 11.6, ILD 6.35, T30 207% | PASS |
| test_mirror_play_two_sources_hard[fdn-BYPASS] | FAIL null +1.17 dB, band 10.9, ILD 3, T30 290% | PASS |
| test_mirror_play_two_sources_centre_is_self_mirror | FAIL null -31.5 dB, T30 373% | PASS |
| test_sh_p7_mirror | FAIL -47.90 dB | PASS (<= -120) |
| test_mirror_play_one_source (control) | PASS | PASS |
| early/direct lanes (control, 4 params) | PASS | PASS |
| test_sh_p1_off_bit_exact (already red) | 0.012091 | 0.011196 (the exact pre-flip value) |

Physics causes all four mirror failures. The one-source mirror passes with physics on, so the fault is specific to two sources.

## Q2. Mechanism (hypothesis a, variant: B gets A's pack)
1. `render_pipeline.py:3180` calls `_live_surf_pack(p, room, surfaces, taps, ...)` with source A's `taps` only. `taps_b` exists (built at 3020) but is not passed.
2. `_sos_from_spec` (`render_pipeline.py:2637-2656`) designs each bus from `fdn_delays_from_taps(taps, ...)` (2638), with `lg` from A's delays (2639-2642). The loop-gain guard (2650-2658) sees only A. The Surfaces branch has the same shape (2748).
3. `fdn_worklet.js:147-161` loads one 1440-float set. `live_stereo.c:210-211` stores `slBuf` and `slC[3][SL_SEC][5][N]` per bus only. The state `slZ[3][2]...` (212) has a bank axis, but the coefficients do not.
4. `live_stereo.c:2235-2241` `surf_batch` always reads `st->slC[b]`; `bankB` only picks the z state. Bank B (2749-2754) reads `line->delayB` with `lgB`, then `surf_batch(st, b, 1, hn)`. So B line i gets A line i's sections on a different delay.
5. Each section set was fitted as "total loss for delay dA minus the dial lg(dA)". On delay dB the loss per second becomes 60/T_dial + (dA/dB)(rate - 60/T_dial). Wherever physics is longer than the dial (the sections boost), a B line with dB < dA can go above 0 dB per pass.

Numbers (sections.py, loopgain2.py, play_probe.py):
- Mirror-test hall (57x34.2x97, dial 0.71): B.L multiset = A.R multiset exactly, but in line order B.L[i] vs A.R[i] differ by up to 90 ms. dA/dB per line is 0.58-1.72. Physics T60 for A lines (median) is 11.4/10.0/7.7/5.8/3.7/2.5 s at 125 Hz-4 kHz. B lines span -213 s to +153 s, where a negative value means growth. Worst B-line loop gain with kept peaks is **+6.5 dB, with 30 B lines >= 0 dB**. The Python guard reported -0.279 dB because it only checks A.
- Play hall, 1 s RMS windows over 12 s, key absent: twoA -84.6, -101, ... -158.6 dB (decays). twoB -83.1, -90, -85.8, -76.8, -66, -54.8, -43.2, -31.6, -19.8, -8.5, -3.0, **-0.7 dB (runaway)**. Explicit false: both decay to -342 dB.
- BIG room (57x34.2x97, sx 24, dial 4, two sources): 6 B lines at +0.034 dB (marginal). 20x10x30 dial 4, sx 14: B worst -0.034 dB against A -0.16 dB. Boot room dial 1.8/4/8 and small 4x2.5x5: B within 0.003 dB of A, no line >= 0.
- Boot room two sources, mirrored, tail only, key absent: Play mirror null -35.5 dB, band 0.067 dB, T30 1.2% (B-line T60 at 125 Hz spans 2.08-4.09 s against an A median of 2.44 s). Explicit false: -183.7 dB, exact. Mild here, but not exact.

Rejected hypotheses:
- (b) The physics row depends on W/H/L/cards/dial only (`surf_loop.py:332-345`, `phys_ceiling_pack` 356-411), not on position. Render two-source mirror with physics is exact (below).
- (c) The line order differs between A and B. That matters only because coefficients are indexed by line, so it is the same bug as (a), not a separate one.
- (d) CPU, see Q2b.

### Q2b. test_p6 CPU 2.663 ms: noise, not physics
Ran the t19 bench body (std_lock18, talking_head + trumpet_byu, two sources) in 4 configurations (flat/Surfaces x shared off/on), key absent and explicit false, 3 rounds each (24 benches, cpu_probe.json):
- Surfaces shared-off, key absent: median 1.600-1.617 ms, silence-late **1.611-1.631 ms**. Explicit false: 1.598-1.611 / 1.613-1.627.
- Flat shared-off, absent: 1.601-1.615 / 1.625-1.640. Explicit false: 1.596-1.610 / 1.606-1.621.
- Shared-on, all: median 1.743-1.779, silence-late 1.759-1.790 ms (limit 2.133).
- Every silence-late is within 1.04x its median. Physics adds at most about 0.02 ms. No denormal signature.

The 2.663 ms was a one-off spike on a busy machine (it ran inside the 14-minute acceptance suite). The isolated harness t19 (1.619) agrees with these 24 runs. Rerun it alone. No code issue.

## Q3. Play only? Yes.
- Render designs per tank: `render_fdn_ir` -> `_surf_bus(taps, ...)` (`render_pipeline.py:1212`) -> `fdn.py:1011-1012` `design_bus(self.delays, ...)`. Two-source Render calls it once with taps_b (1997/2040).
- Direct `_render_impl` probe (render_two.py; output captured in memory, nothing written to the tree): two-source mirror, key absent, **hall -216 dB, boot -232 dB**, all metrics 0. Explicit false: -242 / -234.
- The single-source default hides it: bank B runs only when `two` (`live_stereo.c:2551` single-source branch). test_mirror_play_one_source passes with physics, and t18/test_p0_4 are single-source.
- Harness note: `harness/lib/render_ir.py:44` hard-codes `two_sources=False`, so the harness cannot test two-source Render at all. That is why only Play tests caught this.
- The same shared-coefficient bug already existed before PHYSDEFAULT for `decay_mode: surfaces` with two sources (render_pipeline 2748 path). It is smaller there because Surfaces sections are anchored to the dial: hall twoB Surfaces with explicit false decays (-141 dB vs A -145 dB at 2 s), so no runaway. It was also reachable before today by ticking the physics box with two sources. PHYSDEFAULT exposes it by default.

## Q4. What Idle has heard: unchanged
The AMBIENCE listen files (`roadmap\ambience\listen\`, A/B/C/D) are **Render** and **single-source**. `ambience\make_listens.py` uses `smalldecay\make_listens.py` `page_body` / `render(...)` with `"two_sources": False` (lines 85, 147). The only Play file, `listen\_play\params.json`, has two_sources False. Render is correct anyway. Idle's approval stands, and he does not need to re-listen for the diagnosis.

## Q5. Fix options, ranked

### 1. RECOMMENDED (correct fix): per-source section banks (DSP + wasm; its own run, not PHYSDEFAULT)
- `render_pipeline.py`: `_sos_from_spec(..., taps_b=None)` also designs bank B from `fdn_delays_from_taps(taps_b, ...)` with B's lg. It emits `surf_sos_b` (1440) only when two sources are present, and the guard (worst) covers both banks. Do the same for the Surfaces branch (~2740-2770). Pass `taps_b` at 3180.
- `fdn_worklet.js` 147-161: copy `surf_sos_b` into a new `live_surf_ptr_b` when present.
- `live_stereo.c`: add `slBufB` and `slCB[3][SL_SEC][5][N]`, export `live_surf_ptr_b`. `live_load_surf` validates (finite and Jury) and loads B, or copies A into B when B is absent. `surf_batch` (2239-2240) uses `bankB ? st->slCB[b] : st->slC[b]`. This covers shared tail, which goes through the same surf_batch on BUS_C.
- Rebuild wasm with the zig command in the `live_stereo.c` header (wasm32-freestanding -O3 -msimd128 ...). Bump WORKLET_VER 58 -> 59 (live_fdn.js:20, index.html 964 `live_fdn.js?v=`, test_quick_pins 73-74, test_live_stereo 614/616, test_mic_colour_relative 989/990). pack_room.js is unchanged because the sections are off-blob.
- Pins that move: the wasm and live_stereo.c sha1, WORKLET_VER, and two-source Play output with physics or Surfaces. Audit any two-source live pin (e.g. `_ORTF_PLUS_C_LIVE_MD5` if it is two-source and the MD5 includes the live dict). **Single-source goldens stay bit-exact**: the five TLAW goldens, GOLDEN_META, the empty/centre MD5s and d18/d4, because bank B does not run and the dict grows no key without two sources. Explicit false stays bit-exact (no sections are sent).
- CPU: no extra per-sample work (same biquad count; the pointer differs). +23 KB state. Python pack time for two-source physics roughly doubles in design_bus calls (cache by delay), which affects Play pack latency, not the audio thread.
- Expected result: the 4 mirror tests pass as they are, and the hall twoB runaway is gone.
- Add tests: (i) two-source physics Play, hall twoB, 12 s, RMS falling every second; (ii) the two-source mirror on `decay_mode: surfaces`; (iii) the Python guard reports both banks.

### 2. Interim, smallest safe change with no DSP edit (lets PHYSDEFAULT land without breaking rule 1)
- `app_server.py:641`: two sources use the dial path unless the fix lands. For example `phys = (_b(body["phys_ceiling"], True) if "phys_ceiling" in body else True) and not two_sources` (two_sources is parsed at 528, before this line).
- Play and Render both follow, so they still agree. /api/phys_preview reports on:false for two-source. The UI note should say the physics decay is single-source for now.
- Measured outcome: identical to the explicit-false run above (all 9 mirror cases plus sh_p7 PASS).
- No pin moves: the defaults, goldens and live MD5s are single-source. No wasm change, CPU unchanged.
- Cost: two-source scenes keep the dial sound until fix 1. The latent Surfaces two-source mismatch remains (pre-existing, no runaway seen). Log it in OPEN_FAULTS with the runaway evidence.
- Variant 2b: skip the physics pack only in Play (`_live_surf_pack` 2699 `and not p.get("two_sources")`). It is smaller, but Play and Render then disagree for two-source scenes. Not recommended.

### 3. Rejected: test-only explicit false on the 4 tests
Symmetry must hold physically: in a mirrored scene in a symmetric room, Render is exact (-216 dB) with physics on. Play's error is not a test tolerance issue: B's loop gain is +6.5 dB and its tail rises to -0.7 dB RMS. Muting the tests would ship a runaway on the default path.

### sh_p1 drift (already red, report only)
It fails first at `def_1_on`, which is a **single-source** boot body checked against the old S4b wasm. With explicit false it is exactly 0.011196. With physics on, the same pre-existing difference rides on a different signal (0.012091). This is not the bank-B bug and needs no action in this run.

## Does Idle need to listen?
Not for this diagnosis or for fix 2, which only changes two-source scenes back to the dial sound. After fix 1, an optional quick listen to a two-source Play scene with physics is worth doing, because no one has heard two-source physics Play yet. His single-source approval is unaffected.

## Side observation (not acted on)
`k_for_dial` solves k on the 6x3x8 boot room (`surf_loop.py:320-329`). In the 57 m hall, dial 0.71 therefore gives physics T60 of about 6-10 s at the mids. That large boost relative to the dial is why bank B blows up there. This is by design ("the dial chooses k"), but Idle may want to know that the physics path makes big rooms much longer than the dial number.
