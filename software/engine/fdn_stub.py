"""
FDN helpers / inject API for the 2011 room reverb rebuild.

Audio FDN lives in fdn.py. This module keeps the unscaled ±1 Hadamard
inject helpers importable without pulling the renderer (avoids cycles
with early_field.py).

Agreed (from them / overnight spec):
  * Square FDN, N=32 prototype
  * Mixing matrix = unscaled Hadamard ±1 only (no 1/sqrt(N))
  * Loop gain 0..1 separate (AGC label ``0 > In < 1``)
  * FDN delays from room size, not image delays (see fdn.propose_fdn_delays_samples)
"""

from __future__ import annotations

from typing import List, Sequence


def unscaled_hadamard_signs(n: int) -> List[List[int]]:
    """Recursive Sylvester Hadamard, entries ±1 only. ASSUMED construction."""
    if n < 1 or (n & (n - 1)) != 0:
        raise ValueError(f"Hadamard size must be power of 2, got {n}")
    h: List[List[int]] = [[1]]
    while len(h) < n:
        top = [row + row for row in h]
        bot = [row + [-x for x in row] for row in h]
        h = top + bot
    return h


def inject_tap_into_fdn(
    tap_amplitude: float,
    tap_index: int,
    n_lines: int = 32,
    signs: Sequence[Sequence[int]] | None = None,
) -> List[float]:
    """Map one early tap into N-line inject via Hadamard column. No 1/sqrt(N)."""
    if signs is None:
        signs = unscaled_hadamard_signs(n_lines)
    col = tap_index % n_lines
    return [float(tap_amplitude) * float(signs[row][col]) for row in range(n_lines)]


def stub_note() -> str:
    return (
        "FDN renderer: early-field/fdn.py (unscaled ±1 Hadamard, "
        "loop gain 0..1, delays from room size PROPOSAL)."
    )
