#!/usr/bin/env python3
"""A–F Absorb Diffus Code bit tables (To V 18–52).

Vision re-read 2026-09-19 from Screenshots (196)–(201).

THIS MODULE IS DATA. Do not import it from render_pipeline / early_field / fdn.
Voice 18–52 is not proven to be FDN voice 1–32. Wiring these bits into audio
would invent a map.

See findings/af-bit-tables-reverified.md.
"""

from __future__ import annotations

from typing import Dict, Tuple

# Index 18 .. 52 inclusive (35 bits). Values are 0 or 1 as written on To V.
INDEX0 = 18
INDEX1 = 52

# Compact strings, index 18 at left.
_STRINGS: Dict[str, str] = {
    "A": "00011111111111000001111101111111110",
    "B": "00000011111111111111110000001111100",
    "C": "11101101010110101101101111110100000",
    "D": "00000000000001111110000100110001011",
    "E": "00111001111011001101001111000000000",
    "F": "01110011100111010011011001001110010",
}


def _parse(s: str) -> Tuple[int, ...]:
    if len(s) != (INDEX1 - INDEX0 + 1):
        raise ValueError("mask length")
    return tuple(int(ch) for ch in s)


MASKS: Dict[str, Tuple[int, ...]] = {k: _parse(v) for k, v in _STRINGS.items()}


def bit(letter: str, voice_index: int) -> int:
    """0|1 written by `{letter} Code` at To V index, or 0 if out of 18–52."""
    if voice_index < INDEX0 or voice_index > INDEX1:
        return 0
    return MASKS[letter][voice_index - INDEX0]
