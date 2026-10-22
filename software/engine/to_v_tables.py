#!/usr/bin/env python3
"""Reflection X/Y/Z Code → To V index maps (data only).

Vision re-read 2026-09-19 from Screenshots (206), (208)–(209), (334)–(347).

THIS MODULE IS DATA. Do not import it from render_pipeline / early_field / fdn.
To V 17–52 is a different bus from FDN V1–32. Voice↔tap map is still UNKNOWN.

See findings/yz-to-v-reverified.md.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

# --- X Code: repeating-5, To V 17–52. VERIFIED shot 206. --------------------
X_MACROS: Tuple[str, ...] = ("X", "2W-X", "-X", "2W+X", "-2W+X")
X_INDEX0 = 17
X_INDEX1 = 52


def x_macro(voice_index: int) -> Optional[str]:
    """Named X-macro writing this To V index, or None outside 17–52."""
    if voice_index < X_INDEX0 or voice_index > X_INDEX1:
        return None
    return X_MACROS[(voice_index - X_INDEX0) % 5]


X_MACRO_BY_INDEX: Dict[int, str] = {
    i: X_MACROS[(i - X_INDEX0) % 5] for i in range(X_INDEX0, X_INDEX1 + 1)
}


# --- Y Code first column. VERIFIED cyan → To V *inputs* (not To V→M). --------
# Shot 338: 2H+Y → 13–18, 24
# Shots 208 / 337: 2H-Y → 19–23, 27–28
# Remainder of 13–33 (25, 26, 29–33) is -Y / Y / -2H+Y — not split VERIFIED.
Y_MACRO_BY_INDEX: Dict[int, str] = {}
for _i in (13, 14, 15, 16, 17, 18, 24):
    Y_MACRO_BY_INDEX[_i] = "2H+Y"
for _i in (19, 20, 21, 22, 23, 27, 28):
    Y_MACRO_BY_INDEX[_i] = "2H-Y"

# LIKELY extra 2H-Y hits in columns 34–52 (cyan on To V inputs, shot 337).
# Not merged into Y_MACRO_BY_INDEX — do not treat as VERIFIED.
Y_LIKELY_2H_Y_EXTRA: Tuple[int, ...] = (36, 37, 40, 41, 45, 46, 49, 50)


# --- Z Code first column 19–33. VERIFIED cyan → To V inputs. -----------------
# 342: 2L+Z → 19–24; 343: 2L-Z → 25–28; 345: Z → 29–32; 347: 4L-Z → 33 only.
Z_MACRO_BY_INDEX: Dict[int, str] = {}
for _i in range(19, 25):
    Z_MACRO_BY_INDEX[_i] = "2L+Z"
for _i in range(25, 29):
    Z_MACRO_BY_INDEX[_i] = "2L-Z"
for _i in range(29, 33):
    Z_MACRO_BY_INDEX[_i] = "Z"
Z_MACRO_BY_INDEX[33] = "4L-Z"


def y_macro(voice_index: int) -> Optional[str]:
    """VERIFIED Y-macro for this index, or None if not in the verified subset."""
    return Y_MACRO_BY_INDEX.get(int(voice_index))


def z_macro(voice_index: int) -> Optional[str]:
    """VERIFIED Z-macro for this index, or None if not in the verified subset."""
    return Z_MACRO_BY_INDEX.get(int(voice_index))


def triple(voice_index: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """(X, Y, Z) macros at this To V index. Missing axis → None, not a guess."""
    i = int(voice_index)
    return x_macro(i), y_macro(i), z_macro(i)
