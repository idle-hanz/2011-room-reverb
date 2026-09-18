# Structure screenshots batch 3 — Absorb / Prepare / Direct Field (2026-09-16 ~15:16–15:18 BST)

Ensemble: `2011-room-reverb.ens` (Reaktor 6 Structure view).

**Coverage:** 12 PNGs opened with Read (+ tight 2×/3× crops for bit tables and Prepare math).

Tags: **VERIFIED** = literally visible · **LIKELY** = strong inference from wiring/names · **UNKNOWN** = not shown / OCR-unreliable / conflicting.

**Priority targets this batch**

| Target | Status |
|--------|--------|
| Absorb | **HIT** — Absorb Diffus Code + Surface Absor+Diffu + A–F Code |
| Hadamard | **Partial** — dense To V → `M` collectors; **no** labeled Hadamard opened |
| 2W-X / 2H-Y | **MISS** — not opened |
| Scaling / 1/x gray block | **MISS** — not in these shots (see batches 1–2) |

---

## 1. Absorb Diffus Code (top)

**Path:** `Panel > New > Instrument > Absorb Diffus Code`

**File:** `13966ed47798bc3a…bfcaba.png`

### VERIFIED
- Six child macros in a **serial chain:** **A Code → B Code → C Code → D Code → E Code → F Code**.
- Single **In** → A; each stage’s bottom-right out → next stage In; **F** bottom-right unconnected in this view.
- Each stage’s **top-right tap** → instrument OutPorts **1…6** labeled **A…F**.
- Properties: name **Absorb Diffus Code**; **Mono** checked; Look **Compact**.

### LIKELY
- Serial-in / parallel-tap topology = multi-stage absorb/diffus control chain (Event-rate masks inside A–F; audio absorb lives in **Surface Absor+Diffu**).

### UNKNOWN
- Audio vs Event rate inside A–F Code leaves; exact meaning of A–F tap buses.

---

## 2. Instrument overview (legacy RS-SR for EventCell)

**Path:** `Panel > New > Instrument > Prepare > legacy RS-SR for EventCell` (breadcrumb); selected macro **Surface Absor+Diffu**.

**File:** `ad4c0e1b1e734312…7ac5b3.png`

### VERIFIED (topology)
- **Switch** Surf(0) / Floor(1) / Seal(2) / Wall(3) → **Controller**.
- **Controller** fans many params (FrR, AvW, At*, Di*, St*, Fr*, W, H, L, S, SX/SY/SZ, Ear, HF, HpF, Hp, Mat, …).
- **Absorb Diffus Code** (A–F) sits above **Surface Absor+Diffu** (In + A–F + many Controller lines → **Out**, **Diffu**).
- **Prepare** → ML*/MR*/DD; **Reflection Code** → SX/SY/SZ; **Distances and Delays** → TL/LDir/fL, TC/CDir/fC, TR/RDir/fR, DD.
- **Sound Processing** (In, Diffu, delay taps, Mat) → **L/C/R** → **Mixer** → stereo outs.

### LIKELY
- Surface-type Switch selects Controller material/absorb preset family.

---

## 3. Direct Field wrapper

**Path:** `Panel > New > Instrument > Prepare > Macro > Direct Field`

**File:** `0f0533eb87844f45…42b15aa.png`

### VERIFIED
- Outer ports: **W, H, L, SX, SY, SZ, MSS, MDPC, MX, MY, MZ**.
- Single inner macro **`Legacy R5 SR for EventCell`** (pass-through of those ports; SX/SY/SZ casing Sx/Sy/Sz on inner).
- Outer outs: **SX/SY/SZ**, **MLX/MLY/MLZ**, **MLALR**, **MCX/MCY/MCZ**, **MRX/MRY/MRZ**, **MRALR**, **DD**.
- **MLAUD** / **MRAUD** leave the inner macro **unwired** to outer ports in this view.

---

## 4. Direct Field > `sqrt` (Direct Distance)

**Path:** `… > Prepare > Macro > Direct Field > sqrt`

**File:** `f04c767c2167b220…21761a.png`

### VERIFIED
- Ins: **SDX, SDZ, MLX, MLZ, MRX, MRZ** (no Y in this macro).
- Left distance:  
  \(d_L = \sqrt{(SDX-MLX)^2 + (SDZ-MLZ)^2}\)
- Right distance:  
  \(d_R = \sqrt{(SDX-MRX)^2 + (SDZ-MRZ)^2}\)
- Both distances → Primary **`<`**; compare drives two **selector/switch** modules; results feed a final combine → out **`DD`**.

### LIKELY
- Final combine is **`d_L + d_R`** (selectors sort min/max then add — algebraically same as sum). **2D XZ only** (unlike Distances and Delays’ 3D √).

### UNKNOWN
- Exact selector module type / whether any path can drop a distance (if not pure sum).

---

## 5. Prepare > Macro (mic + sound coords)

**Path:** `Panel > New > Instrument > Prepare > Macro`

**File:** `ba2cdbc63d991533…905a01.png`

### VERIFIED (this screenshot)
- **SX** = **Width × (Sound X 0–1)**.
- **SZ** = **Mic Centre Z + (Length − Mic Centre Z) × (Sound Z 0–1)**  
  i.e. lerp(**MCZ**, **L**, SoZ).
- **MLALR** = `(Diverg Parallel Converge × 0.5) + (−0.25)` = `MDPC×0.5 − 0.25`.
- **MRALR** = `0.25 − (MDPC × 0.5)`.
- **MRAUD** (and MLAUD path) ← constant **0**.
- Shared **Mic + Sound Y** → **MCY / MRY / SY**.
- **MRZ** shares **Mic Centre Z**; **Direct Field** consumes SX/SZ + MLX/MLZ + MRX/MRZ → **DD**.

### CONFLICT / do not silently merge with prior Prepare notes
- This shot’s Primary glyph for **Mic Centre Z** reads as **`*`**: **MCZ = Length × Mic Z** (multiple crops).
- Prior findings claimed **MCZ = L + MZ** (Add).
- **Action:** treat operator as **CONFLICTING** until a human confirms the glyph; both L and MZ still feed MCZ.

### LIKELY
- Panel sound X/Z are **normalized 0–1** mapped into room metres via W and [MCZ…L].

---

## 6–11. Absorb Diffus Code > A–F Code (bit → To V)

**Paths:** `… > Absorb Diffus Code > {A,B,C,D,E,F} Code`

**Files:**
| Code | Hash prefix |
|------|-------------|
| A | `eabccfae7d4898e6…` |
| B | `6296f501581bb8c8…` |
| C | `5bebf2cb3d920ec7…` |
| D | `e9f76eb59ef51f27…` |
| E | `04af93aaed3f24c8…` |
| F | `952ef9b511eacb87…` |

### VERIFIED (shared structure)
- Each A–F Code is a **column of indexed writers**:
  - Pair of constants: **index** (Event → port **V**) + **value 0|1** (→ lower port).
  - Module strip labeled **`To V`** (with terminal/F icon).
- Indices cover approximately **18…52** (some views show **53**); three visual bands ~**18–33**, **34–43**, **44–52**.
- Outputs aggregate into tall gray **`M`** collector(s); lower `M` often feeds upper `M` (same pattern family as Reflection Code collectors).
- Dense diagonal yellow wiring between columns — **looks** matrix-like but is **not** a labeled Hadamard in these shots.

### LIKELY
- **Surface → image-voice map:** each surface letter A–F writes a **0/1 mask** onto the same voice-index space used by Reflection **To V** sinks (here starting at **18**, Reflection Y/Z shots emphasized **19–52**).
- Serial A→F chain + taps = progressive mask bus into **Surface Absor+Diffu**.

### Bit tables (LIKELY — vision OCR of tight crops; not hand-counted)

Partial rows with **consistent** multi-crop agreement. Gaps / disagreements left blank. **Do not treat as final truth.**

**A Code (partial)**  
18–28 values: `0,0,0,1,1,1,1,1,1,1,1` (18–23 solid; 23–28 mid-crop all 1s)

**B Code (partial)**  
18–23 values: `0,0,0,0,0,0`

**C Code (partial)**  
18–23 values: `1,1,1,0,0,0`

**D Code (partial)**  
18–28 values: all `0`  
34–41 values: `1,1,1,0,0,0,0,0`

**E Code (partial)**  
18–31: `0,0,1,1,1, 0,0,1,1,1, 0,0,1,1`  
35–41: `0,0,1,0,0,1,0`  
44–51: `0,0,1,0,0,1,0,0`  
(34 / 32–33 / 42–43 / 52–53 still soft)

**F Code (partial)**  
18–29: `0,1,1,1,0, 0,1,1,1,0, 0,1`  
34–41: `0,0,1,0,0,1,0,0`  
44–51: `0,1,0,0,1,0,0,1`

### UNKNOWN
- Exact full 18–52 masks per letter (OCR of 0 vs 1 is error-prone at Structure zoom).
- Whether value port is audio-rate gate vs Event coefficient.
- Whether column-to-column “butterfly” wires implement mixing or only bus aesthetics / Order chaining.
- Live Hadamard ±1 signs (still not on-screen).

---

## 12. Surface Absor+Diffu

**Path:** `Panel > New > Instrument > Surface Absor+Diffu`

**File:** `46db14de41ba247b…91d527.png`

**Info tab (VERIFIED):** *“Calculates each surface Absorption and Diffusion.”*

### VERIFIED
- **Six Surface macros** daisy-chained **A → B → C → D → E → F** → **Out**.
- Surfaces **A–D:** ports **In, Freq, On, Mid/Widt, dB** (labels vary slightly by crop: Mid vs Widt).
- Surfaces **E–F:** **In, FrH, On/Dn, FrL** (split high/low frequency) — **no** single Freq/dB pair like A–D.
- Bottom **Diffu** path: tree of **`×` / `+`** over per-surface Dif inputs (**ADif, BDif, CDif, EDif, FDif**) × **MDif**, then **Clipper** → **Diffu**.

### LIKELY
- A–D = mid-oriented absorb EQ; E–F = shelving / dual-band absorb.
- Diffu aggregate is a clipped weighted sum of surface diffusion knobs × master.

### UNKNOWN
- Exact Diffu algebra (which Dif terms multiply vs add); internals of each Surface macro; mapping from Absorb Diffus Code A–F taps into this block’s On/Dif lines.

---

## Cross-check vs batches 1–2

- **No** open of **`2W-X` / `2H-Y`** leaf graphs — prior “still need Structure open” stands.
- **No** Mic Stand **Scaling** / **`1/x`** gray block (batch 1).
- Distances **`1/x`** + **340** (batch 2) unchanged.
- Prepare mic-centre / angle formulas: **this batch conflicts** with 2026-09-10 Add/`×±0.25` writeup — see §5.

---

## Top new facts (short)

1. **Absorb Diffus Code** = serial **A…F Code** with parallel taps A–F.
2. Each **A–F Code** writes **0/1** into **To V** indices **~18–52** (LIKELY surface↔image mask).
3. **Surface Absor+Diffu** = serial Surface A–F absorb + clipped Diffu sum; Info string confirmed.
4. **Direct Field > sqrt**: **2D XZ** \(d_L,d_R\) → **DD** (LIKELY \(d_L+d_R\)).
5. Prepare: **SX = W·SoX**; **SZ = lerp(MCZ, L, SoZ)**; angle outs **MDPC·0.5 ± offset 0.25** form (Add/Sub) — **MCZ op conflicts** with prior Add.
