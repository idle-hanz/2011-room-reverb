"""Proposed 32 live early-field voices from ens 52 fan-out triples.

PROPOSAL only — id→poly voice map UNKNOWN. See voice_table_32.md.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

Triple = Tuple[str, str, str]

# VERIFIED fan-out (ens-mining-notes); duplicates noted
ALL_52: Dict[int, Triple] = {
    1: ("X", "2H+Y", "Z"),
    3: ("X", "2H-Y", "Z"),
    5: ("X", "Y", "Z"),
    7: ("X", "-Y", "Z"),
    9: ("X", "-2H+Y", "Z"),
    11: ("X", "2H+Y", "2L-Z"),
    13: ("X", "2H-Y", "2L-Z"),
    15: ("X", "2H-Y", "2L-Z"),  # dup of 13
    17: ("X", "Y", "2L-Z"),
    19: ("X", "Y", "2L-Z"),  # dup of 17
    21: ("2W-X", "2H+Y", "2L-Z"),
    23: ("2W-X", "2H-Y", "2L-Z"),
    25: ("2W-X", "Y", "2L-Z"),
    27: ("2W-X", "-Y", "2L-Z"),
    29: ("2W-X", "-2H+Y", "2L-Z"),
    31: ("2W-X", "2H+Y", "Z"),
    33: ("2W-X", "2H-Y", "Z"),
    35: ("2W-X", "Y", "Z"),
    37: ("2W-X", "-Y", "Z"),
    39: ("2W-X", "-2H+Y", "Z"),
    41: ("-X", "2H+Y", "Z"),
    43: ("-X", "2H-Y", "Z"),
    45: ("-X", "Y", "Z"),
    47: ("-X", "-2H+Y", "Z"),
    49: ("-X", "-2H+Y", "Z"),  # dup of 47
    51: ("-X", "2H+Y", "2L-Z"),
    53: ("-X", "2H-Y", "2L-Z"),
    55: ("-X", "Y", "2L-Z"),
    57: ("-X", "-Y", "2L-Z"),
    59: ("-X", "-2H+Y", "2L-Z"),
    61: ("X", "2H-Y", "2L+Z"),
    63: ("X", "Y", "2L+Z"),
    66: ("X", "-Y", "2L+Z"),
    73: ("2W-X", "2H-Y", "2L+Z"),
    75: ("2W-X", "Y", "2L+Z"),
    77: ("2W-X", "-Y", "2L+Z"),
    79: ("2W+X", "2H-Y", "2L-Z"),
    81: ("2W+X", "Y", "2L-Z"),
    83: ("2W+X", "-Y", "2L-Z"),
    85: ("2W+X", "2H-Y", "Z"),
    87: ("2W+X", "Y", "Z"),
    89: ("2W+X", "-Y", "Z"),
    91: ("-2W+X", "2H-Y", "Z"),
    93: ("-2W+X", "Y", "Z"),
    95: ("-2W+X", "-Y", "Z"),
    97: ("-2W+X", "2H-Y", "2L-Z"),
    99: ("-2W+X", "Y", "2L-Z"),
    101: ("-2W+X", "-Y", "2L-Z"),
    103: ("-X", "2H-Y", "2L+Z"),
    105: ("-X", "Y", "2L+Z"),
    107: ("-X", "-Y", "2L+Z"),
    109: ("X", "Y", "4L-Z"),
}

DUP_IDS = (15, 19, 49)
UNWIRED_MACROS = ("-Z", "-2L+Z")

# PROPOSAL live 32 (row order = lane 0..31) — see voice_table_32.md
LIVE_32_IDS: List[int] = [
    7, 5, 17, 3, 13, 57, 45, 55, 43, 53,
    37, 27, 35, 25, 33, 23, 87, 93, 1, 9,
    109, 63, 31, 41, 39, 47, 11, 21, 29, 51,
    59, 81,
]

assert len(LIVE_32_IDS) == 32
assert len(set(LIVE_32_IDS)) == 32
assert 109 in LIVE_32_IDS
assert not any(i in LIVE_32_IDS for i in DUP_IDS)


def live_triples() -> List[Tuple[int, Triple]]:
    return [(i, ALL_52[i]) for i in LIVE_32_IDS]


def omitted_unique_ids() -> List[int]:
    kept = set(LIVE_32_IDS) | set(DUP_IDS)
    # unique by triple: lowest id per triple
    best = {}
    for tid, t in sorted(ALL_52.items()):
        best.setdefault(t, tid)
    return sorted(tid for tid in best.values() if tid not in kept)
