# Rebased patches for Build's 1 Oct 2026 tree (its last edits are dated 29 Sep 22:00 BST, WORKLET_VER 33)

- **Base:** the read-only PC snapshot taken 1 Oct 07:36 BST.
- **Result:** `work/p6/software` on the box.
- **Superseded:** the 28 Sep patches 02 (F3), 06 (K4 stale early) and 08 (colour per rate). Build did all three itself on 29 Sep, and its 44.1k tables are byte-identical to ours.

| Patch | Contents | Hunks |
|---|---|---|
| `R01_F2_line_absorption.diff` | F2: per-line loss, g = 1/√N, `line_t60` blob float (BLOB_LEN 1982). **Has no version bump: apply R09 with it** | 26 |
| `R03_diffusion_master_clamp.diff` | First clamp (final range set in R05) | 1 |
| `R04_K1_yaw_convention.diff` | `YAW_X_SIGN = +1` (Python + JS), polar_field, mic_display, mic_desk; 5 crossed-image asserts in Build's `selfcheck.py` flipped | 12 |
| `R05_K2_K3_K4_defaults_diffusion.diff` | `air_lp` 0; source 2.6/1.2 (+ empty body, B 3.4/1.2); FDN-first faders, `early_wet` 1.0 enable; diffusion −0.25, clamp [−0.5, 0] | 15 |
| `R07_headroom_trim.diff` | `fdn.LOOP_LEVEL_TRIM_DB`: f2 −2.81 dB (both paths, lock only), f3 −1.70 dB (Play), f5 reserved | 4 |
| `R09_versions_and_build_tests.diff` | WORKLET_VER **34**, `live_fdn.js?v=34`, room_math 14, mic_desk 8, app 22; Build test pins 33 → 34; Build early-toys window 15 → 40 ms (K1) | 5 |
| `00_ALL_build_0929_to_p6.diff` | All of the above in one file | — |

## Apply

From `software\`, apply R01 → R03 → R04 → R05 → R07 → R09 with `patch -p1` (or apply `00_ALL` once). Then rebuild the wasm:

```
zig cc -target wasm32-freestanding -O3 -msimd128 -nostdlib -ffreestanding -Wl,--no-entry -Wl,--export-memory -Wl,--export=live_stereo -Wl,--max-memory=1073741824 -o static/wasm/live_stereo.wasm engine/live_stereo.c
```

## Checks

VERIFIED on the box, 1 Oct ~07:50 BST:
- **Patch chain:** both the chain and `00_ALL` apply cleanly to the snapshot and reproduce `p6` byte for byte, apart from the wasm.
- **Build's tests:**
  - `test_mic_colour_relative.py` 15/15.
  - `test_live_stereo.py` 13/13 (native .so).
  - `selfcheck` 44/44.
- **Package 3 suite:** 60 PASS / 2 FAIL / 22 XFAIL / 0 SKIP.
  - FAIL 1: two-source colour needs 146 entries against a cap of 128 (caused by K3's default source position).
  - FAIL 2: small-room 500 Hz T30 +10.6 %.
- **run_all:** 9 pass / 2 fail (t13, t18, which need F5) / 2 skip (goldens) / 5 pending.
- **Levels:** see `../results/levels/levels_p6_dm025_air025.log`. They are identical to p5, so the trim table is still valid with Build's version of F3.

`build_diff_0928_to_1001_for_reference.diff` is Build's own 28 Sep → 1 Oct change. It excludes the wasm and the 44100 tables and is for reading only.
