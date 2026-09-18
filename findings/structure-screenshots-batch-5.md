# Structure screenshots batch 5 — shots 316–350 (2026-09-17 ~07:43 BST)

Ensemble: `20 October 2011 room reverb.ens` (Reaktor 6 Structure view).

**Coverage:** All 35 PNGs in `/workspace/structure-shots-316-350/` (Screenshot (316).png … (350).png). Every file Read; no skips.

Tags: **VERIFIED** = literally visible leaf algebra / labels · **LIKELY** = strong inference · **UNKNOWN** = not shown / OCR-unreliable · **CONFLICT** = prior disagreement settled or flagged.

---

## Priority target status

| Target | Status | Shots | Formula / note |
|--------|--------|-------|----------------|
| **`2H-Y` leaf** Mul const + Sub pin order | **HIT / VERIFIED** | **317** | `(2·H) − Y` — Const **2**; Sub plus=`2H`, minus=`Y` (same pattern as `2W-X`) |
| **Mic Centre Z in Prepare** | **HIT / VERIFIED** — CONFLICT **settled** | **331, 332** (+ aligns prior 191) | **`L − MZ`** — Sub; plus=`L`, minus=`MZ`. Overturns early `L+MZ` and batch-3 `L×MZ` |
| **`2W+X` leaf** | **HIT / VERIFIED** | **330** | `(2·W) + X` — Const **2**; Add |
| **`-2W+X` leaf** | **MISS** | — | Not opened. Y-analog **`-2H+Y`** and Z-analog **`-2L+Z`** opened (see below) |
| **`-X` leaf** | **MISS** | — | Not opened. Y-analog **`-Y`** opened (Invert `-x`) |
| Bonus **`2L-Z`** | **HIT / VERIFIED** | **326** | `(2·L) − Z` — Const **2**; Sub plus=`2L`, minus=`Z` |
| Bonus **`4L-Z`** | **HIT / VERIFIED** | **328** | `(4·L) − Z` — Const **4**; Sub plus=`4L`, minus=`Z` |
| Bonus Y/Z To V fan-outs | **PARTIAL** | 334–347 | Macro stacks confirmed; dense-wire OCR **conflicts** across selection shots — no full VERIFIED index table this batch |
| Bonus Hadamard rows | **PARTIAL HIT** | 348–350 | FDN shell + labeled **Hadamard Matrix** V1–32; no new per-row ±1 table beyond prior |

---

## Per-shot index (breadcrumb + content)

| Shot | Path / content | Tag |
|------|----------------|-----|
| **316** | Desktop / bot settings / file explorer — **no Structure** | skip |
| **317** | `Reflection Code > Y Code > 2H-Y` — leaf open | **VERIFIED** |
| **318** | `Reflection Code > Y Code > 2H+Y` — leaf open | **VERIFIED** (port label quirk) |
| **319** | `Reflection Code > Y Code > -Y` — Invert `-x` | **VERIFIED** |
| **320** | `Reflection Code > Y Code > Y` — pass-through | **VERIFIED** |
| **321** | `Reflection Code > Y Code > -2H+Y` — leaf open | **VERIFIED** |
| **322** | Breadcrumb claims `Z Code > -Z`; nested macros + To V — OCR soft | **UNKNOWN**/soft |
| **323** | `Z Code` overview (macros `2L+Z`, `2L-Z`, `Z`, `4L-Z` + To V) | **LIKELY** overview |
| **324** | `Reflection Code > Z Code > -2L+Z` — leaf open | **VERIFIED** |
| **325** | `Reflection Code > Z Code > 2L+Z` — leaf open | **VERIFIED** |
| **326** | `Reflection Code > Z Code > 2L-Z` — leaf open | **VERIFIED** |
| **327** | `Reflection Code > Z Code > Z` — pass-through | **VERIFIED** |
| **328** | `Reflection Code > Z Code > 4L-Z` — leaf open | **VERIFIED** |
| **329** | `Reflection Code > X Code > 2W-X` — reconfirm leaf | **VERIFIED** (matches 207) |
| **330** | `Reflection Code > X Code > 2W+X` — leaf open | **VERIFIED** |
| **331** | `Prepare > Macro` — Mic Centre Z Sub visible | **VERIFIED** |
| **332** | `Prepare > Macro` — Mic Centre Z + Sound Co-Ordinate Z | **VERIFIED** |
| **333** | `Prepare > Macro > Direct Field` — 2D XZ distances → DD | **VERIFIED** (reconfirm) |
| **334** | `Y Code` — To V 1–16 distributor view | partial |
| **335–341** | `Y Code` — macro stack + To V 17–52 selection fan-outs | partial / OCR conflict |
| **342–347** | `Z Code` — macro stack + To V fan-outs; `-Z`/`-2L+Z` also appear in some views | partial / OCR conflict |
| **348–350** | `Sound Processing > Feedback Delay Network` — Fr.V / Hadamard / To V | **VERIFIED** shell |

---

## 1. Leaf macros — VERIFIED algebra

### Priority 1 — `2H-Y` (317) ⭐

Path: `Instrument > Reflection Code > Y Code > 2H-Y`

- Ins: **H** (top), **Y** (bottom)
- Mul: **H × Const 2** → `2H`
- Sub: minuend = `2H`, subtrahend = **Y**
- Out: **Y** = **`(2·H) − Y_in`**

Matches verified `2W-X = (2·W) − X`.

### `2H+Y` (318)

Path: `Y Code > 2H+Y`

- Mul: **H × Const 2**
- Add: `(2·H) +` bottom-port
- Out: **Y**
- **Port label quirk:** bottom InPort reads **`Z`** on-screen (vision consistent across two Reads). Parent Y Code wires **SY** into that port (**LIKELY** reused/mislabeled port name; algebra is still add-of-source-axis). Report literal: **`Y_out = (2·H) + Z_port`**.

### `-Y` (319)

Path: `Y Code > -Y`

- Single In **SY** → Primary Invert **`-x`** → Out **Y**
- Formula: **`Y = −SY`**

### `Y` (320)

Path: `Y Code > Y`

- Pass-through In → Out **Y** (no Mul/Sub)

### `-2H+Y` (321)

Path: `Y Code > -2H+Y`

- Mul: **H × Const 2** → `2H`
- Sub: plus = **Y**, minus = `2H`
- Out: **`Y − (2·H)`** ≡ **`-2H + Y`**

### `2W-X` reconfirm (329)

Path: `X Code > 2W-X` — identical to shot **207**: **`(2·W) − X`**, Const **2**.

### Priority 3 — `2W+X` (330) ⭐

Path: `X Code > 2W+X`

- Mul: **W × Const 2**
- Add: `(2·W) + X`
- Out: **`X_out = (2·W) + X_in`**

### Bonus Z leaves

| Macro | Shot | Const | Op | Pin order | Formula |
|-------|------|-------|-----|-----------|---------|
| **`2L+Z`** | 325 | **2** | Add | `(2·L)` + Z | **`(2·L) + Z`** |
| **`2L-Z`** | 326 | **2** | Sub | plus=`2L`, minus=`Z` | **`(2·L) − Z`** |
| **`4L-Z`** | 328 | **4** | Sub | plus=`4L`, minus=`Z` | **`(4·L) − Z`** |
| **`Z`** | 327 | — | wire | pass-through | **`Z_out = Z_in`** |
| **`-2L+Z`** | 324 | **2** | Sub | plus=`Z`, minus=`2L` | **`Z − (2·L)`** ≡ **`-2L + Z`** |

**Pattern (VERIFIED family):**  
`2R−S` → Mul Const **2** (or **4** for `4L-Z`), Sub plus=product, minus=S.  
`2R+S` → Mul Const **2**, Add.  
`-2R+S` → Mul Const **2**, Sub plus=S, minus=`2R`.  
`-S` → Invert `-x`.  
`S` → pass-through.

### MISS this batch

- **`-2W+X`** interior (X Code) — not opened
- **`-X`** interior (X Code) — not opened  
  (Y/Z analogs above make the algebra **LIKELY** identical, but not pixel-verified for X.)

---

## 2. Prepare — Mic Centre Z CONFLICT settled

### VERIFIED — `Mic Centre Z = L − MZ` (331, 332)

Path: `Instrument > Prepare > Macro`

Both shots show a **Subtract** module labeled Mic Centre Z:

- Upper (+) pin ← **L** (Length)
- Lower (−) pin ← **MZ** (Mic Z)
- Result → **MCZ** / shared to **MLZ / MCZ / MRZ**

**CONFLICT resolution:**

| Prior claim | Disposition |
|-------------|-------------|
| `L + MZ` (early Prepare notes) | **Overturned** — Sub, not Add |
| `L × MZ` (batch-3 `*` glyph) | **Overturned** — Sub module visible, not Mul |
| `L − MZ` (shot 191 reading) | **Confirmed** by 331 + 332 |

Tag: **VERIFIED**.

### Also visible in Prepare (331 / 332) — reinforce / note

**VERIFIED / reinforced:**

- `Mic Centre X = W × 0.5`
- `Space/2 = MSS × 0.5`
- `MY` pass-through → MLY/MCY/MRY/SY
- `MLAUD` / `MRAUD` = Const **0**
- **Sound Co-Ordinate Z (332):** `SZ = MCZ + (L − MCZ) × SoZ` — matches prior batch-3/4
- **Direct Field (333):** 2D XZ √ for L and R; compare + switches → sum **DD** (reconfirm)

**CONFLICT / do not silently merge (secondary, not priority):**

- Shot **331** description of Mic Left/Right X pin order (`Left = MCX − Space/2`, `Right = MCX + Space/2`) **disagrees** with early notes (`Left = MCX + Space/2`, `Right = MCX − Space/2`). **Do not overturn** Left/Right X without a dedicated re-read; priority target was only MCZ.
- Angle path descriptions (331 `MDPC×0.3×±0.25` vs prior `MDPC×0.5` Add/Sub ±0.25) remain soft — prefer prior Structure Add/Sub form until pixel-confirmed.

---

## 3. Y / Z Code To V fan-outs (bonus — partial)

### VERIFIED macro stacks (parent level)

**Y Code** (335–341): inputs **SY**, **H**; macros **`2H-Y`**, **`2H+Y`**, **`-Y`**, **`Y`**, **`-2H+Y`** → To V → **M** collectors. Index range includes **17–52** (and some views show 1–16 separately, shot 334).

**Z Code** (323, 342–347): inputs **SZ**, **L**; wired image macros **`2L+Z`**, **`2L-Z`**, **`Z`**, **`4L-Z`** → To V **17–52** → **M**. Matches prior VERIFIED wired set.

### UNKNOWN / OCR conflict — full per-macro index tables

Selection-highlight shots (337–341 Y; 342–347 Z) give **mutually inconsistent** cyan fan-out index lists across Reads. One overview (336) claimed a clean **repeating-5** Y map analogous to X Code; other cyan selections show contiguous blocks. **Do not publish a VERIFIED full Y or Z To V table from this batch.** Prior partials (batch-2/4) stand until a clean highlight pass.

### Note on `-Z` / `-2L+Z` presence

Shots **322, 324, 344, 346** show **`-Z`** and/or **`-2L+Z`** as existing macros (324 opens `-2L+Z` leaf). Prior ens claim “`-Z` / `-2L+Z` unwired” referred to **OutPort fan-outs into the main image To V 17–52 triples**. Main Z Code overview still shows only **`2L+Z`, `2L-Z`, `Z`, `4L-Z`** on that panel — **do not overturn** “unwired from main image To V” without proof those negatives feed indices 17–52.

Shot **322** nested-content OCR is soft (conflicting labels `-4L+Z` / Hadamard claims) — treat as **UNKNOWN**.

---

## 4. Feedback Delay Network / Hadamard (348–350)

Path: `Instrument > Sound Processing > Feedback Delay Network`

**VERIFIED (shell):**

- In + Gain → `In` macro → Fr.V 1–16 / 17–32 columns
- Central labeled **Hadamard Matrix** with **V1–V32** in/out
- Matrix outs → **To V** → merge → **Out**
- Channels **17–32** visible in 350

No new complete ±1 row dump this batch (prior batch-4 rows stand).

---

## 5. What not to invent

- No invented algebra for unopened **`-2W+X`** / **`-X`**.
- No full Y/Z To V tables from conflicting OCR.
- Mic Left/Right X swap and angle factor soft readings **not** elevated to VERIFIED.
- Do not claim `-Z`/`-2L+Z` are now main-image-wired.
