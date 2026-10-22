# build_support — planning pack for Grok Build (2011 Room Reverb rebuild)

Written 27 Sep 2026 (BST). These are docs only. Nothing in `software\` was changed, and the running app was not touched.

## Read in this order

1. **`planning/BUILD_ROADMAP.md`**: one ordered plan across every pending handoff (Phase 0 engine fixes → blob v2 → ISO air → Surfaces A/B → Play cascade → scattering → source radiation → C migration → plugin). It includes the dependency graph, PR-sized steps with files, tests and A/B listening checks, the CPU budget, the shed order, and the implemented-vs-not table.
2. **`engine/`**: bugs, parity, tests and bench (denormal, tail length, 9/11 kHz residue, loop semantics). **This folder is produced by a parallel worker.** It may still be in progress; Phase 0 of the roadmap defers to it.
3. **`planning/C_MIGRATION_PLAN.md`**: which Python moves to C and in what order, one shared core (split `live_stereo.c`, retire `fdn_core.c`), loop semantics, WASM / native / plugin builds, SIMD, denormals, N, ABI versioning, verification tolerances, tests, sources.
4. **`planning/PARAMETERS.md`** + **`planning/parameters.csv`**: every current and pending control, with defaults (server vs client), provenance, tabs, Play/Render support and a conflict list.
5. **`planning/LICENCE_AUDIT.md`**: licences for every dataset and dependency, and the checklist before sharing with Ben Supper or publishing on GitHub / idlehanz.com. **Blocking item**: the TU Berlin instrument data.

The source briefs these docs merge (authoritative for detail) are on the box:

- `/workspace/handoff_surfaces_for_build/`
- `/workspace/source_radiation/`
- `/workspace/mic_fitter/`
- `/workspace/air_fitter/`

## Research (added 27 Sep 2026, evening)

Research, harnesses and briefs, in `research/`. These are not implementation; each brief is for Grok Build when Idle says go. Read them in this order:

6. **`research/reference_2011/CAPTURE_GUIDE.md`**: Idle's step-by-step for capturing impulse responses from the original 2011 Reaktor ensemble. It has a fixed grid (GainF × Diffusion Master × Humidity), Studio One or standalone recording, file naming, the JSON sidecar, and a list of controls whose names or ranges are still UNKNOWN. The impulse files are in `research/reference_2011/impulses/`. **`research/reference_2011/compare/`** holds `compare_ref.py`, the harness that renders the matching Render and Play IRs (current, F1–F3, F1–F3+F5) and gives verdicts on (a) two-stage tail vs F2 and (b) z⁻¹ vs same-sample loop. It is tested on TEST-ONLY stand-ins; see `compare/README.md`.
7. **`research/cheap_colour/FINDINGS.md`** + **`GROK_BUILD_BRIEF_Cheap_colour.md`**: replace the Play colour FIR with SOS K = 3 plus a per-mic w-table. Colour cost drops about 88% (1 source 1.16 → 0.58 ms/block) with ≤ 0.46 dB error and a −48 dB render null. It includes a C diff, acceptance tests, and the updated full-roadmap CPU budget.
8. **`research/surfaces_extras/FINDINGS.md`** + **`GROK_BUILD_BRIEF_Surfaces_extras.md`**: angle-dependent absorption (LATER), porous thickness/air-gap presets (YES, offline), panel resonances (LATER), FDN wall-tone from materials via Eyring (YES, decay lock only). Sources are cited and there are prototype plots.
9. **`research/room_validation/`** and **`research/studio_one_plugin/`**: **written by a parallel worker** (room validation; Studio One plugin design). Read their own READMEs.

**Sample-0 click (room_validation finding):** the FDN diffuser emits its Schroeder-allpass feed-forward term at t = 0, before the direct sound (`fdn.py process_block_poly` `y = -gi*x + v`; the same form is in `live_stereo.c` around line 956). **Play has it too** (checked by the cheap-colour/compare harness): about −24 to −32 dB re direct in default scenes, and −8 to −10 dB at Diffusion Master −0.5. It is present in every tree (current, F1–F3, F1–F3+F5) and does not depend on colour. The 2011 Diffuser Delay probably has the same structure (ASSUMED), so decide whether to fix it only after Idle's captures (`compare_ref.py` reports `zero_time_db_re_direct` for the reference). Details: `research/cheap_colour/FINDINGS.md` §4.

## Other contents

- `planning/snapshot/software/` (box only): the read-only code snapshot of `software\` from 27 Sep, used for the VERIFIED claims. It is not copied to the PC.
- On the PC: `handoff_build_support\software_snapshot_readonly.tgz`, the tar the snapshot came from. It is safe to delete.

## Tags used throughout

- **VERIFIED**: read in the code or docs.
- **ASSUMED**: estimate or proposal.
- **BRIEF**: from a pending handoff brief.
- **UNKNOWN**: not determinable.
