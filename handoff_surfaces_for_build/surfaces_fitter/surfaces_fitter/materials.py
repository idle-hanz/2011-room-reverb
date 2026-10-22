"""ASSUMED textbook octave absorption coefficients + role tags.

Sources are typical published tables (Sengpielaudio / Everest / common NRC
compilations). Values are NOT measured for Idle's rooms and NOT Structure OCR.
Tag every preset ASSUMED_TEXTBOOK.

Octave centres: 125, 250, 500, 1000, 2000, 4000 Hz (published).
8000 Hz: extended by gentle clamp of 4 kHz, or slight rise for porous absorbers.
α is clamped to [0, 0.99] for reflection math √(1−α).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

OCTAVE_HZ: Tuple[float, ...] = (125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0)
ROLES_ALL = ("floor", "wall", "ceiling")
HONESTY = "ASSUMED_TEXTBOOK"


@dataclass(frozen=True)
class Material:
    id: str
    display_name: str
    roles: Tuple[str, ...]
    alpha_octave: Tuple[float, ...]  # 7 bands matching OCTAVE_HZ
    source_note: str
    honesty: str = HONESTY
    notes: str = ""

    def banned_on(self) -> List[str]:
        """Faces (roles) this material must never paint."""
        return [r for r in ROLES_ALL if r not in self.roles]

    def alpha_dict(self) -> Dict[str, float]:
        return {str(int(hz)): float(a) for hz, a in zip(OCTAVE_HZ, self.alpha_octave)}


def _clamp_alpha(vals: Sequence[float]) -> Tuple[float, ...]:
    out = []
    for v in vals:
        out.append(float(max(0.0, min(0.99, v))))
    return tuple(out)


def _ext8(a4k: float, mode: str = "clamp") -> float:
    """Extend 4 kHz α to 8 kHz."""
    if mode == "rise_porous":
        return float(max(0.0, min(0.99, a4k + 0.03)))
    if mode == "slight_rise":
        return float(max(0.0, min(0.99, a4k + 0.01)))
    # clamp / glass fall
    return float(max(0.0, min(0.99, a4k)))


# ---------------------------------------------------------------------------
# Material library (sane set)
# ---------------------------------------------------------------------------

MATERIALS: List[Material] = [
    Material(
        id="plaster_smooth",
        display_name="Plaster (smooth)",
        roles=("wall", "ceiling"),
        alpha_octave=_clamp_alpha(
            (0.02, 0.02, 0.03, 0.04, 0.05, 0.05, _ext8(0.05, "clamp"))
        ),
        source_note="Sengpiel / typical smooth plaster on solid backing",
        notes="Hard reflective finish; mild HF rise.",
    ),
    Material(
        id="gypsum_painted",
        display_name="Gypsum board (painted)",
        roles=("wall", "ceiling"),
        alpha_octave=_clamp_alpha(
            (0.10, 0.08, 0.05, 0.04, 0.05, 0.06, _ext8(0.06, "slight_rise"))
        ),
        source_note="Typical painted gypsum / drywall on studs (panel LF dip)",
        notes="Slight LF absorb from panel resonance; mid reflective.",
    ),
    Material(
        id="brick_unglazed",
        display_name="Brick (unglazed)",
        roles=("wall",),
        alpha_octave=_clamp_alpha(
            (0.03, 0.03, 0.03, 0.04, 0.05, 0.07, _ext8(0.07, "slight_rise"))
        ),
        source_note="Sengpiel / unglazed brick wall typical table",
        notes="Dense masonry; mostly reflective.",
    ),
    Material(
        id="concrete_painted",
        display_name="Concrete (painted)",
        roles=("floor", "wall", "ceiling"),
        alpha_octave=_clamp_alpha(
            (0.01, 0.01, 0.02, 0.02, 0.02, 0.03, _ext8(0.03, "clamp"))
        ),
        source_note="Painted concrete / sealed concrete typical",
        notes="Very reflective; legal on all faces.",
    ),
    Material(
        id="wood_parquet",
        display_name="Wood parquet",
        roles=("floor",),
        alpha_octave=_clamp_alpha(
            (0.04, 0.04, 0.07, 0.06, 0.06, 0.07, _ext8(0.07, "slight_rise"))
        ),
        source_note="Wood parquet / hardwood on concrete (typical)",
        notes="Floor only — not walls or ceiling.",
    ),
    Material(
        id="plywood_panel",
        display_name="Plywood panel",
        roles=("wall",),
        alpha_octave=_clamp_alpha(
            (0.28, 0.22, 0.17, 0.09, 0.10, 0.11, _ext8(0.11, "slight_rise"))
        ),
        source_note="Plywood paneling ~10 mm on battens (LF panel absorb)",
        notes="Needs LF absorb in fit (low_shelf + high_shelf candidate).",
    ),
    Material(
        id="carpet_on_concrete",
        display_name="Carpet on concrete",
        roles=("floor",),
        alpha_octave=_clamp_alpha(
            (0.02, 0.06, 0.14, 0.37, 0.60, 0.65, _ext8(0.65, "rise_porous"))
        ),
        source_note="Heavy carpet on concrete (no pad) — Sengpiel-style",
        notes="FLOOR ONLY. Ban on walls/ceiling unless Idle unlocks.",
    ),
    Material(
        id="carpet_on_foam",
        display_name="Carpet on foam",
        roles=("floor",),
        alpha_octave=_clamp_alpha(
            (0.08, 0.24, 0.57, 0.69, 0.71, 0.73, _ext8(0.73, "rise_porous"))
        ),
        source_note="Carpet on foam underlay / pad — typical published",
        notes="FLOOR ONLY. Stronger LF absorb than carpet-on-concrete.",
    ),
    Material(
        id="glass_window",
        display_name="Glass window",
        roles=("wall",),
        alpha_octave=_clamp_alpha(
            (0.35, 0.25, 0.18, 0.12, 0.07, 0.04, _ext8(0.04, "clamp"))
        ),
        source_note="Large ordinary window glass (panel LF resonance)",
        notes="WALL ONLY. HF reflective; LF panel absorb.",
    ),
    Material(
        id="acoustic_ceiling_tile",
        display_name="Acoustic ceiling tile",
        roles=("ceiling",),
        alpha_octave=_clamp_alpha(
            (0.45, 0.55, 0.70, 0.80, 0.80, 0.75, _ext8(0.75, "rise_porous"))
        ),
        source_note="Mineral-fiber / ACT NRC~0.70 class typical table",
        notes="Ceiling role primary; do not paint on floor.",
    ),
    Material(
        id="absorber_panel_2in",
        display_name="Absorber panel (2 in fiberglass)",
        roles=("wall",),
        alpha_octave=_clamp_alpha(
            (0.28, 0.70, 0.88, 0.92, 0.94, 0.92, _ext8(0.92, "rise_porous"))
        ),
        source_note="~50 mm fiberglass / rigid mineral wool panel typical",
        notes="High α mid–HF; wall treatment.",
    ),
    Material(
        id="heavy_curtain",
        display_name="Heavy curtain",
        roles=("wall",),
        alpha_octave=_clamp_alpha(
            (0.14, 0.35, 0.55, 0.72, 0.70, 0.65, _ext8(0.65, "rise_porous"))
        ),
        source_note="Heavy velour / drape on wall (spaced) — Sengpiel-style",
        notes="WALL ONLY — ban floor (E) and ceiling (F). NOT a floor finish.",
    ),
]


MATERIAL_BY_ID: Dict[str, Material] = {m.id: m for m in MATERIALS}


def list_materials() -> List[Material]:
    return list(MATERIALS)


def get_material(material_id: str) -> Material:
    if material_id not in MATERIAL_BY_ID:
        raise KeyError(f"Unknown material id: {material_id!r}")
    return MATERIAL_BY_ID[material_id]


def role_matrix() -> Dict[str, List[str]]:
    """role → list of material ids allowed on that face."""
    out: Dict[str, List[str]] = {r: [] for r in ROLES_ALL}
    for m in MATERIALS:
        for r in m.roles:
            out[r].append(m.id)
    return out
