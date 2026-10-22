"""Optional manufacturer high-pass stacked on H_db.

Default off. Disabled when hpf_hz is null. Not the unwired panel mic_hp_*.
"""

from __future__ import annotations

from mic_colour.model import apply_hpf


def stack_hpf(db, freqs, hpf_hz, hpf_slope=12, engaged=False):
    if not engaged or hpf_hz is None:
        return db
    try:
        hz = float(hpf_hz)
    except (TypeError, ValueError):
        return db
    if hz <= 0.0:
        return db
    slope = 12
    try:
        slope = int(hpf_slope)
    except (TypeError, ValueError):
        slope = 12
    return apply_hpf(db, freqs, hz, slope, True)
