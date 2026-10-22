"""ASSUMED preset family → pattern, family, polar.

Does not carry yaw, space, or mic_setup. Those stay where the desk left them.
"""

from __future__ import annotations

# pattern, engine family ("cardioid"|"bi"), polar slider.
_FAMILY = {
    "fig8_ribbon": ("fig8", "bi", 0.5),
    "fig8": ("fig8", "bi", 0.5),
    "bidirectional": ("fig8", "bi", 0.5),
    "bidirect": ("fig8", "bi", 0.5),
    "hypercardioid": ("supercardioid", "cardioid", 1.0),
    "supercardioid": ("supercardioid", "cardioid", 1.0),
    "super": ("supercardioid", "cardioid", 1.0),
    "omni": ("omni", "cardioid", 0.0),
    "dynamic_cardioid": ("cardioid", "cardioid", 0.5),
    "sdc_cardioid": ("cardioid", "cardioid", 0.5),
    "ldc_cardioid": ("cardioid", "cardioid", 0.5),
    "cardioid": ("cardioid", "cardioid", 0.5),
}


def capsule_law(family: str) -> dict:
    key = str(family or "").strip().lower().replace("-", "_").replace(" ", "_")
    pattern, fam, polar = _FAMILY.get(key, ("cardioid", "cardioid", 0.5))
    return {"pattern": pattern, "family": fam, "polar": float(polar)}
