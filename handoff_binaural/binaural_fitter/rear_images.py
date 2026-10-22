"""Binaural image set with rear images (DECISION LOCKED 2026-09-30, item 5).

Play is compiled with N = 32 lines and one early image per line (VERIFIED live_stereo.c
`N = 32`, route `early L/R [2][32]`), and the FDN is excited by those same images (engine lock).
So "adding rear images" in binaural mode means a binaural 32-image set, BINAURAL_REAR32:

  * start from the p5 LIVE_32 table (VERIFIED engine/early_field.py), keep its order;
  * the 3 duplicate voices go: (0,1,1)#2, (0,0,1)#2, (-1,-2,0)#2;
  * the 4 order-4 corners go: (1,2,1), (1,-2,1), (-1,2,1), (-1,-2,1) (the weakest images: they cross 4 walls);
  * 2 missing L/R or floor partners come in: (0,-1,1) (floor + front wall, partner of (0,1,1)) and (-1,-1,0)
    (partner of (1,-1,0)), so the set is mirror-symmetric in X;
  * 5 rear images come in (the Behind wall family, n_z = -1): (0,0,-1), (+-1,0,-1), (0,+-1,-1).

The selection rule is a design choice (ASSUMED). Counts, symmetry and arrival directions are checked by
tests/test_binaural_locked.py (VERIFIED). Direct (0,0,0) stays at index 2, so direct_line_index is unchanged.
"""
from __future__ import annotations

LIVE_32_P5 = (
    (0, 2, 0), (0, 1, 0), (0, 0, 0), (0, -1, 0), (0, -2, 0),
    (0, 2, 1), (0, 1, 1), (0, 1, 1), (0, 0, 1), (0, 0, 1),
    (1, 2, 1), (1, 1, 1), (1, 0, 1), (1, -1, 1), (1, -2, 1),
    (1, 2, 0), (1, 1, 0), (1, 0, 0), (1, -1, 0), (1, -2, 0),
    (-1, 2, 0), (-1, 1, 0), (-1, 0, 0), (-1, -2, 0), (-1, -2, 0),
    (-1, 2, 1), (-1, 1, 1), (-1, 0, 1), (-1, -1, 1), (-1, -2, 1),
    (0, 1, 2), (0, 0, 2),
)  # copy of p5 engine.early_field.LIVE_32 (a test checks it still matches)

# slot index in LIVE_32 -> replacement
REPLACE = {
    7: (0, -1, 1),    # duplicate (0,1,1)  -> floor partner
    9: (0, 0, -1),    # duplicate (0,0,1)  -> rear wall, first order
    24: (-1, -1, 0),  # duplicate (-1,-2,0) -> X partner of (1,-1,0)
    10: (1, 0, -1),   # corner (1,2,1)     -> rear + right wall
    25: (-1, 0, -1),  # corner (-1,2,1)    -> rear + left wall
    14: (0, 1, -1),   # corner (1,-2,1)    -> rear + ceiling
    29: (0, -1, -1),  # corner (-1,-2,1)   -> rear + floor
}


def binaural_rear32(live32=LIVE_32_P5):
    out = list(live32)
    for i, n in REPLACE.items():
        out[i] = n
    return tuple(out)


BINAURAL_REAR32 = binaural_rear32()
REAR = tuple(n for n in BINAURAL_REAR32 if n[2] < 0)
