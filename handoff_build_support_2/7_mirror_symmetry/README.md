# 7_mirror_symmetry: Two sources + Mirror left/right asymmetry (1 Oct 2026)

Read `../MIRROR_ASYMMETRY_BRIEF.md` first.

## Contents

| Path | What it is |
|---|---|
| `prototype/MIRROR_on_p6.diff` | The fix against the tree + rebased patches (`work/p6`). Apply with `patch -p1` from `software/`, then rebuild `live_stereo.wasm`. **Bump WORKLET_VER and add a Reaktor-parity table**; the prototype does neither. |
| `prototype/MIRROR_on_build_1001.diff` | The same fix against Build's 1 Oct 07:36 tree. |
| `scripts/` | Box experiment scripts. They use the box paths `/workspace/build_support_2/work/mirror/<variant>/software`; `make_variants.py` builds the variants. |
| `results/` | Raw JSON and log output. `e1_*.json` is the full variant matrix. |

Both diffs were verified: applying them to a clean copy reproduces the prototype trees exactly (wasm excluded).

## Scripts

| Script | What it does |
|---|---|
| `make_variants.py` | Builds the variant trees: base, sym, tau (first τ), nopeak, and p6 variants |
| `tau_search.py` → `tau2.json` | Finds the final line order: τ = (b0 b4)(b1 b3), with (0,2,0) kept on line 0 |
| `colB_patch.py` | The B-side colour map: `fdn_b`, route 326, `fdnIdxB` / `yBlkB`, MAX_FILT 176 |
| `mirror_lib.py` | Idle's scene and the metrics |
| `e0`–`e8` | The experiments; see the brief §2 and §4 |
| `bench.py` | CPU with colour on |
| `render2_ir.py` | Two-source Render |

## Acceptance test

`../3_phase_acceptance_tests/tests/test_mirror_symmetry.py`. It is XFAIL until the fix lands.

**Harness change:** `harness/lib/wasm_run.js` `buildRoute` now emits 326 ints. This is backward compatible.
