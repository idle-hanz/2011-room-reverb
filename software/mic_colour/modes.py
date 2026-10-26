"""Colour modes. One enum. No Structure-pole mode."""

from __future__ import annotations

MEASURED_SHELF = "MEASURED_SHELF"
BYPASS = "BYPASS"
ASSUMED_TOYS = "ASSUMED_TOYS"

_MODES = (MEASURED_SHELF, BYPASS, ASSUMED_TOYS)

_ALIASES = {
    "MEASURED": MEASURED_SHELF,
    "MEASURED_SHELF": MEASURED_SHELF,
    "BYPASS": BYPASS,
    "ASSUMED_TOYS": ASSUMED_TOYS,
    "ASSUMED": ASSUMED_TOYS,
    "TOYS": ASSUMED_TOYS,
    "LEGACY": ASSUMED_TOYS,
}


def parse_colour_mode(value) -> str:
    """Missing or unknown → MEASURED_SHELF. There is no Structure-pole mode."""
    if value is None:
        return MEASURED_SHELF
    key = str(value).strip().upper().replace("-", "_").replace(" ", "_")
    if not key:
        return MEASURED_SHELF
    return _ALIASES.get(key, MEASURED_SHELF)


def shelf_in_scalars_for(mode: str) -> bool:
    """L8: only ASSUMED_TOYS keeps the −6 dB level shelf in the inject scalars."""
    return parse_colour_mode(mode) == ASSUMED_TOYS


def fitter_on_for(mode: str) -> bool:
    return parse_colour_mode(mode) == MEASURED_SHELF


COLOUR_SOS = "sos"
COLOUR_FIR = "fir"


def parse_colour_impl(value) -> str:
    """Missing or unknown → sos (27 Sep IIR). fir keeps the Phase 3 impulse."""
    if value is None:
        return COLOUR_SOS
    key = str(value).strip().lower().replace("-", "_")
    if key in ("fir", "fir_mp", "minimum_phase", "impulse"):
        return COLOUR_FIR
    return COLOUR_SOS
