# Structure screenshots batch — Mic Stand / Source Position (2026-09-16)

Ensemble: `2011-room-reverb.ens` (Reaktor 6 Structure view).

**Coverage note:** These six PNGs are on the box and were opened with Read. User-listed Windows paths Screenshot (191)–(315) are **not** on the box (PC offline) — gap remains.

Tags: **VERIFIED** = visible in screenshot · **LIKELY** = strong inference from wiring/names · **UNKNOWN** = not shown.

---

## 1. Controls > Source Position

**Path:** `Panel > New > Instrument > Controls > Source Position`

**File:** `736bd19a…29ff.png`

### VERIFIED
- **Mouse Area** outputs used: `X`, `Y`, `Db` (double-click).
- `X` and `Y` → **Event-Merger (M)** → **Snap Value** with constant **2** on the snap/resolution port.
- That Snap Value → second **Event-Merger**.
- `Db` → **Trig** of two **Value** modules: constants **0.75** and **0.5**; both Value outs → second Event-Merger.
- Second Event-Merger → second **Snap Value** with constant **1** on snap/resolution → output terminal **X**.
- Floating constant **1** near final output (role not fully clear from shot).

### LIKELY
- Snap constants **2** / **1** are the same “Z=2, X=1” click/snap steps noted in conversation (labels not unambiguously read as Z/X on this crop).
- Double-click Values **0.75** / **0.5** are reset/default positions injected into the same merge chain as mouse XY.

### UNKNOWN
- Exact meaning of the floating `1`; whether a parallel Z output chain exists off-crop; full Source Position Y/Z terminals if any.

---

## 2. Controls > Mic Stand (parent)

**Path:** `Panel > New > Instrument > Controls > Mic Stand`

**File:** `e295cdf4…28a7.png`

### VERIFIED
- **Iteration:** `N = 8`, `Inc = 1`, `In = 1`; index `i` → Core Cell **Mic**; `Out` → **Order**.
- **Core Cell** (outer view) inputs include: **Hr**, **W**, **L**, **Spac**, **Angl**, **Dept**, **Mic**, plus a constant **0.2** on one port.
- Core Cell outputs: **IDX**, **X1**, **Y1**, **X2**, **Y2**, **R**.
- **Mic Placement** macro after Core (via Trig/Value fan-out): inputs include `Mic`, `Obj`, `X1`, `Y1`, `X2`, `Y2`, `R`, `G`, `B`, `LW`, `XO`, `XR`, `YO`, `YR`; outputs `NP`, `NO`, `M`, `H`.
- Color-ish constants into Value chain: **0.431372**, **0.0980392**; also **1**, **-1**, **-0.5**, **10**, **7**; constant **2** into a Value → Mic Placement `Mic`.
- Discrete right-side controls → instrument outs:
  - **Height** (internal `Y`) → out **3**
  - **Car/Omni** (internal `Car`) → out **5**
  - **Mic Respon** (internal `HF`) → out **6**
  - **High Pass F** (internal `Hpf`) → out **7**
  - **HP In** (internal `Hp`) → out **8** (constant **0** shown)
- Top-left: macro path taking **W, L, Space, Angl, Depth**; another block exposing **Hr, Spac, Angl, Dept** (Hr → Core).

### LIKELY
- `0.431372` / `0.0980392` are RGB panel-draw colors for Mic Placement (≈110/255, 25/255).
- Outer Core port **Hr** is the same quantity as inner **ry** after boundary rename (see §6).
- Outer **Mic** + const **0.2** relate to inner **Mic Lenth** / length scaling (exact map UNKNOWN).

### UNKNOWN
- Contents of the M55/HPn-style top-left macro; full Trig/Value bus map to Mic Placement; what Order does after Iteration.

---

## 3. Mic Stand > Macro (StpFltr → Core → rr)

**Path:** `Panel > New > Instrument > Controls > Mic Stand > Macro`

**File:** `ab385702…4f1c.png`

### VERIFIED
- Five inputs: **1 W**, **2 L**, **3 Space**, **4 Angl**, **5 Dept**.
- Each → its own **StpFltr**; shared **Tol = 0.001**.
- StpFltr outs → Core Cell: **W→X**, **L→Y**, **Space→Spac**, **Angl→Angl**, **Dept→Dept**.
- Core Cell single out **rr** → macro out **1 rr**.

### LIKELY
- StpFltr gates noisy panel events so Core only updates on meaningful parameter change (tol 0.001).

### UNKNOWN
- Algebra inside this Core Cell (see §4–5 for nested view).

---

## 4. Mic Stand > Macro > Core Cell

**Path:** `… > Mic Stand > Macro > Core Cell`

**File:** `2b2fc6e8…1e89.png`

### VERIFIED
- Core inputs: **X**, **Y**, **Space**, **Angle**, **Depth**.
- **legacy R5 SR for EventCell** → inner Macro **Sr**.
- Inner Macro ports mirror spatial inputs (**X, Y, Space, Angle, Depth**) + **Sr**.
- Single Core output from Macro: labeled **Rr** on this shot (same chain as parent **rr**).

### LIKELY
- Label **Rr** / **rr** is one port; casing/OCR variation only.

### UNKNOWN
- How **Sr** is used inside the next Macro (sample-rate scaling of distance/time?).

---

## 5. Mic Stand > Macro > Core Cell > Macro (1/x → ry)

**Path:** `… > Mic Stand > Macro > Core Cell > Macro`

**File:** `e036c942…cf6c.png`

### VERIFIED
- Inputs: **x**, **y**, **Space**, **Angle**, **Depth**.
- **x, y, Space, Angle** → small gray block (4-in / 1-out) → top of Core Macro **`1/x`**.
- **Depth** → bottom of **`1/x`**.
- **`1/x`** out → terminal **ry**.

### LIKELY
- Gray block computes a length/radius or similar from planar geometry; **`1/x`** combines that with **Depth** (reciprocal or divide) to form **ry**.
- **ry** is the quantity later ingested by Mic Stand Core Cell (as **ry** / outer **Hr**).

### UNKNOWN
- Exact formula inside gray block and inside **`1/x`** (no operators readable beyond the macro name).

---

## 6. Mic Stand > Core Cell (Scaling + Macro)

**Path:** `Panel > New > Instrument > Controls > Mic Stand > Core Cell`

**File:** `225de358…6f87.png`

### VERIFIED
- Inputs: **ry**, **W**, **L**, **Space**, **Angle**, **Depth**, **Mic Lenth** (spelling **Lenth**, not Length).
- **ry** → **legacy R5 SR for EventCell** → Macro **ry**.
- **Scaling** block: in **W, L, Space, Angle, Depth, Mic Lenth** → out **W Scaled, L Scaled, Space Scaled, Angle Scaled, Depth Scaled, Mic Lenth Scaled**.
- Scaled outs + **ry** → Macro (ports renamed back to unscaled names on Macro side).
- Macro / Core outs: **Idx**, **X1**, **Y1**, **X2**, **Y2**, **R**.

### LIKELY
- Scaling normalizes panel units into Core geometry units (factors UNKNOWN).
- This is the same Core Cell seen from outside in §2 (port name differences: outer Hr↔ry, Mic↔Mic Lenth, IDX↔Idx).

### UNKNOWN
- Scaling formulas; Macro math that produces Idx / segment endpoints / R; how Iteration Mic index selects among N=8.

---

## Cross-shot wiring picture (LIKELY chain)

```
Panel W,L,Space,Angl,Dept
  → [StpFltr Tol=0.001] → Core(X,Y,Spac,Angl,Dept) + legacy SR
       → Macro (… → 1/x) → ry / rr
  → Mic Stand Core: ry (+ legacy SR) + Scaling(W,L,Space,Angle,Depth,Mic Lenth)
       → Macro → Idx, X1,Y1,X2,Y2, R
  → Trig/Value bus → Mic Placement
Iteration N=8 → Mic index
Side panels: Height, Car/Omni, Mic Respon(HF), HPF, HP In
```

Source Position is a separate Controls branch: Mouse Area XY + Db defaults → merge → snap → **X**.

---

## Gap

Windows Screenshot **(191)–(315)** not present on box — cannot verify further nested Scaling / Macro / gray-block / `1/x` internals or Source Position siblings until those files land.
