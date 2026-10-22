# A–F bit tables — vision re-read (2026-09-19)

Source shots: `Screenshot (196).png` … `(201).png`  
Path: `Instrument > Absorb Diffus Code > {A–F} Code`  
Each To V writes Const **0 or 1** at Event index **18–52**.

Batch-4 OCR had **A** and **F** badly wrong (run-length collapse). **B** and **D** matched. **C** differed at index **33**. **E** differed at index **19**.

These bits are **not** wired into the Desktop renderer. Machine copy: `software/engine/absorb_masks.py`. Voice 18–52 vs FDN 1–32 map is still UNKNOWN.

Index order in every row: **18 … 52** (35 bits).

## A Code (196) — CORRECTED

```
18–33: 0 0 0 1 1 1 1 1 1 1 1 1 1 1 1 0
34–52: 0 0 0 1 1 1 1 1 0 1 1 1 1 1 1 1 1 1 0
```

Batch-4 claimed `18–33: 1`. Actual: 18–20 = 0, 21–32 = 1, 33 = 0.

## B Code (197) — matches batch-4

```
18–33: 0 0 0 0 0 0 1 1 1 1 1 1 1 1 1 1
34–52: 1 1 1 1 1 1 0 0 0 0 0 0 1 1 1 1 1 0 0
```

18–23:0 · 24–39:1 · 40–45:0 · 46–50:1 · 51–52:0.

## C Code (198) — index 33 corrected

```
18–33: 1 1 1 0 1 1 0 1 0 1 0 1 1 0 1 0
34–52: 1 1 0 1 1 0 1 1 1 1 1 1 0 1 0 0 0 0 0
```

Batch-4 had 33=1. Shot shows **33=0**.

## D Code (199) — matches batch-4

```
18–33: 0 0 0 0 0 0 0 0 0 0 0 0 0 1 1 1
34–52: 1 1 1 0 0 0 0 1 0 0 1 1 0 0 0 1 0 1 1
```

18–30:0 · 31–36:1 · 37–40:0 · 41:1 · 42–43:0 · 44–45:1 · 46–48:0 · 49:1 · 50:0 · 51–52:1.

## E Code (200) — index 19 corrected

```
18–33: 0 0 1 1 1 0 0 1 1 1 1 0 1 1 0 0
34–52: 1 1 0 1 0 0 1 1 1 1 0 0 0 0 0 0 0 0 0
```

Batch-4 had 19–22:1. Shot shows **19=0**, 20–22=1.

## F Code (201) — CORRECTED (batch-4 “18–40:1” was OCR collapse)

```
18–33: 0 1 1 1 0 0 1 1 1 0 0 1 1 1 0 1
34–52: 0 0 1 1 0 1 1 0 0 1 0 0 1 1 1 0 0 1 0
```

Early F looks like a repeating **011100** motif, not a long run of ones.

## Compact 18–52 strings (for diffs)

```
A 00011111111111000001111101111111110
B 00000011111111111111110000001111100
C 11101101010110101101101111110100000
D 00000000000001111110000100110001011
E 00111001111011001101001111000000000
F 01110011100111010011011001001110010
```

## Still UNKNOWN

Which image triple (X-macro, Y-macro, Z-macro) sits at each To V index, and how that relates to FDN voice k. Until that map is Structure-proven, masks stay out of audio.
