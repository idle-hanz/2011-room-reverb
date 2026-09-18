# Voice table proposal — 32 live of 52 fan-out triples

Source: `/workspace/ens-mining-notes.md` §2 (52 sink ids).  
Tags: **VERIFIED** (bytes), **PROPOSAL** (which 32 are live — id→voice map still UNKNOWN).

## Constraints (VERIFIED)

- 52 unique sink ids; each is one `(X-macro, Y-macro, Z-macro)` triple.
- **`-Z` and `-2L+Z` OutPort connection count = 0** → omit (macros present, unwired).
- **`4L-Z` fans only to id 109** (with passthrough `X`,`Y`).
- Duplicate triples (same macros, different ids): **15≡13**, **19≡17**, **49≡47** — keep lowest id.
- Instrument comment: voices reduced to **32** for square FDN.
- Mental model: **voice = lane** (1..32) into unscaled Hadamard / FDN.

## Macro → paper-n (LIKELY, not Structure-proven)

| Macro | LIKELY n | Expression (name + Mul/Const) |
|-------|---------:|-------------------------------|
| `X`/`Y`/`Z` | 0 | S |
| `-X`/`-Y` | −1 | −S |
| `2W-X`/`2H-Y`/`2L-Z` | +1 | 2R−S |
| `2W+X`/`2H+Y`/`2L+Z` | +2 | 2R+S |
| `-2W+X`/`-2H+Y` | −2 | −2R+S |
| `4L-Z` | face +z | 4L−Z |

**Gap:** no wired `-Z`, so paper `nz=−1` slice has **no** `-Z` triple. Behind-mic Z images are not in this fan-out as named `-Z`.

## Proposed live 32 (PROPOSAL)

Prefer: dense **3×3-ish on X/Y** × `{Z, 2L-Z}` + **face centres** `(±2W,Y,Z)`, `(X,±2H,Z)`, `(X,Y,4L-Z)`, plus fill with `2L+Z` / remaining `2H±` on `2L-Z`.

| # | sink id | X | Y | Z | notes |
|--:|--------:|---|---|----|-------|
| 1 | 7 | X | -Y | Z | core |
| 2 | 5 | X | Y | Z | direct |
| 3 | 17 | X | Y | 2L-Z | (dup 19 omitted) |
| 4 | 3 | X | 2H-Y | Z | |
| 5 | 13 | X | 2H-Y | 2L-Z | (dup 15 omitted) |
| 6 | 57 | -X | -Y | 2L-Z | |
| 7 | 45 | -X | Y | Z | |
| 8 | 55 | -X | Y | 2L-Z | |
| 9 | 43 | -X | 2H-Y | Z | |
| 10 | 53 | -X | 2H-Y | 2L-Z | |
| 11 | 37 | 2W-X | -Y | Z | |
| 12 | 27 | 2W-X | -Y | 2L-Z | |
| 13 | 35 | 2W-X | Y | Z | |
| 14 | 25 | 2W-X | Y | 2L-Z | |
| 15 | 33 | 2W-X | 2H-Y | Z | |
| 16 | 23 | 2W-X | 2H-Y | 2L-Z | |
| 17 | 87 | 2W+X | Y | Z | face +X |
| 18 | 93 | -2W+X | Y | Z | face −X |
| 19 | 1 | X | 2H+Y | Z | face +Y |
| 20 | 9 | X | -2H+Y | Z | face −Y |
| 21 | 109 | X | Y | 4L-Z | **extra +z face** |
| 22 | 63 | X | Y | 2L+Z | +z layer |
| 23 | 31 | 2W-X | 2H+Y | Z | |
| 24 | 41 | -X | 2H+Y | Z | |
| 25 | 39 | 2W-X | -2H+Y | Z | |
| 26 | 47 | -X | -2H+Y | Z | (dup 49 omitted) |
| 27 | 11 | X | 2H+Y | 2L-Z | |
| 28 | 21 | 2W-X | 2H+Y | 2L-Z | |
| 29 | 29 | 2W-X | -2H+Y | 2L-Z | |
| 30 | 51 | -X | 2H+Y | 2L-Z | |
| 31 | 59 | -X | -2H+Y | 2L-Z | |
| 32 | 81 | 2W+X | Y | 2L-Z | |

**Lane index** in the table row order above = prototype tap index 0..31 when using this table (PROPOSAL — not proven To V map).

## Intentionally omitted

- Unwired macros: all triples that would need `-Z` or `-2L+Z` (none exist in the 52).
- Duplicate ids: 15, 19, 49.
- Remaining unique triples (mostly extra `2L-Z` / `±2W` on `2L-Z` / `2L+Z` sides): see `OMITTED_UNIQUE` in `voice_table_32.py`.

## Still UNKNOWN

Mapping of these sink ids → Reaktor polyphonic voice 1..32 / To Voice injectors.

