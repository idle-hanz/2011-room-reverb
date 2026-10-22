# Y/Z To V re-read (2026-09-19)

Vision re-read of Reaktor Structure screenshots — **not OCR**.  
Machine copy of the verified subset: `software/engine/to_v_tables.py` (**data only**, not imported by the renderer).

## Method (do not repeat the old cyan mistake)

Selecting a macro in Reaktor highlights **all** of its connections in cyan:

1. **Inputs** into the macro (SY/H, SZ/L) — ignore for the index table.
2. **Macro out → To V inputs** — these **are** the fan-out destinations.
3. **To V out → `M` collectors** — same indices again; **do not count as extra destinations**.

Earlier batch-5 “conflicts” mixed (2) and (3). This pass only records (2), and only when the numbered To V module is a clear landing.

Repeating-5 for **Y** (claimed from an unselected overview, shot 336) is **REJECTED**. Cyan block maps are the wiring.

## X Code — VERIFIED repeating-5 (206, restated)

To V **17–52**. Macros top-to-bottom: `X`, `2W-X`, `-X`, `2W+X`, `-2W+X`.

| Macro | To V indices |
|-------|----------------|
| **X** | 17, 22, 27, 32, 37, 42, 47, 52 |
| **2W-X** | 18, 23, 28, 33, 38, 43, 48 |
| **-X** | 19, 24, 29, 34, 39, 44, 49 |
| **2W+X** | 20, 25, 30, 35, 40, 45, 50 |
| **-2W+X** | 21, 26, 31, 36, 41, 46, 51 |

X Code crop starts at **17**. No 1–16 column on that panel.

## Y Code — range and verified subset

Shots **334** (scrolled to 1–16) and **335** (13–52): Y Code writes **To V 1–52**, not 19–52.

Macros top-to-bottom (208 / 336): `2H-Y`, `2H+Y`, `-Y`, `Y`, `-2H+Y`.

### VERIFIED (cyan → To V inputs)

| Macro | First-column To V | Shots |
|-------|-------------------|-------|
| **2H+Y** | 13, 14, 15, 16, 17, 18, 24 | 338 |
| **2H-Y** | 19, 20, 21, 22, 23, 27, 28 | 208, 337 |

First column 13–33 has 21 slots. Those two macros take 14. Remainder **25, 26, 29–33** belongs to `-Y` / `Y` / `-2H+Y` — **not split VERIFIED** (339–341 cyan overlaps on 29–32 vs collector wires).

### LIKELY only (not in the machine VERIFIED map)

Shot 337 cyan also lands on To V inputs **36, 37, 40, 41, 45, 46, 49, 50** from `2H-Y`. Stored as `Y_LIKELY_2H_Y_EXTRA`.

Y **1–12**: exist (334) but the selected-macro landing is off-crop in 338. Do not assign.

## Z Code — verified first column 19–33

Main panel macros (209 / 342–347): `2L+Z`, `2L-Z`, `Z`, `4L-Z`.

### VERIFIED (cyan → To V inputs)

| Macro | To V | Shots |
|-------|------|-------|
| **2L+Z** | 19–24 | 209, 342 |
| **2L-Z** | 25–28 | 209, 343 |
| **Z** | 29–32 | 209, 345 |
| **4L-Z** | **33 only** | 209, 347 |

19–33 is a complete 15-slot partition (6+4+4+1). Shot 347’s long cyan run past 33 is **33 → M**, not a second destination. Matches the ens note that `4L-Z` has a single sink.

Columns **34–52** still **UNKNOWN** as a full per-macro table (same collector-wire trap).

### To V 1–16 and negative Z macros

Shots **344** and **346** (scrolled up): To V **1–16** exist on Z Code. Macros **`-Z`** and **`-2L+Z`** sit in that region and have gold wires into it.

- They **exist** and are **not dead macros**.
- They are **not** on the main 17–52 panel (209 still shows only `2L+Z`, `2L-Z`, `Z`, `4L-Z` there).
- Do **not** overturn “unwired from main image To V 17–52” without a cyan landing on 17–52 from `-Z` / `-2L+Z`.
- Shot 346: passthrough **`Z`** also feeds some of 1–16 (cyan). 1–16 is a mixed bus — **not** a complete image-triple table (X Code does not write 1–16).

## What this does *not* unlock

- Live 32 of 52 triples still **UNKNOWN** (id→voice / To V→image-n).
- A–F 0\|1 masks still **not** in the audio path.
- FDN V1–32 is a **different** bus.
- `-2W+X` leaf is **VERIFIED** shot 402: `X − (2·W)`.

## Files

| File | Role |
|------|------|
| `software/engine/to_v_tables.py` | VERIFIED subset as data |
| `software/engine/absorb_masks.py` | A–F bits 18–52, still data only |
| `software/engine/voice_table_32.md` | older PROPOSAL 32-of-52 from ens sink ids — not replaced by this table |
