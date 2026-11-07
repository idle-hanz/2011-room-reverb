# PC0 — 610-A input calibration

Step 0 score only. Read-only ledger. No flux trim, no coefficient edit, no 9 kHz chase. The 2026-10-23 shelf stays for every edit. Idle lifted it for this file only.

HEAD `fd4a99aebac65f500e8411400eaa2c7527fd0808` (`fd4a99a` split render into two-source, still, and moving paths).

Gate: **PASS**. Both levels are numbers. Every link below is VERIFIED.

## Heard fault

The 610-A preamp distorts badly. Compressor sound and Neve are out of this score.

Backlog, next to this cause:

- Line 213: room bus after the 610 preamp peaked 301186 from 0.246 (+122 dB). A 0.246 probe with the flux coefficient at 0 peaked 5.23. No trim.
- Line 214: with phi_c 0 the peak is 5.23, still about +26 dB hot. The 610-A fix awaits Idle's OK.

This ledger does not re-score that probe.

## Suspected cause

The shaper sees the wrong level. The H2 unity scale hides it. One cause.

## The two levels

Drive 0, 1 kHz, 48 kHz, peak-1 input. 48 kHz is the fit rate (`prelib.py` line 8, `volterra.py` line 5).

| | Linear | dB re the input peak |
|---|---:|---:|
| Reference level, fit shaper input `x * G` | 161.466931945 | +44.162 |
| Internal shaper level, shipping `\|H1\|` | 686.053822727 | +56.727 |

`G` is `gain1k(klin_u610a)`: FFT bin 1365 at 999.755859 Hz, length-65536, roll −64. The same kernel summed at exactly 1000 Hz is 161.467408475.

Same input after the shared divide by `vc`:

| | Into the shaper `u` | dB re the input peak |
|---|---:|---:|
| Reference `G / vc` | 1112.84226208 | +60.929 |
| Internal `\|H1\| / vc` | 4728.33464287 | +73.494 |

The gap is +12.565 dB (`|H1| / G` = 4.24888126915). `vc` is the same on both sides, so the divide does not make the gap.

`vc_db` −16.76700034210179. Shipped linear `vc` 0.14509417681775544.

## Why the output does not show it

`pack_pre` multiplies H2 `b0 b1 b2` by `1/|H1*H2|` at 1 kHz. At 48 kHz that scale is 0.00598809978251131.

Raw `|H1*H2|` at 1 kHz is 166.997885192 (+44.454 dB), 0.293 dB above `G`. Raw `|H2|` is 0.243418052141 (−12.273 dB). H1 is left at +56.727 dB. After the scale the linear cascade is unity (0 dB). A level check at the output does not see the +12.565 dB the shaper sees.

`UAD_ROUND3_2026-10-19.md` line 165 says the low-order IIR was still to do. Line 167 is the fit note, and it has no H2 scale: Vc −16.77 dBFS, called input-referred, at drive 0 defined as the UAD mic gain where −57 dBFS in is the round 2 1 % point. This ledger is the first place that note and the H2 scale sit together.

## Links

1. **VERIFIED.** Shipping coefficients are `pre_choice.json` `u610a`, loaded by `bloom_dsp.py` `_DATA` lines 49–57 and `pack_pre` lines 742–743. SHA256 `b56b8e902205c08be59db892e9374b3e30147e80bc39f90737aa2be8a275f0a9` (807 bytes). `u610a.th.vc_db` is line 30. The same `vc_db`, `p0`, `p1`, `p2`, `phi_fc`, `phi_db`, and `phi_c` are the `nclip_flux` block in `prefit_u610a_nclip_emph_nclip_flux_nclip_emph_flux.json` lines 56–68. Family `nclip_flux`. `cfg` has `flux` and no `emph` (lines 25–28).

2. **VERIFIED.** `vc` in the pack is `10 ** (vc_db / 20)` at `pack_pre` line 754. Packed value 0.14509417681775544. It is pack index 3.

3. **VERIFIED.** Drive 0 stores `pre_drive_db` 0 at pack index 2 (`pack_pre` line 753). `_pre_bus` line 1052 sets `drive = 10 ** (0 / 20) = 1`. The input is multiplied by that drive, then H1.

4. **VERIFIED.** H1 is the first `u610a` row of `_PRE_SOS`, `bloom_dsp.py` lines 690–693. `pack_pre` lines 767–778 copy it and do not scale it. `b0` stays 111.20940456172353.

5. **VERIFIED.** Emphasis is off. `pack_pre` line 744 sets `emph` only when `cfg` has `emph`. Packed flag 0. `_pre_bus` lines 1078–1082 then leave `ue = v`.

6. **VERIFIED.** `_pre_bus` lines 1083–1084 divide by `vc`. Lines 1085–1097 run nclip and multiply by `vc`. Oversample is 8 (`pack_pre` line 745). Three halfband stages sit around nclip (lines 1088–1096). On a settled 1 kHz sine the amplitude into nclip matches `|H1|/vc` within 0.001 dB. The halfband does not move this level.

7. **VERIFIED.** The trailing divide by drive is `_pre_bus` lines 1114–1118. It runs only when `drive_db != 0`. At Drive 0 it does not run.

8. **VERIFIED.** Reference path is `prelib.py` lines 21–23 and 75–81. `G = gain1k(klin)`, `v = x * G`, then `u = v / Vc`. `PRE = 64` is `volterra.py` line 5. `kernels.npz` key `klin_u610a`, shape `(8256,)`, peak index 64 (8192 taps plus that delay). SHA256 `77d58672817c1e3bec0cc4b66b32a70a0f939ca3c7f59c7c1fe41835ca4ba8ff` (301630 bytes). `mk_kernels.py` line 4 is the writer. `real_eval.py` line 9 reloads that key.

9. **VERIFIED.** H2 scale is `pack_pre` lines 768–778, using `_cascade_gain_1k` lines 697–707. H2 `b0 b1 b2` are pack indices 20–22. `a1` and `a2` are not scaled. `_pre_bus` line 1113 runs that H2 on `v + d`.

10. **VERIFIED.** Render call order. `render_pipeline.py` lines 1370–1373 call `_route_buses` when an array or room spec is on, then `_apply_chain` when a bloom spec is on. `_route_buses` lines 1215–1216 run the array strips, then the room strips. Each call is `_apply_chain` (line 1211). `_apply_chain` lines 1176–1184 run the preamp (`amount_db` 0) and then the compressor when both are on. Otherwise one `apply_fdn_buses`. `apply_fdn_buses` line 956 builds `pack_pre`, and lines 990–995 call `_pre_bus` on L, C, and R.

## Reports read before the numbers

`round3/data` has no manifest. Read before any gain was written down: `pre_choice.json`, `real_meta.json` (excerpt RMS only), `prefit_u610a_nclip_emph_nclip_flux_nclip_emph_flux.json`, `pf_u610a_a.log`, `round3/progress.md`, and `UAD_ROUND3_2026-10-19.md`. None of them print `G` or `|H1|`. Those two levels come from `klin_u610a` and from `_PRE_SOS`.

## Left alone

No UAD recapture, no rerender, no REA install, no app launch. Empty MD5, centre MD5, the five goldens, `GOLDEN_META`, and `WORKLET_VER` 63 were not edited. This file is uncommitted.
