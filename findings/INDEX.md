# Findings index

Copies and pointers for Structure / batch notes used by the 2011 rebuild.

## In this folder

| File | Summary |
|------|---------|
| `structure-findings.md` | Master log: verified macros, Prepare, Distances, Absorb, FDN, conflicts settled (`MCZ = L−MZ`), prototype wire-up. |
| `structure-screenshots-batch.md` | Batch 1 (~15:11 BST 2026-09-16): Source Position, Mic Stand, Scaling / `1/x` unknowns. |
| `structure-screenshots-batch-2.md` | Batch 2: Distances 3D + `(d/340)×1000`, Y/Z Code macros, `aL` Relay. |
| `structure-screenshots-batch-3.md` | Batch 3: Absorb A–F codes, Surface Absor+Diffu, Direct Field 2D XZ, Prepare conflict flags. |
| `structure-screenshots-batch-4-full.md` | Batch 4 (191–315): `2W−X` leaf HIT, A–F bit tables, Hadamard shell, Scaling GUI factor. |
| `structure-screenshots-batch-5.md` | Batch 5 (316–350): `2H−Y` family, `MCZ=L−MZ` settle, Z leaves, `2W+X`. |
| `structure-screenshots-batch-6.md` | Batch 6 (358–399): Diffusion Matrix **Sides/Ahead/Behind/Floor/Ceiling**, panel snapshot, GUI stem `dX/dY`, Voices 32. |
| `af-bit-tables-reverified.md` | Vision re-read of A–F To V 18–52. **A and F OCR in batch-4 were wrong.** Not wired into audio. |
| `yz-to-v-reverified.md` | Vision re-read of Y/Z To V. X repeating-5 restated; Y/Z first-column subset VERIFIED; repeating-5 Y rejected. Data only. |
| `mic-one-pole.md` | Mic Gain `1-(2·|Dir|)^C/O` (466). Log F→P(Res)×Gain → 1-pole on delay **out** (410). Not in Hadamard loop. |
| `live-32-images.md` | Ordered poly voices 1–32 from SX/SY/SZ + Dis. 29 unique; no ±2W; no −Z; `2L+Z` not `4L−Z`. |
| `air-absorption.md` | Air Abs amp = `1/r²`. 1-pole `fc=Wet/Dis` (256) plus ASSUMED high-shelf upgrade. |
| `distance-and-angle.md` | Image delay = 3D Euclidean √(sum of squares). Angle is the long ΔX/ΔZ ArcTan stack; polar only needs the XZ dot-product cosine. |
| `fdn-loop.md` | Diffuser Delay = the delay lines; Hadamard mixes/inverts and feeds back into the `+` (473 both summands cyan). Desktop: L/C/R loops + Mixer fold; Render RMS / Play live AGC. |
| `structure-screenshots-batch-10.md` | Shots 466–476: Power `X^Y` + \|Dir\|; Fr.V = voice picker; Diffuser Delay built-in allpass; **Max Delay 1000 ms**. |
| `dffs-allpass.md` | Dffs = `Dis × Dff × (1/Diffusion)` (462–465). 202.633 is 1/x **in**. Schroeder allpass on Diffuser Delay. |
| `diffusion-two-layers.md` | Surfaces jitter `Δd` (ASSUMED, already in app) vs 2011 Dffs allpass (VERIFIED module). Do not unify without a go. |
| `instrument-path-map.md` | Instrument spine Prepare→…→Mixer. Mixer 477 = L+0.5·C, no delay. Distances→Mixer REJECTED. |
| `mixer-agc.md` | Mixer Voice Combiner + Receive **RMS Volume** (478–482). AGC On = `√(Σ 1/r²)` (256+260). Desktop IR RMS ASSUMED. |
| `structure-screenshots-batch-7.md` | Shots 402–419: `-2W+X` HIT; Prepare ±0.25 **Add**; Mic Power (x^y); Distances debug 32-voice. |
| `structure-screenshots-batch-8.md` | Shots 420–433: Distances chain Δ→√→`/340`→×1000; SX clusters X / 2W−X / −X. |
| `structure-screenshots-batch-9.md` | Shots 434–465: SY/SZ/mic InPorts; **Dly = image delay_ms** (460). |
| `screenshot-catalog.md` | Every Pictures screenshot **138–486** classified. |
| `ens-binary-notes.md` | Read-only mine of the `.ens`: author comment (32 voices / Puckette FDN), named macros including `-2W+X`, Const **340**, **no 1/√N**, no `DffC`. |

Start-of-session file (parent folder): [`../HANDOVER.md`](../HANDOVER.md).

## Related notes still on the box (not all copied)

| Path on box | Topic |
|-------------|--------|
| `/workspace/ens-mining-notes.md` | Ens binary mining (340 Const, 52 sink ids, Hadamard zlib). |
| `/workspace/mic-core-findings.md` | Mic Dir+ / C/O / Res Core graph. |
| `/workspace/2011-reverb-overnight.md` | Overnight design agreement. |
| `/workspace/2011-morning-handoff.md` | Morning handoff. |
| `/workspace/2011-rebuild-checklist.md` | Rebuild checklist. |
| `/workspace/away-progress.md` | Away-day progress (corner default). |
| `/workspace/non-cubic-rooms.md` | Non-cubic discussion. |
| `/workspace/shared-room-sketch.md` | Shared room sketch. |
| `/workspace/grid-scaling.md` | Grid scaling notes. |

## Rule

Prefer VERIFIED Structure algebra. Do not invent A vs C Left/Right (Sides is one panel) or full Hadamard OCR rows into audio code. A–F **names** B/D/E/F are panel-verified; bit tables live in `software/engine/absorb_masks.py` as data only. Y/Z To V verified subset lives in `software/engine/to_v_tables.py` — also data only.
