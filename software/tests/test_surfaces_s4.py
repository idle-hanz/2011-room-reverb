"""S4: diffusion split, role-banned materials, Solo/Mute, porous-gap presets.

Defaults stay on the old single-knob numbers: both new keys are 0.15, solo and
mute are off, and effective_surfaces returns the same dict.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import render_pipeline as rp
import surface_colour as sc

SR = 48000.0
HONESTY = "MODELLED (Miki 1990 + Paris; sigma=15 kPa s/m2 ASSUMED)"
GAPS = (
    "absorber_panel_1in_gap1in",
    "absorber_panel_2in_gap2in",
    "absorber_panel_4in_gap4in",
)


def test_old_diffusion_copies_into_both_layers():
    old = sc.parse_surfaces({"A": {"diffusion": 0.4}})
    assert old["A"]["jitter_D"] == 0.4
    assert old["A"]["structure_dif"] == 0.4
    alias = sc.parse_surfaces({"B": {"jitter_d": 0.7}})
    assert alias["B"]["jitter_D"] == 0.7
    assert alias["B"]["structure_dif"] == 0.15
    both = sc.parse_surfaces({"A": {"jitter_D": 0.4, "structure_dif": 0.4}})
    n = (-1, 0, 0)
    assert rp.tap_dff(n, old) == rp.tap_dff(n, both)
    d_old = sc.jittered_distance(
        3.0, n, 2, "l", (0.0, 1.0, 1.0), (1.0, 1.2, 2.0), old, seed=1,
    )
    d_both = sc.jittered_distance(
        3.0, n, 2, "l", (0.0, 1.0, 1.0), (1.0, 1.2, 2.0), both, seed=1,
    )
    assert d_old == d_both


def test_jitter_only_leaves_structure_dif():
    card = sc.parse_surfaces({"C": {"jitter_D": 1.0}})
    assert card["C"]["jitter_D"] == 1.0
    assert card["C"]["structure_dif"] == 0.15
    base = sc.default_surfaces()
    assert rp.tap_dff((1, 0, 0), card) == rp.tap_dff((1, 0, 0), base)


def test_defaults_are_identity_gate():
    raw = sc.default_surfaces()
    assert sc.effective_surfaces(raw, None, None) is raw
    assert sc.solo_mute_gates(None, None) == [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    for card in raw.values():
        assert card["jitter_D"] == 0.15
        assert card["structure_dif"] == 0.15
        assert card["absorb"] == [0.05, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22]


def test_curtain_wall_only_and_carpet_floor_only():
    table = sc.MATERIAL_PRESETS
    assert "heavy_curtain" in table
    assert "carpet_on_concrete" in table
    assert "carpet_on_foam" in table
    for name, mat in table.items():
        if "curtain" in name:
            assert set(mat["roles"]) <= {"wall"}
            assert "floor" in mat["banned_on"] and "ceiling" in mat["banned_on"]
        if name.startswith("carpet"):
            assert set(mat["roles"]) == {"floor"}
            assert "wall" in mat["banned_on"] and "ceiling" in mat["banned_on"]
    assert sc.material_legal(table["heavy_curtain"], "A")
    assert not sc.material_legal(table["heavy_curtain"], "E")
    assert not sc.material_legal(table["heavy_curtain"], "F")
    assert sc.material_legal(table["carpet_on_concrete"], "E")
    assert not sc.material_legal(table["carpet_on_concrete"], "A")
    assert not sc.material_legal(table["carpet_on_concrete"], "F")


def test_porous_gap_beats_same_model_rigid():
    folder = ROOT / "presets" / "surfaces"
    for mid in GAPS:
        data = json.loads((folder / f"{mid}.json").read_text(encoding="utf-8"))
        assert data["honesty"] == HONESTY
        assert "MEASURED" not in data["honesty"]
        assert set(data["roles"]) == {"wall", "ceiling"}
        assert "floor" in data["banned_on"]
        gap = data["absorb"]
        rigid = data["on_rigid_absorb"]
        assert gap[0] > rigid[0]
        assert gap[1] > rigid[1]
        assert data["rmse_r_db"] < 0.5
        assert mid in sc.MATERIAL_PRESETS


def test_mute_skips_colour_and_zeroes_reflect_gain():
    raw = sc.default_surfaces()
    eff = sc.effective_surfaces(raw, None, list("ABCDEF"))
    x = np.zeros(256)
    x[0] = 1.0
    y = sc.apply_surface_to_buffer(x.copy(), eff, ["A", "B", "E"], SR)
    assert np.allclose(y, x)
    assert rp.tap_reflect_gain((0, 0, 0), eff) == 1.0
    assert rp.tap_reflect_gain((1, 0, 0), eff) == 0.0
    assert sc.card_jitter_D(eff["C"]) == 0.0
    assert sc.card_structure_dif(eff["C"]) == 0.0
    solo = sc.effective_surfaces(raw, "E", {"E": True})
    assert sc.surface_filter_stages(solo, ["E"], SR)
    assert sc.surface_filter_stages(solo, ["A"], SR) == []
    assert rp.tap_reflect_gain((0, -1, 0), solo) != 0.0
