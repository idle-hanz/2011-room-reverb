# Structure findings (2026-09-10, with Pat + ens file)

## Verified navigation
- Ensemble opens; Structure via right-click **Instrument Structure** (EDIT helps).
- Path: `Instrument > Reflection Code > X Code` (and Y Code / Z Code).
- Inside X Code: a 1..16 **To V** distributor (leaf — will not open). Real math is sibling macros.

## Verified macro names (from ens + Structure)
Per-axis image helpers (inputs source axis + room size):

| Axis | Room port | Macros present |
|------|-----------|----------------|
| X | W | `X`, `-X`, `2W-X`, `2W+X`, `-2W+X` |
| Y | H | `Y`, `-Y`, `2H-Y`, `2H+Y`, `-2H+Y` |
| Z | L | `Z`, `-Z`, `2L-Z`, `2L+Z`, `-2L+Z`, **`4L-Z`** |

`4L-Z` exists only on Z (matches the extra +z face-centre room).

## Likely wired meaning (from names — not Core-opened)
Treat names as algebra on source coordinate S and room size R:

- `S` → S
- `-S` → −S
- `2R-S` → 2R − S
- `2R+S` → 2R + S
- `-2R+S` → −2R + S
- `4L-Z` → 4L − Z

This matches **corner-origin / classic mirror** tables more than a pure centre-origin `(-1)^n S + n R` expansion (those can coincide for some n after rewriting). **Operator graph inside `2W-X` still needs one Structure open** (or Core dump) to prove mul-by-2 vs other wiring.

## Prototype impact
Prototype default is now **corner** macro algebra with `origin="corner"|"centre"` switch (centre retained). Sub order / W full vs half still need Structure (`2W-X`). When Pat returns: one click — open **`2W-X` only**. See `/workspace/away-progress.md` (2026-09-15).

## Still unknown (need Structure or Core)
- Exact operators inside each macro
- How 32 voice indices pick which X/Y/Z macro
- Metres → samples
- Surface → image map; live Hadamard signs


## Delta — ens binary mining (2026-09-10)

See `/workspace/ens-mining-notes.md` for full tagged notes.

**NEW VERIFIED**
- Axis image macros contain Primary **Mul + Constant + Add/Sub**: Const **2.0** in `2W-X` / `2W+X` / `-2W+X` / `2L-Z` / `2L+Z`; Const **4.0** in `4L-Z`; `-X` is unary type `0x70`.
- Macro OutPort fan-outs yield **52** internal sink ids, each an (X-macro, Y-macro, Z-macro) triple; **`4L-Z` → id 109 only**; **`-Z` and `-2L+Z` have zero connections** (unwired).
- Distances and Delays embeds Constant **340.0** (no 343 / 44100 floats in file).
- Hadamard Matrix ×3 with V1–V32; Core Hadamard zlib has **no** readable ±1 float coefficients.

**Still open:** W full vs half; Sub input order; id→voice map; metres→samples law; live FDN copy.

## Prepare macro (Structure screenshot 2026-09-10 ~21:11)

Path: `Instrument > Prepare > Macro` (legacy RS SR for EventCell).

VERIFIED from on-screen Core/Primary graph:
- `Space/2` = `MSS * 0.5`
- `Mic Centre X` = `W * 0.5`
- `Mic Left X` = `Mic Centre X + Space/2`
- `Mic Right X` = `Mic Centre X - Space/2`
- `Mic Centre Z` = `L + MZ`
- `MLALR` = `(MDPC * 0.5) * (-0.25)`
- `MRALR` = `(MDPC * 0.5) * (+0.25)`
- `MLAUD` / `MRAUD` = constant `0`
- Y for mics = shared `MY` ("Mic + Sound Y") pass-through

LIKELY: room uses **corner origin** with centre at half-width (`W/2`), which aligns macro names `2W-X` with classic mirrors better than centre-origin `(-1)^n s + n W`.

## Units (user recall + file, 2026-09-13)

User: units differ in places; radians somewhere; degrees may fold into 0–1.

VERIFIED:
- Mic/Direct path port comment: **"Direction in radians of the incident sound"** (`Dir+`).
- Nested macro **`0-1-Degrees`** from `Rad-Degrees.mdl` (path under Drum Sequencer) — InPorts labelled **`0-1`**, OutPorts labelled **`Deg`**.
- Const **360.0** appears in that Degrees region (×4 file-wide) — LIKELY `turns(0–1) → degrees` via `*360`.
- Prepare mic toe: `MDPC * 0.5 * ±0.25` (Structure) — panel control folded into a small factor, **not** raw degrees.

LIKELY unit map:
- Incident direction into mic pattern: **radians**
- Some panel/angle paths: **0–1 turns** (full circle), converted toward Deg via Rad-Degrees / *360
- MDPC diverge/converge: **normalized 0–1** (or similar), not degrees

UNKNOWN: exact Rad↔Deg↔0–1 graph inside Rad-Degrees.mdl; whether cardioid uses cos(radians) directly.

## Delta — mic Dir+ / C/O / Res (2026-09-13 ~21:10 BST)

Full write-up: `/workspace/mic-core-findings.md`.

**VERIFIED**
- `Microphone` ×2 under Sound Proccessing: ports audio, `Dir+` (radians comment), `C/O4`, `Res` (“upper frequency limit”), audio out.
- Nested control macro `Dir`/`C/O` → `Gain`: `Dir→0x7a→Mul(×Const 2.0)` with `C/O` into unknown `0x7e`, then `Sub` from Const `1.0` → Gain ⇒ `Gain = 1 - Op(2·Trig(Dir), C/O)`.
- `MiF` = Microphone Response; panel Mic Response shows Hz-scale floats (10k/20k); `0x0156` value slot **1000.0**. Separate HP Freq / HP In on panel.
- No `2π` float in file; Primary trig units remain turns (manual); Gain has no in-macro unit converter.

**LIKELY**
- `0x7a` = Primary Sine (vs `0x82` Sine/Cosine).
- C/O blend intent matches prototype omni↔`(1+trig)/2` cardioid; exact `0x7e` algebra unproven.

**UNKNOWN**
- Identity of `0x7e`; Res sink `(7,0)`; shelf vs LPF for Res; whether `Dir+` numerics are turns despite “radians” comment.

**Prototype delta:** keep `(1+cosθ)/2` lerp; treat Res as Hz limit/shelf corner (not invented dB); don’t conflate with panel HP; verify Dir units before trusting Primary Sine.

## Delta — Structure screenshots batch (2026-09-16 ~15:11 BST)

Full write-up: `/workspace/structure-screenshots-batch.md` (6 PNGs opened). Screenshots (191)–(315) still offline.

**NEW VERIFIED**
- **Source Position:** Mouse Area `X,Y` → Event-Merger → Snap(**2**) → Event-Merger; `Db` → Value(**0.75**) + Value(**0.5**) into same merge; Snap(**1**) → out **X**.
- **Mic Stand:** Iteration **N=8**; Core outs **IDX/X1/Y1/X2/Y2/R**; side outs Height→3, Car/Omni→5, Mic Respon(HF)→6, HPF→7, HP In→8 (const 0); Mic Placement after Trig/Value bus (incl. color consts ~0.431372 / 0.0980392).
- **Mic Stand > Macro:** five **StpFltr**, shared **Tol=0.001**; map W→X, L→Y, Space→Spac, Angl→Angl, Dept→Dept; Core out **rr**.
- Nested: **legacy R5 SR** → Macro **Sr**; deepest Macro **`1/x`** (planar block + Depth) → **ry**.
- **Mic Stand > Core Cell:** **Mic Lenth** spelling; **Scaling** then Macro; **ry** via legacy R5 SR; outs **Idx, X1, Y1, X2, Y2, R**.

**LIKELY:** outer Core **Hr** ≡ inner **ry**; StpFltr Macro feeds that path; Scaling = unit normalize (factors unknown).

**UNKNOWN:** gray-block / `1/x` / Scaling formulas; Iteration→voice map; Source Position Z chain if any; (191)–(315) not on box.

## Delta — Structure screenshots batch 2 (2026-09-16 ~15:21 BST)

Full write-up: `/workspace/structure-screenshots-batch-2.md` (6 PNGs; #4 path typo-fixed).

**NEW VERIFIED**
- **Distances and Delays:** 3D Euclidean √(Δx²+Δy²+Δz²) for L/C/R; delay **`(d/340)*1000`**; consts **340** and **1000** on-screen; outs **TL/TC/TR**, **LDist/CDist/RDist**.
- **Listener ports in Distances:** **HLX/HLY/HLZ**, **HCX/HCY/HCZ**, **HRX/HRY/HRZ** (+ SX/SY/SZ); input index **7** skipped.
- **`aL` Macro** (`Distances and Delays > Macro`): Relay on `(I*0.25)==0` → **`aL = (0.5*M)−Z`** else **`aL = Z`**; Sub order plus=`0.5*M`, minus=`Z`; consts **0.25 / 0 / 0.5**.
- **Y Code:** macros **`2H-Y`**, **`2H+Y`**, **`-Y`**, **`Y`**, **`-2H+Y`**; inputs SY, H; **To V 19–52** + **`M`** collectors; `2H-Y` fans to many To V indices.
- **Z Code:** unambiguous macros **`Z`**, **`2L-Z`**, **`4L-Z`** (+ one L-macro with **obscured** label); **To V 19–52** into three **`M`** groups (15+10+9).
- Same Distances crop also shows **`? MLLR` / `? MRLR`**, three **`aL`**, **`0-1-Degrees`→Lamp**.

**LIKELY**
- Corner-origin / **full** H,L mirrors reinforced by `2H-Y`, `-2H+Y`, `2L-Z`, `4L-Z` naming (internals still unopened).
- Shared To V index across X/Y/Z Codes = one image triple.

**UNKNOWN / do not overturn**
- Exact Mul/Sub graph **inside** `2H-Y` / `2W-X` (not opened this batch).
- Obscured top Z-macro name — **do not** claim `-2L+Z` wired against prior ens “unwired” finding.
- Semantic map of `aL` ports I/M/Z beyond Structure labels; To V 1–18 layout.

## Delta — Structure screenshots batch 3 (2026-09-16 ~15:43 BST)

Full write-up: `/workspace/structure-screenshots-batch-3.md` (12 PNGs from ~15:16 and ~15:18; skipped already-mined batches + d301204a… settings).

**Priority:** Absorb **HIT**. Hadamard unlabeled only. **2W-X / 2H-Y / Scaling / 1/x** not opened.

**NEW VERIFIED**
- **Absorb Diffus Code:** serial **A Code→…→F Code**; In→A; each stage taps Out **A…F**; Mono/Compact.
- **A–F Code (each):** indexed **To V** writers — Event index (**V**) + **0|1** value; indices ~**18–52**; aggregate into **`M`** collectors (same visual family as Reflection collectors).
- **Surface Absor+Diffu:** Info *“Calculates each surface Absorption and Diffusion.”* Serial **Surface A…F** → Out; A–D use Freq/On/Mid|Widt/dB; E–F use **FrH/FrL**; Diffu = `×`/`+` tree over *Dif + **MDif** → **Clipper**.
- **Instrument topology:** Switch Surf/Floor/Seal/Wall → Controller → Absorb Diffus Code + Surface Absor+Diffu + Prepare + Reflection Code + Distances and Delays → Sound Processing → Mixer.
- **Direct Field** wraps **Legacy R5 SR for EventCell**; MLAUD/MRAUD unwired outwardly.
- **Direct Field > sqrt:** \(d_L=\sqrt{(SDX-MLX)^2+(SDZ-MLZ)^2}\), same for \(d_R\); `<` + selectors → **DD** (**2D XZ only**).
- **Prepare > Macro (this shot):** **SX = W × SoX(0–1)**; **SZ = MCZ + (L − MCZ) × SoZ**; **MLALR = MDPC×0.5 − 0.25**; **MRALR = 0.25 − MDPC×0.5**; M*AUD = 0.

**LIKELY**
- A–F **0/1 → To V** = **surface → image-voice mask** (opens prior “Surface → image map”).
- **DD** final = \(d_L + d_R\) (selector sort then add).
- Partial bit rows OCR’d for A–F (see batch-3); pattern-ish (e.g. F looks like repeating `01110` early) — **not** final.

**CONFLICT (do not overturn blindly)**
- This shot’s **Mic Centre Z** glyph reads **`*`** → **L × MZ**; prior Prepare notes claimed **L + MZ**. Flag until human confirms.
- Angle path here is **Add/Sub with ±0.25**, not prior **`(MDPC×0.5)×(±0.25)`**.

**UNKNOWN / still open**
- Exact full A–F bitmasks 18–52 (OCR soft).
- Labeled **Hadamard** / live ±1 signs; **2W-X / 2H-Y** leaf Mul/Sub order; Scaling / 1/x gray internals.

## Delta — Structure screenshots batch 4 full dump 191–315 (2026-09-17 ~07:11 BST)

Full write-up: `/workspace/structure-screenshots-batch-4-full.md` (125 PNGs; every-5th skim + ~90 deep-reads).

**Priority outcomes:** `2W-X` HIT · A–F bit tables HIT · Scaling HIT · labeled Hadamard HIT · Mic Centre Z still CONFLICT · surface→image partial.

**NEW VERIFIED**
- **`2W-X` leaf (207):** Mul Const **2** on W; Sub plus=`2W`, minus=`X` → **`(2·W) − X`**. Same leaf shape also under Room Dimensions (281).
- **X Code To V (206):** macros `X`, `2W-X`, `-X`, `2W+X`, `-2W+X` → repeating-5 map indices **17–52** (X→17,22,…52; 2W-X→18,23,…48; -X→19…49; 2W+X→20…50; -2W+X→21…51).
- **Y Code (208):** `2H-Y`, `2H+Y`, `-Y`, `Y`, `-2H+Y` → To V **19–52**; partial `2H-Y` fans documented in batch-4.
- **Z Code (209):** wired macros **`2L+Z`, `2L-Z`, `Z`, `4L-Z`** (clarifies batch-2 obscured label → **`2L+Z`**). Partial To V 19–33: 19–24←2L+Z, 25–28←2L-Z, 29–32←Z, 33←4L-Z. Still no `-Z` / `-2L+Z` on the wired panel (ens unwired claim stands).
- **A–F Code bit tables (196–201):** full **0|1** for To V **18–52** tabulated in batch-4 (E: treat 18–52 only; one OCR claimed 53 = UNKNOWN).
- **Surface Absor+Diffu (202–204):** serial A–F; A–D Peak EQ + invert vs Diffuser Delay (Delay=0 / Diff=0%); Diffu = masked sum × **MDiff** → Clipper.
- **FDN Hadamard (216–254):** labeled path; **32×32**; Voice = 8×(4-sums)→1×(8-sum); signs via gray **`-x`**. Gain **`In×(1/32)×Gain`** (218). Sample rows: V1 all+; many alternating +−; V3 `[+−−+]`; V5/23/31 `[++−−]`; V9 blocks of 8; etc. (see batch-4 table).
- **Distances (210–213):** reconfirm 3D √, `(d/340)×1000`, gray **`1/x` on 340**, **`aL` Relay** formula.
- **Mic Stand Scaling (314):** GUI factor **`min(8/M, 6/L)`** then × M→W, L, Space, Angle, Mic Lenth (display 10:7 / work 8:6) — **not audio**.
- **Microphones addresses (307–310):** L=17, C=21, R=25; write X1/Y1/X2/Y2 at Address+0..3.

**LIKELY**
- Corner-origin / full-W mirrors reinforced by opened `2W-X`.
- A–F masks + X/Y/Z To V = surface→image components; FDN V1–32 is a separate live bus from image indices ~17–52.
- Sylvester/Walsh–Hadamard construction from hierarchical summers + `-x`.

**CONFLICT (do not overturn blindly)**
- **Mic Centre Z:** early `L+MZ` vs batch-3 `L×MZ` (`*`) vs shot **191** reading `L−MZ`. Needs human pixel confirm.
- Mic angles: prefer Structure **Add/Sub ±0.25** after `MDPC×0.5` (batch-3/191) over early multiply form.
- Z fourth wired macro is **`2L+Z`**, not `-2L+Z` — does **not** overturn ens “`-Z`/`-2L+Z` unwired”.

**UNKNOWN / still open**
- Leaf graphs of **`2H-Y`, `2L-Z`, `4L-Z`, `2W+X`, `-2W+X`, `-X`** (only `2W-X` opened under Reflection).
- Full Y/Z → To V fan-outs; Distances gray **`1/x`** interior; complete 32-row Hadamard sign table (OCR-soft rows).
- Mic Centre Z operator; A–F letter → physical surface dictionary; FDN voice k ↔ image index i (if any).

## Delta — Structure screenshots batch 5 shots 316–350 (2026-09-17 ~07:43 BST)

Full write-up: `/workspace/structure-screenshots-batch-5.md` (35 PNGs; every file Read).

**Priority outcomes:** `2H-Y` **HIT** · Mic Centre Z **HIT** (CONFLICT settled → `L−MZ`) · `2W+X` **HIT** · `-2W+X`/`-X` **MISS** · bonus `2L-Z`/`4L-Z` **HIT** · Y/Z To V partial · Hadamard shell only.

**NEW VERIFIED**
- **`2H-Y` leaf (317):** Mul Const **2** on H; Sub plus=`2H`, minus=`Y` → **`(2·H) − Y`**. Same family as `2W-X`.
- **`2H+Y` (318):** Mul Const **2**; Add → **`(2·H) + Z_port`** (bottom InPort labeled **Z** on-screen; parent supplies SY — LIKELY port-name quirk).
- **`-Y` (319):** Invert **`-x`** → `Y = −SY`. **`Y` (320):** pass-through.
- **`-2H+Y` (321):** Sub plus=`Y`, minus=`2H` → **`Y − (2·H)`**.
- **`2W+X` leaf (330):** Mul Const **2**; Add → **`(2·W) + X`**. **`2W-X` (329)** reconfirms **`(2·W) − X`**.
- **Z leaves:** `2L+Z`=(2·L)+Z (**325**); `2L-Z`=(2·L)−Z (**326**); `4L-Z`=(4·L)−Z Const **4** (**328**); `Z` pass-through (**327**); `-2L+Z`=`Z−(2·L)` (**324**).
- **Mic Centre Z (331, 332):** Sub plus=`L`, minus=`MZ` → **`MCZ = L − MZ`**. Settles prior CONFLICT (`L+MZ` / `L×MZ` / `L−MZ`) in favor of **subtract**. Aligns shot 191 reading.
- Prepare reinforce: `SZ = MCZ + (L−MCZ)×SoZ`; Direct Field 2D XZ → DD (**333**); FDN Hadamard shell V1–32 (**348–350**).

**LIKELY**
- Full corner-mirror family now pixel-proven on Y and Z; X `-2W+X`/`-X` almost certainly match Y/Z analogs but **not opened**.
- Const **2** / **4** and Sub pin order pattern is universal for named `nR±S` macros.

**CONFLICT (settled / residual)**
- **Mic Centre Z: SETTLED VERIFIED = `L − MZ`.** Overturn early `L+MZ` and batch-3 `*`.
- Residual soft: Mic Left vs Right X Space/2 polarity and MDPC angle factor — descriptions disagree with early notes; **do not overturn** those yet.

**UNKNOWN / still open**
- Leaf interiors of **`-2W+X`**, **`-X`** (X Code).
- Full Y/Z → To V index tables (OCR conflict across cyan-selection shots).
- Whether `-Z`/`-2L+Z` feed main image To V 17–52 (macros exist; main panel still shows four wired macros only).

## Delta — Structure screenshots 351–354 (2026-09-17 ~08:25 BST)

**NEW / RECONFIRMED VERIFIED**
- **`-X` leaf (353):** path `Reflection Code > X Code > -X` — unary **`-x`** invert → **OUT = −IN**. Closes optional X-family leftover.
- **`2W+X` (352):** reconfirm **`(2·W) + X`**.
- **Direct Field / Prepare Macro (354):** path `Prepare > Macro > Direct Field`
  - Selected Sub: **Mic Centre Z = L − MZ** (reconfirms 331/332 settle).
  - **MLX = MCX − Space/2**, **MRX = MCX + Space/2**; MLY/MCY/MRY pass **MY**; MLZ/MCZ/MRZ share Mic Centre Z.
  - Angles: `Diverg Parallel Converge × 0.3 × (−0.25)` → **MLALR**; `× 0.3 × (+0.25)` → **MRALR**. MLAUD/MRAUD = 0.
  - **SX = Width × SoX**; **SY = MY**; **SZ = MCZ + (L − MCZ) × SoZ**.

**LIKELY**
- Shot 351 breadcrumb is `Y Code > 2H-Y` (already verified 317 as `(2·H)−Y`); leaf OCR this crop unreliable — do not overturn 317.

**STILL OPEN**
- **`-2W+X`** leaf still not opened (only remaining named X optional).

## Delta — prototype wired (2026-09-17 ~08:28 BST)

Wired `/workspace/early-field/` to Structure locks above (no invented Hadamard OCR rows, no A–F surface dictionary, no unproven coeffs).

**In code + README**
- Mirror leaves as named `macro_*` with full-R Sub/Add algebra; `corner_axis_from_macro` calls them; `(0,0,2)→4L-Z`.
- Prepare: `MCZ=L−MZ`, `MCX=W×0.5`, ML/MR X = MCX∓Space/2, angles `Diverg×0.3×±0.25`, source `SX/SY/SZ` formulas; CLI `--use-prepare`.
- Propagation: c=340, `delay_ms=(d/c)*1000`, geometric `1/r`; `dist` 3D for images; `dist_xz` for Direct Field DD.
- FDN: keep unscaled ±1 Sylvester (**ASSUMED** construction), g∈(0,1), no 1/√N.

**Selfcheck:** `test_verified_mirror_leaf_algebra`, `test_verified_prepare_mcz_and_mics`.

**Still ASSUMED / open:** `-2W+X` leaf interior; A–F→surface dict; full Hadamard sign table from Structure; FDN delay proposal; cardioid `0x7e`; peaking Q.

