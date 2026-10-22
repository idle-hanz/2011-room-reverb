# BLOOM RETRY 3 — STOP 2026-10-22

CPU gate failed. The tree is restored from `software_backup_2026-10-22_preBLOOMRETRY3.zip`. Current pin stays UI-TIDY-1. `WORKLET_VER` stays 59. `app.js?v` stays 63. No listen wavs were written.

Idle overrides for this run: Room Crush 2x and Room Crush alone on the alias gate; other presets report worst-image dBc only; re-apply `ls_ln` with mask 2047; report the 610-A spike and do not fix it. Ceiling stays 2.40 ms.

## Stop

**RT-4 CPU. STOP.** Idle re-bench, decay-8 cube, shared off, two sources, Surfaces, predelay 4799, Drive +24, Neve `nclip_flux` 8x, 4 warmup + 12 rounds. Blob checked first: bloom length 65, colour OS 2, pre length 25, pre OS 8.

| Case | Median | p90 | Silence-late median | Spikes |
| --- | --- | --- | --- | --- |
| Natural 2x + Neve 8x | 2.805 ms | 2.842 ms | 2.747 ms | 0 |
| Room Crush 2x + Neve 8x | 2.790 ms | 2.847 ms | 2.956 ms | 0 |

VERIFIED over 2.40 ms. The ceiling was not raised. A first pass overlapped the alias render (Natural p90 4.662) and was discarded. The table is the idle repeat. `play_spikes` is 0 because a spike is a block over 3× the median (about 8.4 ms). The first play window still has one block at 8.122 ms (Natural) and 8.223 ms (Room Crush). Later window maxima sit between 4.56 and 4.78 ms. The floor itself is about 2.8 ms, so the miss is not a few spikes.

The 2026-10-22 wired-tree json recorded Natural + Neve 8x at median 2.209, p90 2.246, silence-late 2.381. That wasm was not re-run on this boot. Why today's idle number is about 0.6 ms higher is UNKNOWN.

## What passed, then was reverted

**RT-2.** VERIFIED on the edited Python. Gated presets Nuke, Room Crush, Swell: worst |dGR|, |dRMS|, |dPeak| over the last 0.5 s was 0.0 dB on all 48 rows (printed to 4 decimals, so under 0.00005 dB). Natural and Glue were the same 0.0 and were not gated. Nuke 7 kHz 0 dBFS pilot before the full set: mean dGR 0.0, max 0.0.

**Room Crush alias.** VERIFIED on the scratch tap wasm (`%TEMP%\bloom_rt2\live_stereo_tap.wasm`, sha1 `db4c40efd1939db12433b7abd346b84a17155079`, 376486 bytes), FIR47 at 2x, after makeup and EQ, same scorer as the stop. 0 of 16 failed. Worst gap +0.073 dB at 9 kHz, −24 dBFS: ours −63.527 dBc, UAD −63.6 dBc. Gate was UAD worst + 0.5 dB.

**Other worst images, report only, not a gate.** Same scratch wasm.

| Preset | Fails | Worst gap | Row | Ours dBc | UAD dBc |
| --- | --- | --- | --- | --- | --- |
| Natural 2x | 15/16 | +32.113 | 13 kHz 0 | −71.987 | −104.1 |
| Glue ADAA | 16/16 | +21.289 | 17 kHz −12 | −78.111 | −99.4 |
| Swell 2x | 16/16 | +44.273 | 9 kHz 0 | −63.527 | −107.8 |
| Nuke ADAA | 6/16 | +51.700 | 13 kHz −24 | −89.700 | −141.4 |
| Neve 8x | 8/16 | +21.826 | 17 kHz −6 | −43.674 | −65.5 |
| 610-A 8x | 14/16 | +89.964 | 9 kHz −6 | −24.436 | −114.4 |

**Sound pins.** VERIFIED before the restore: `test_quick_pins.py` and `test_physdefault_two_source.py`, 6 passed. Empty MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88`. Centre `b3e6bcd9dfa13ad737d2b15d561f7d30`. After the restore, those two plus `test_bloom_off.py`: 8 passed.

**Selfcheck.** 45/45 on the edited tree and again after the restore.

`ls_ln` was re-applied as `e = (int)((v.u >> 52) & 2047) - 1023` and then reverted with the tree. The restored inc is the 10-bit mask again, and `live_stereo.c` does not include it.

## 610-A spike (not fixed)

VERIFIED. 9 kHz, 0 dBFS, 1 s, Drive 0, once-trimmed H2. Python `_pre_bus` peak 2643.92 at sample 95 (+68.445 dB). Tail peak 2.49935 (+7.957 dB). The scratch C tap matches: 2643.95 at sample 95 (+68.445 dB), tail 2.475.

The spike is the flux cubic on H1's output. It is not a second 1 kHz divide and it is not nclip.

- Packed row: OS 8, emphasis flag 0, `af` 0.974183, `Vphi` 0.325227, `phi_c` −0.041303, `mem_m` 0.
- `phi_c` set to 0: Python peak −8.673 at sample 52 (+18.763 dB). C peak −8.639 at sample 52. The sample-95 spike is gone.
- Nclip output forced to 0, flux left on: peak 2649.98 at sample 95 in Python and in C. The spike stays, and it is slightly larger.
- Both removed: peak −0.8945 at sample 15, −0.968 dB, the linear 9 kHz gain.
- Emphasis is already off. Clearing the flag changes nothing.
- H1 alone peaks at 154.509 (+43.779 dB) at sample 2. The output spike is not that linear peak.
- The burst is about 101 samples wide above half the peak, not one sample.

LIKELY: H1 is untrimmed, so the one-pole into the cubic sees about +44 dB. Flux divides the cubic difference by `(1-af)` ≈ 0.0258, and the one-pole state starts at 0. `af` 0.974 has a time constant of about 39 samples. The peak at sample 95 is that charge on a 9 kHz sine. Not isolated sample-by-sample inside the flux state. Do not add `y /= g`.

Small-signal trim still holds. 1 kHz at −100 dBFS, tail gain 0.0 dB. At −40 dBFS the same 1 kHz tail is +5.15 dB, and at 0 dBFS it is +84.09 dB, because the flux is still in the tail. The 9 kHz level sweep: −100 dBFS is linear (−0.968 dB, index 15); −40 is +3.677 dB at index 580; −12 is +44.317 dB at index 95; 0 dBFS is +68.445 dB at index 95.

## Restore

VERIFIED. Zip `software_backup_2026-10-22_preBLOOMRETRY3.zip`. Manifest `PIN_MANIFEST_preBLOOMRETRY3.txt`: 247 files, 0 mismatches. The nine files only in the RETRY2 zip are pytest cache. Listen wav sha1 `7365f08b96981de3b7d0085de7117382471564e9`, 86032844 bytes. Survivors outside the zip: none.

| File | sha1 | Bytes |
| --- | --- | --- |
| `software/engine/live_stereo.c` | `bbdf57994e0996e2c9b77eb8a634550bb71ef3cf` | 136434 |
| `software/static/wasm/live_stereo.wasm` | `843a6eb8c91a9278ba927f643481f3260766a08c` | 279668 |
| `software/engine/bloom_dsp.py` | `ab1f3c4b87044edecb921f72e46e0e74f2366c12` | 34475 |
| `software/engine/bloom_live.inc` | `ebb0e2c0860070415010ca8aa68374efdcd60323` | 15414 |
| `%LOCALAPPDATA%\Temp\live_stereo.dll` | `181d05cd0616b63c061e72b27900f4c4c331fcc3` | 285184 |

The DLL was rebuilt with `python -m ziglang cc -shared -O3` straight to `live_stereo.dll` from the restored C. Room Crush is 1x again. `ls_ln` mask is 1023 again.
