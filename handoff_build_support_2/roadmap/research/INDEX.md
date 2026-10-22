# Research briefs for Thursday (4 Oct 2026, box, build 51)

Every brief has real sources, VERIFIED/ASSUMED tags, a recommended design, exact touch points in the app copy, risks, test/golden impact and decisions. The pre-built code for T1/T2/T3/T7/T8 and the mockups are in `../prebuild/`; the paste prompts are in `../thursday_prompts/`.

| Brief | Key finding | Recommendation |
|---|---|---|
| R01 T1 knobs | Knobs are transparent range inputs: they jump, have no fine mode, detent or typing; the Width needle never moves (B2) | Built: relative drag, Shift fine, detent, reset, typing on 13 knobs + 21 sliders, proven in the real Mix tab |
| R02 T2 mixer | Every L/R/Ø state maps onto an existing route; null holds against the real `fold_for` | Built and tested; mic Solo = solo-in-place; rename to "On stand"/"Room mic" |
| R03 T3 MS | +3.5 dB Mid = ±53° vs ±63° at unity, a width choice, not a standard; B3 cause found (`ms_decode` never set) | Presets a/b/c built; ask Q2 |
| R05 T5/T6 U87 | U87 has ~6 dB more rear pickup and is brighter off-axis, so expect more room and tail | A/B plan (blind, loudness-matched) before T6; check the double-count |
| R07 T7/T8 drag | Server already takes per-strip mic positions, so T7 is client-only | Built: per-strip spots, Mirror/Linked/Split, wall/ceiling drag with a "stop" rule |
| R09 T9/T10 layout | Host strip hidden at 1280 px; Room size duplicated | Wrap strips; Room size on Room only + read-only chip |
| R11 reflections | Loudest-32 would gain ≤0.2 dB (1.2 dB only for a fig-8 side pair) | Keep LIVE_32 |
| R12 scatter | ~0.1 ms Play headroom left under 2.40 ms | Shared velvet-noise smear (keeps Play = Render); measure first |
| R13 D5 / D7 | Render small room is now −4 % at 1 kHz (−12 % at 250 Hz); Play not measurable on the box (harness out of step) | Re-measure Play on the PC, then accept or fix; D5 as opt-in "Physical" |
| R14 tank gating | Tank runs while FDN muted (2.17 ms) | Gate after the tail dies (−96 dB), restart from zero with a ramp; not urgent |
| R15 N18 | ORTF includes C at 0 dB (477 fold); C raises early L/R correlation 0.00 → 0.14 | ORTF = C off, plus an "ORTF + C" preset (golden YES), decide before T6 |
| R16 Space | The lattice view is wrong for angled rooms (few mirror sources are heard) | Plan + heard/blocked sources + paths + arrivals (mockups) |
| R17 Surfaces/Polar | Colour, absorption and Air are split; free sliders; 3-D polar is hard to read | Faces table + real materials + face tone + Air in Surfaces; 2-D polar, C follows desk |
| **R18 (new)** | **Direct sound ignores the mic pattern with one source: MS direct sits 11.2 dB left wherever the source is; coincident pairs have no direct image** | Fix for MS now; all setups via D5 |

## Decisions: all LOCKED by Idle, 4 Oct 2026 16:43 BST (`../DECISIONS_LOCKED_2026-10-04.md`)
1. **D18** (was Q2) MS Mid: unity decode + −3 dB on M and S → T3b.
2. **D19** (was Q-MS-DIRECT, R18) MS direct uses the pattern spikes, Render + Play → T3b (prototype `../prebuild/t3b_ms_sound/`, ORTF bit-exact).
3. **D20** (was N18) ORTF C off by default + "ORTF + C" preset → T4b, **main golden YES**.
4. **D21** (was D7) re-measure Play on the PC after T4, then accept/widen or fix → P-D7.
5. **D22** (was D5) realism as opt-in "Physical" options → later.
6. **D23** (was N17) tank gating after the tail dies, low priority → later.
7. **D24** (was D-SCATTER) velvet-noise smear, default off, CPU first → later.
8. **D-UI32** (was D-SURF1–4) Surfaces redesign (face tone per face, real materials, Air in, dial keeps tail) → later.
9. **D-UI33** (was D-POLAR1–2) 2-D polar small multiples, C follows the desk → later.
10. **D-UI34** (was D-SPACE) plan + paths view for angled rooms → later.
11. **D-UI35** (was D-ROOMSIZE) Room size on Room only + chip → T10.
12. **D-UI36** (was D-NAME/Solo) "On stand"/"Room mic", mic solo-in-place → T2.
13. **D-UI37** (was Q5 + D-DRAG) one Mirror/Linked/Split control → T7; wall drag "stop" → T8.
14. **D-UI38** (was T5 → T6) U87 default only after Idle's OK on the T5 A/B → T6 (gated).

`proto/` holds the probes and their outputs (d7_*, tap_suppression.*, ms_direct_image.json, n18_ortf_c_probe.*).
