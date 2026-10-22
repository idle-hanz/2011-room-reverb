# Structure screenshots batch 2 — Reflection Code / Distances and Delays / aL (2026-09-16 ~15:20 BST)

Ensemble: `2011-room-reverb.ens` (Reaktor 6 Structure view).

**Coverage:** Six PNGs opened with Read. Image #4 path as given was missing; used typo-fixed hash  
`3e44c531400ccee64ec16b2826f29d78ee795c893b897ca0b86537245a35a36d.png`.

Tags: **VERIFIED** = literally visible · **LIKELY** = strong inference from wiring/names · **UNKNOWN** = not shown / not opened.

---

## 1. Reflection Code > Y Code

**Path:** `Panel > New > Instrument > Reflection Code > Y Code`

**File:** `9ea2a9f14674decc…7173e4.png`

### VERIFIED
- Inputs: **`1 SY`**, **`2 H`**.
- Five image macros (cube icons), top→bottom as shown:
  - **`2H-Y`** (selected / highlighted) — both SY and H
  - **`2H+Y`** — both SY and H
  - **`-Y`** — SY only
  - **`Y`** — SY only
  - **`-2H+Y`** — both SY and H
- Large **`To V`** sink array numbered **19…52** in three columns (~19–33 | 34–43 | 44–52).
- Selected **`2H-Y`** output fans out to multiple To V indices (clearly includes **19–22**, **34–37**, **44–46**; more wires continue).
- Far-right collector macros labeled **`M`** aggregate To V outs.

### LIKELY
- Macro names encode classic corner-origin mirrors with **full-room H** (not H/2): `2H−Y`, `−2H+Y`, etc.
- Same Y value shared across several To V indices (those images differ only in X and/or Z).

### UNKNOWN
- Exact Primary graph **inside** `2H-Y` / `-2H+Y` (Mul const, Sub pin order) — macros not opened in this shot.
- To V **1–18** (off this crop / other pane).

---

## 2. Reflection Code > Z Code

**Path:** `Panel > New > Instrument > Reflection Code > Z Code`

**File:** `555cb1dc6ca44797…5d46.png`

### VERIFIED
- Inputs: **`1 SZ`**, **`2 L`**.
- Four image macros visible (cube icons):
  - **`2L-Z`** — SZ + L
  - **`Z`** — SZ only
  - **`4L-Z`** — SZ + L
  - One additional L-using macro above `2L-Z` (label **partially obscured** in the shot)
- **`To V` 19…52** again in three columns; three right-side **`M`** collectors:
  - Top M ← To V **19–33** (15)
  - Mid M ← To V **34–43** (10)
  - Bot M ← To V **44–52** (9)
  - Total in this pane: **34** sinks (19–52).

### LIKELY (wiring from fan-outs)
- One L-macro → To V **19–22**
- **`2L-Z`** → To V **23–28** (and further cross-links into 34+)
- **`Z`** → To V **29–32**
- **`4L-Z`** → at least To V **33** (plus possible further)
- Cross-wiring into columns 34–52 from the same four macros (shared Z across image triples).

### Conflict / caution vs prior ens mining
- Prior verified: **`-Z` and `-2L+Z` unwired** in the ensemble.
- This pane’s top macro label is **partially obscured**; description tentatively read it as `-2L+Z`, but that would contradict prior mining if true.
- **Do not overturn** the unwired finding: treat the obscured name as **UNKNOWN** until a clearer open or Core dump. Visible unambiguous names here: **`Z`**, **`2L-Z`**, **`4L-Z`**.

### UNKNOWN
- Exact Mul/Sub graph inside each Z macro; To V 1–18; whether `-Z` / `2L+Z` appear off-crop or are absent here.

---

## 3. Distances and Delays (overview — L/C/R Euclidean + delay)

**Path:** `Panel > New > Instrument > Distances and Delays`

**File:** `e4fc90f2a44ba878…3151e.png`

### VERIFIED
- **Inputs (numbered):**
  - Source: **`1 SX`**, **`2 SY`**, **`3 SZ`**
  - Head Left: **`4 HLX`**, **`5 HLY`**, **`6 HLZ`**
  - Head Center: **`8 HCX`**, **`9 HCY`**, **`10 HCZ`** (index **7 skipped** in labels)
  - Head Right: **`11 HRX`**, **`12 HRY`**, **`13 HRZ`**
- Three parallel L/C/R branches:
  - Per-axis **Sub** → self-**Mul** (square) → **Add** of three squares → **Square Root** → distance
  - Distance outs: **`LDist` (2)**, **`CDist` (5)**, **`RDist` (8)**
  - Delay path: distance × (**1/340**) × **1000** → time outs **`TL` (1)**, **`TC` (4)**, **`TR` (7)**
- Yellow **Order** modules (1/2/3) gate/sequence the event path into the math.
- Lower section: **ArcTan**, **Sine/Cosine**, nested **`aL`** macros; output region includes **`HLLR`** (and related angle terminals).

### LIKELY
- Delay formula in ms: **`(distance / 340) * 1000`** (equivalent to `distance * (1000/340)`).
- Subtraction is source-vs-head on each axis (exact S−H vs H−S pin order not labeled on every Sub; Euclidean squares make sign irrelevant for distance).

### UNKNOWN
- Full azimuth/elevation algebra beyond “ArcTan of Δ ratios”; exact role of every Sine/Cosine pair.

---

## 4. Distances and Delays (second crop — R branch / angles / aL / lamps)

**Path:** `Panel > New > Instrument > Distances and Delays`  
(same macro; different crop / collage pane)

**File:** `3e44c531400ccee6…a35a36d.png` *(typo-fixed path)*

### VERIFIED
- Same Euclidean **Square Root** → distance / delay path; **`RDist`**, **`TR`** visible on the right-hand branch.
- Input stack includes **`13 HRZ`** (and Order 1/2/3 stacks).
- Multiple **ArcTan**, six **Sine/Cosine** (three pairs), **three nested `aL`** instances.
- Angle-ish terminals labeled **`? MLLR`**, **`? MRLR`** (question-mark port style in Structure).
- Two **`0-1-Degrees`** macros → **Lamp** modules (panel feedback).
- One `aL` chain feeds a terminal toward **`dL`** (label as read on crop).

### LIKELY
- MLLR / MRLR are mic/listener left–right angle quantities (naming mixes **M** with the **HL/HC/HR** distance ports).
- `0-1-Degrees` here matches the earlier Rad-Degrees / turns→degrees unit path (see prior findings).

### UNKNOWN
- Exact wiring of Mul-by-**2** modules near Order stacks (visible const **2**, role not fully traced in this crop — **not** proof of image-macro `2W-X` internals).

---

## 5. Distances and Delays (third crop — consts 340 / 1000 explicit)

**Path:** `Panel > New > Instrument > Distances and Delays`

**File:** `ad31a27a1d200614…c232.png`

### VERIFIED
- Same SX/SY/SZ + HL/HC/HR input set as §3.
- Constant module **`340`** (also referenced as DD-region const) → **`1/x`** → Mul with distance → Mul by **`1000`** → **`TL` / `TC` / `TR`**.
- Distance terminals **`LDist`**, **`CDist`**, **`RDist`** again.
- Nested **`aL`**; ArcTan / Sine/Cosine present; terminal near bottom-right includes **`? HL_R`**-style label (as read).

### Confirms focus Q2
- **Euclidean** distance: **VERIFIED**
- **`c = 340`**, ms factor **`1000`**: **VERIFIED** on-screen (matches binary mining)

---

## 6. Distances and Delays > Macro (`aL`)

**Path:** `Panel > New > Instrument > Distances and Delays > Macro`  
(output terminal **`aL`**)

**File:** `d59eef96b3c2b56a…9299f.png`

### VERIFIED — exact nested `aL` logic
**Ports:** In **`I`**, **`M`**, **`Z`** → Out **`aL`**.

**Graph:**
1. **`I * 0.25`** → **Compare / Eq** vs constant **`0`** → Relay **`Ctl`**
2. **`M * 0.5`** → **Sub** with **`Z`** on the minus pin → **`(0.5 * M) − Z`**
3. **Relay:**
   - Input **`1`**: `(0.5 * M) − Z`
   - Input **`0`**: raw **`Z`**
   - Out → **`aL`**

**Hence (Relay semantics as labeled 1/0):**
- If **`(I * 0.25) == 0`**: **`aL = (0.5 * M) − Z`**
- Else: **`aL = Z`**

**Constants visible:** **`0.25`**, **`0`**, **`0.5`**.  
**Sub order VERIFIED:** plus = `0.5*M`, minus = `Z`.

### LIKELY
- Port **`I`** is an index/flag (zero → special centre/half-M path); **`M`** a room or mic span; **`Z`** a coordinate or depth term — semantic names not printed beyond I/M/Z.

### UNKNOWN
- Parent meaning of I/M/Z wires into this Macro (need parent wire labels beyond the three Distances crops).

---

## Focus-question scorecard (this batch)

| # | Question | Status | Evidence |
|---|----------|--------|----------|
| 1 | Exact algebra inside `2H-Y` / `-2H+Y` / `2W-X` | **UNKNOWN** (internals not opened). Names + prior binary Const **2.0** still stand. | Y Code / Z Code show wrappers only |
| 2 | Distances Euclidean? delay? 340 & 1000? | **VERIFIED** Euclidean; **`ms = (d/340)*1000`**; both consts on-screen | §§3–5 |
| 3 | `aL` nested exact logic | **VERIFIED** Relay + `0.25` / `0.5` as above | §6 |
| 4 | Reflection Code X/Y/Z → 3D images; To V | **VERIFIED** pattern: per-axis macros → shared **To V n** (n=19…52 here) → **`M`** collectors. Combination = same index across X/Y/Z Codes. | §§1–2 |
| 5 | HL/HC/HR vs ML/MC/MR | **VERIFIED** Distances ports are **HL/HC/HR**. Separate **MLLR/MRLR** (and prior Prepare **Mic***) also exist — dual naming. | §§3–5 |
| 6 | Corner-origin / W-full vs half | **LIKELY** reinforced: `2H-Y`, `-2H+Y`, `2L-Z`, `4L-Z` use **full** H/L; Prepare already has Mic Centre X = W*0.5. **Still UNKNOWN** Sub order inside image macros. | §§1–2 + prior Prepare |

---

## Top new facts (for parent)

1. **`aL` opened:** `aL = ((I*0.25)==0) ? (0.5*M − Z) : Z` with Relay 1/0 — consts **0.25 / 0.5** VERIFIED.
2. **Distances and Delays Structure confirms** Euclidean √(Δx²+Δy²+Δz²), **`340`**, **`1000`**, outs TL/TC/TR + LDist/CDist/RDist.
3. **Receiver ports in Distances = HL/HC/HR** (not ML/MC/MR); index **7** unused in that input list.
4. **Y Code / Z Code** distribute image coords to **To V 19–52** (34 sinks) via **`M`** collectors; **`2H-Y`** (and Z macros) fan one formula to many To V indices.
5. Image-macro **internals** (`2H-Y` Mul/Sub) still **not** screenshot-proven this batch — need open `2W-X` / `2H-Y` leaf.
