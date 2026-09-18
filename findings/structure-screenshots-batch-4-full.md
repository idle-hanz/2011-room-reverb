# Structure screenshots batch 4 — full dump (191)–(315) (2026-09-17 ~07:11 BST)

Ensemble: `2011-room-reverb.ens` (Reaktor 6 Structure view).

**Coverage:** All 125 PNGs in `/workspace/structure-shots-191-315/` (Screenshot (191).png … (315).png). Systematic every-5th skim + deep-reads of priority targets and neighbors.

Tags: **VERIFIED** = literally visible leaf algebra / labels · **LIKELY** = strong inference from wiring/names · **UNKNOWN** = not shown / OCR-unreliable / conflicting · **CONFLICT** = contradicts prior notes without overturning blindly.

**Priority target status**

| Target | Status |
|--------|--------|
| 2W-X / 2H-Y / 2L-Z Mul const + Sub pin order | **HIT** — `2W-X` opened (207); same leaf pattern in Room Dimensions (281). `2H-Y` / `2L-Z` **not** opened as named macros this dump |
| A–F Code bit tables / To V 0|1 | **HIT** — full A–F tables (196–201) |
| Scaling / 1/x gray macros | **HIT** — Mic Stand Scaling (314); Distances `1/x` on 340 (210/212); AGC `1/SQRT(x)` (258/260) |
| Labeled Hadamard / FDN signs | **HIT** — labeled Hadamard Matrix; many Voice N rows with `-x` signs |
| Mic Centre Z Prepare (`*` vs `+`) | **CONFLICT remains** — operators disagree across shots; see §Prepare |
| Surface→image voice map | **Partial HIT** — X Code To V map + A–F masks + Z Code macros; Y full fan-out incomplete |

---

## 1. Reflection Code — X / Y / Z

### VERIFIED — Reflection Code shell (205)
- Path: `Instrument > Reflection Code`
- Parallel: **X Code**(SX,W) · **Y Code**(SY,H) · **Z Code**(SZ,L)

### VERIFIED — `2W-X` leaf algebra (207) ⭐
Path: `Reflection Code > X Code > 2W-X`

- Ins: **W** (top), **X** (bottom)
- Mul: **W × Const 2** → `2W`
- Sub: minuend = `2W`, subtrahend = **X**
- Out: **X** = **`(2·W) − X_in`**

Same Mul/Sub pattern also visible under Room Dimensions Core nested Macro (281): `(In1·2) − In2`.

### VERIFIED — X Code To V distributor (206)
Path: `Reflection Code > X Code`

Macros: **`X`**, **`2W-X`**, **`-X`**, **`2W+X`**, **`-2W+X`** (SX + W into each).

Repeating-5 fan-out (indices as labeled on To V):

| Macro | To V indices |
|-------|----------------|
| **X** | 17, 22, 27, 32, 37, 42, 47, 52 |
| **2W-X** | 18, 23, 28, 33, 38, 43, 48 |
| **-X** | 19, 24, 29, 34, 39, 44, 49 |
| **2W+X** | 20, 25, 30, 35, 40, 45, 50 |
| **-2W+X** | 21, 26, 31, 36, 41, 46, 51 |

Collectors: **M** merges. Note X Code includes index **17** (Y/Z codes start ~19).

### VERIFIED — Y Code overview (208)
Path: `Reflection Code > Y Code`

- Ins: **SY**, **H**
- Macros: **`2H-Y`**, **`2H+Y`**, **`-Y`**, **`Y`**, **`-2H+Y`**
- To V range **19–52** → **M** collectors
- Selected **`2H-Y`** fans (cyan) to at least: **19–23, 27–28, 36–37, 40–41, 45–46, 49–50** (other macros fill remaining slots — full per-macro table not fully OCR’d this pass)

### VERIFIED — Z Code overview (209) — clarifies obscured 4th macro
Path: `Reflection Code > Z Code`

- Ins: **SZ**, **L**
- Wired macros (all used): **`2L+Z`**, **`2L-Z`**, **`Z`**, **`4L-Z`**
  - **`Z`** takes **SZ only** (no L)
  - Others take SZ + L
- Partial To V (column 19–33):
  - **19–24** ← **2L+Z**
  - **25–28** ← **2L-Z**
  - **29–32** ← **Z**
  - **33** ← **4L-Z**
- Columns 34–52 continue interleaved fan-out (not fully tabulated)

### LIKELY
- Corner-origin / full-room mirrors reinforced: leaf `2W-X = 2W−X` proves **full W**, not half-W, in the named macro.
- Shared To V index across X/Y/Z = one image triple (unchanged).

### UNKNOWN / not opened this dump
- Named **`2H-Y`**, **`2L-Z`**, **`4L-Z`**, **`2W+X`**, **`-2W+X`**, **`-X`** interiors (only `2W-X` opened under Reflection Code).
- Complete Y-macro → index table; complete Z 34–52 table.

### CONFLICT note (Z naming)
- Prior ens: **`-Z` / `-2L+Z` unwired**. This dump’s Z Code shows **`2L+Z`** (not `-2L+Z`) as the fourth wired macro. **Does not overturn** “`-Z`/`-2L+Z` unwired” — those names still absent from the wired set. Clarifies batch-2 “obscured top Z-macro” → **`2L+Z`**.

---

## 2. Absorb Diffus Code — A–F bit tables

### VERIFIED — serial shell (195)
Path: `Instrument > Absorb Diffus Code`  
**A Code → B → C → D → E → F**; In→A; taps Out **A…F**.

### VERIFIED — bit tables To V 18–52 (value = Const 0|1)

#### A Code (196)
| Range | Value |
|-------|-------|
| 18–33 | 1 |
| 34–37 | 0 |
| 38–41 | 1 |
| 42 | 0 |
| 43–51 | 1 |
| 52 | 0 |

#### B Code (197)
| Range | Value |
|-------|-------|
| 18–23 | 0 |
| 24–39 | 1 |
| 40–45 | 0 |
| 46–50 | 1 |
| 51–52 | 0 |

#### C Code (198)
18:1, 19:1, 20:1, 21:0, 22:1, 23:1, 24:0, 25:1, 26:0, 27:1, 28:0, 29:1, 30:1, 31:0, 32:1, 33:1,  
34:1, 35:1, 36:0, 37:1, 38:1, 39:0, 40:1, 41:1, 42:1, 43:1, 44:1, 45:1, 46:0, 47:1, 48:0, 49:0, 50:0, 51:0, 52:0

#### D Code (199)
| Range | Value |
|-------|-------|
| 18–30 | 0 |
| 31–36 | 1 |
| 37–40 | 0 |
| 41 | 1 |
| 42–43 | 0 |
| 44–45 | 1 |
| 46–48 | 0 |
| 49 | 1 |
| 50 | 0 |
| 51–52 | 1 |

#### E Code (200)
18:0, 19–22:1, 23–24:0, 25–28:1, 29:0, 30–31:1, 32–33:0,  
34–35:1, 36:0, 37:1, 38–39:0, 40–43:1, 44–52:0  
(**Caution:** one OCR pass claimed index **53**; treat **18–52** as verified range; 53 = UNKNOWN.)

#### F Code (201)
| Range | Value |
|-------|-------|
| 18–40 | 1 |
| 41–42 | 0 |
| 43 | 1 |
| 44–45 | 0 |
| 46–48 | 1 |
| 49–50 | 0 |
| 51–52 | 1 |

### VERIFIED — Surface Absor+Diffu (202–204)
- Serial **Surface A…F** audio chain → Out
- A–D: Peak EQ path (Freq / On / Mid|Widt / dB); E–F: FrH/FrL
- Surface A info: absorbtion filtered, then **signal inversion** (`~x`) for reflection; Diffuser Delay present but Delay=0, Diffusion=0%
- Diffu bus: per-surface Dif × On, summed, × **MDiff**, → **Clipper**
- A/B may share On flag in some wiring views (OCR soft) — LIKELY pair for opposing walls

### LIKELY
- A–F 0|1 To V masks = **which image voices receive each surface’s absorb/diffus treatment** (surface→image map component). Combine with X/Y/Z Code To V for full triples.

---

## 3. Prepare / Direct Field / Mic Centre Z

### VERIFIED — Direct Field > sqrt (192)
- 2D XZ Euclidean for L and R; `<` + selectors → **DD** (confirms prior)

### VERIFIED — Prepare > Macro leaf coords (191 + batch-3)
Visible / reinforced:
- **SX = W × SoundX(0–1)**
- **SZ = MCZ + (L − MCZ) × SoundZ(0–1)**  (lerp from MCZ toward L)
- **MLALR / MRALR**: Add/Sub with ±0.25 after `MDPC×0.5` (not multiply-by-±0.25) — aligns batch-3
- **M*AUD = 0**
- Direct Field sub-macro: SDX/SDZ + ML/MR XZ → DD

### CONFLICT — Mic Centre Z operator (do not invent)
| Claim | Source |
|-------|--------|
| `MCZ = L + MZ` | Early Prepare notes |
| glyph `*` → `L × MZ` | Batch-3 Prepare shot |
| `MCZ = L − MZ` (Sub, L top / MZ bottom) | Shot **191** description |

**Status:** CONFLICT. Prefer a human re-read of (191) Prepare Macro; **do not pick** among `+` / `*` / `-` without pixel confirmation.

### VERIFIED — Latch / Legacy pass-through (193)
- Direct Field > sqrt > Latch wraps **Legacy R5 SR for EventCell**; exposes ML/MC/MR XYZ + angles + DD

---

## 4. Distances and Delays / aL / 1/x

### VERIFIED (210–213) — reconfirms prior
- 3D Euclidean HL/HC/HR; **`(d/340)×1000`**
- Gray **`1/x`** on Const **340** → then ×1000 (210, 212)
- Listener ports HL*/HC*/HR*; index **7** skipped in some numbering views
- **`aL`** Macro (213): `aL = ((i×0.25)==0) ? (0.5×M − Z) : Z` — Sub order plus=`0.5·M`, minus=`Z`
- ArcTan / SineCos / `? MLLR` / `? MRLR` / `0-1-Degrees`→Lamp still present

### UNKNOWN
- Interior of gray **`1/x`** Primary (not opened; only usage seen)
- Exact selector algebra for DD min/max vs sum (batch-3 LIKELY sum)

---

## 5. Sound Processing / FDN / Hadamard

### VERIFIED — Sound Processing shell (214)
- Air Absorption → three Diffuser Delay + Feedback Delay chains (DtL/C/R) → Microphone L/C/R

### VERIFIED — Feedback Delay Network (215–218)
- Fr.V / To.V around matrix; **live 32** channels
- Labeled **Hadamard Matrix** (216, 217, 219)
- **Gain** macro (218): **`Out = In × (1/32) × Gain`** (Const 1 / Const 32)

### VERIFIED — Hadamard architecture (219–223)
- Hadamard → Legacy RS SR for AudioCell → Macro with **Voice 1…32** columns
- Each Voice: 32 inputs → 8× (4-in summers) → 1× (8-in summer) → **V out**
- Signs via gray **`-x`** (unary negate) on selected inputs before summers
- No `1/√32` inside Voice rows (normalization at Gain `1/32`)

### VERIFIED — sample Hadamard row signs (selected Voices)

| Voice | Shot | Pattern (as labeled `-x`) |
|-------|------|---------------------------|
| **1** | 224 | **No `-x`** → all **+** (classic H row 1) |
| **2** | 225 | Repeating **`+ − + −`** (even negated) |
| **3** | 226 | Repeating **`+ − − +`** per quartet |
| **4** | 227 | Negate on pairs (3,4), (7,8), … |
| **5** | 228 | Repeating **`+ + − −`** |
| **6** | 229 | Alternating **`+ −`** |
| **7** | 230 | Alternating **`+ −`** (same family as 2/6/8/…) |
| **8** | 231 | Alternating **`+ −`** |
| **9** | 232 | Blocks of 8: `++++++++ −−−−−−−−` ×2 |
| **10** | 233 | Alternating **`+ −`** |
| **11** | 234 | Mixed quartet pattern (OCR detailed; treat as LIKELY until cross-check) |
| **13** | 236 | Mixed (see shot) |
| **14** | 237 | Alternating **`+ −`** |
| **18** | 241 | Alternating **`+ −`** |
| **23** | 246 | Repeating **`+ + − −`** |
| **28** | 251 | Block pattern with mid-row flips |
| **29** | 252 | Repeating **`++++ −−−−`** |
| **30** | 253 | Alternating **`+ −`** |
| **31** | 254 | Repeating **`+ + − −`** |
| **32** | 235 | Heavy negation; exact row = UNKNOWN without `-x` pin audit |

### LIKELY
- Sylvester / Walsh–Hadamard construction (hierarchical 4→8 summers + row `-x` patterns)
- FDN uses voices **1–32**; Reflection/Absorb To V **17/18–52** are a **separate** image-source indexing space (52 triples leftovers vs live 32)

---

## 6. Air Absorption / AGC / Scaling utilities

### VERIFIED — Air Absorption (256)
- Ins: In, Dis, Met → Humidity; filter P ← `Log(Humidity/Dis)`; amp path uses Order + **`1/x`** + Atten → Value → × LP out

### VERIFIED — AGC (258–260)
- Parallel Fr.V extraction; sum bus; gray **`1 / SQRT(x)`** (and/or `1/x`) → RMS-style gain
- To V 19–52 region also appears in AGC views (259) — AGC broadcast into some voice slots (23–33 noted)

### UNKNOWN
- Exact Humidity / Atten leaf formulas beyond Order/Value latch (257)

---

## 7. Controls / Room Dimensions / Mic Stand (GUI path)

**Note:** Letter-coded macros here (`A1,H1,D1`, opacity writers, etc.) are **panel/display** Core, **not** Absorb Diffus A–F audio masks.

### VERIFIED — Controls stack (266)
- Diffusion Matrix (FrR…Wet), Room Dimension (W/H/L), Source Position (SX/SZ), Mic Stand (MSS…Hp)

### VERIFIED — Room Dimensions Macro (276–277)
- **Output the large[st]**: max of three dims via `>` + selectors
- Volume ← Macro_out1 × Volume; Diffusion ← Macro_out2 × mean(dims) × Diffusion; mean = `(d1+d2+d3)/3`

### VERIFIED — Room Dimensions Core nested leafs (280–285, 281)
- `(x·4)−2`, `(x·4)−1`, `x·48`, plain `/`, and **`(In1·2)−In2`** (same shape as 2W-X)

### VERIFIED — Mic Stand Scaling (314) ⭐
Path: `Controls > Mic Stand > Core Cell > Scaling`  
Info: *"Scale of display is 10:7 and 1 and 0.5 borders… working area of 8:6"*

- Factor = **`min(8/M, 6/L)`** (via `/` + `>` + routers)
- Factor × {M→W, L, Space, Angle, Mic Lenth}

### VERIFIED — Mic Stand StpFltr / Core (296–301, 297)
- StpFltr Tol=**0.001**; W→X, L→Y; Iteration N=**8**; Mic Lenth spelling; dz const **0.2** on some Core views

### VERIFIED — Microphones address map (307–310)
- Mic Left Address **17**, Centre **21**, Right **25**
- Each writes X1,Y1,X2,Y2 at Address+0…+3

### VERIFIED — Microphones geometry Macro (311)
- Space/2; centre/left/right X from Width & Space (display coords — **do not conflate** with Prepare audio MCX=W/2)
- Depth labeled Mic Z; angle sub-macro → dX/dY

### LIKELY / OCR-soft — Angle dX/dY Macro (312)
- Uses Const **22**, **7**, **PI**, **0.5**, **−0.25**, `sin -pi..pi` / `cos -pi..pi`
- Exact combined formula OCR-unreliable — **do not invent**; re-open for leaf proof

### SKIP (already documented; no contradiction)
- Pure Mic Stand Iteration / Source Position Mouse Area duplicates (296 etc.) unless noted above

---

## 8. Surface → image voice map (synthesis)

### VERIFIED pieces
1. Per-axis image algebra macros → To V **~17–52** (X) / **19–52** (Y,Z)
2. Absorb A–F write **0|1** into same ~18–52 index space
3. Live FDN Hadamard is **V1–V32** (separate bus)

### LIKELY
- Index **i** selects one (X-macro, Y-macro, Z-macro) triple + A–F surface masks
- Live audio polyphony **32**; indices **>32** (up to 52) are leftover / unused triples (prior)

### UNKNOWN
- Exact A–F letter → physical surface (Front/Back/…) dictionary
- Complete Y and Z To V fan-out tables
- How FDN voice k relates to image index i (if at all)

---

## Shot triage log (abbreviated)

| Range | Dominant content |
|-------|------------------|
| 191–195 | Prepare / Direct Field / Absorb shell |
| 196–201 | **A–F Code bit tables** |
| 202–205 | Surface Absor+Diffu / Reflection shell |
| 206–209 | **X/Y/Z Code** (+ **2W-X** open) |
| 210–213 | Distances / aL |
| 214–255 | Sound Proc / FDN / **Hadamard Voices** |
| 256–265 | Air Absorption / AGC / `1/SQRT` |
| 266–295 | Controls / Room Dimensions / lettered GUI macros |
| 296–315 | Mic Stand / Scaling / Microphones / angle |

**Deep-read:** ~90 unique shots opened with Read (priority + neighbors).  
**Systematic skim:** every 5th of 125 (=25) plus adjacent opens.  
**Not pixel-audited:** remaining ~30–35 (mostly Hadamard Voice duplicates / Mic Stand duplicates).
