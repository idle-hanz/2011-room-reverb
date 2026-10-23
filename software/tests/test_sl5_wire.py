"""SL5 wiring: old scenes, the plaster + parquet library set, make_panel, the model curve."""
import math
import pytest
try:
    import _sl_harness as H
except ImportError:
    from tests import _sl_harness as H
import surf_panels as P


def test_old_scene_loads_flat_without_rows():
    import app_server as A
    p = A.params_from_body({})
    assert p["decay_mode"] == "flat"
    assert p["surf_treatment"] == []
    dropped = A.params_from_body({
        "surf_treatment": [{"id": "x", "face": "D", "type": "membrane", "f0": 90, "q": 1, "amax": 0.3, "coverage": 2}],
    })
    assert dropped["surf_treatment"] == []


def test_plaster_parquet_set_does_not_replace_default_cards():
    from surface_colour import default_surfaces, load_material_sets
    sets = {s["id"]: s["faces"] for s in load_material_sets()}
    assert sets["plaster_parquet"] == {
        "A": "plaster_smooth", "B": "plaster_smooth", "C": "plaster_smooth",
        "D": "plaster_smooth", "E": "wood_parquet", "F": "plaster_smooth",
    }
    boot = default_surfaces()
    assert boot["A"]["absorb"][0] == 0.05
    assert boot["E"].get("material") != "wood_parquet"
    assert boot["A"].get("material") != "plaster_smooth"


def test_make_panel_keeps_the_formula_q():
    import app_server as A
    low = A.api_make_panel({"f0": 125})
    assert low["ok"] is True and low["row"]["type"] == "membrane" and low["row"]["q"] == 2.0
    helm = A.api_make_panel({"f0": 198.4})
    assert helm["row"]["type"] == "helmholtz" and helm["row"]["q"] == 3.0
    assert A.api_make_panel({"f0": 400})["row"] is None


def test_toggling_a_125_panel_moves_the_model_curve():
    """Box UI proof: T(125) 2.091 s on, 2.615 s off, and 4 kHz moves under 2 %."""
    import surf_autotreat as AT
    import surf_target as ST
    p = H.default_params()
    plan = AT.auto_treat(p["W"], p["H"], p["L"], p["surfaces"], float(p["humidity"] or 0.0), 1.8)
    rows = [dict(r, suggested=False, on=True) for r in plan["suggested"]]
    hit = [r for r in rows if r.get("face") == "D" and r.get("type") in ("membrane", "helmholtz")
           and abs(float(r.get("f0") or 0) - 125.0) < 1.0]
    assert hit, [(r.get("face"), r.get("type"), r.get("f0")) for r in rows]

    def curve(rs):
        cards = P.cards_with_treatment(p["surfaces"], rs)
        out = ST.room_result(
            p["W"], p["H"], p["L"], p["surfaces"], float(p["humidity"] or 0.0),
            decay_s=1.8, decay_lock=True, cards_with_fn=cards,
        )
        f = out["f"]
        i = min(range(len(f)), key=lambda k: abs(math.log(f[k] / 125.0)))
        j = min(range(len(f)), key=lambda k: abs(math.log(f[k] / 4000.0)))
        return out["T_faces_air"][i], out["T_faces_air"][j]

    on_b, on_h = curve(rows)
    off_b, off_h = curve([dict(r, on=False) if r is hit[0] else r for r in rows])
    assert on_b == pytest.approx(2.091, rel=0.02)
    assert off_b == pytest.approx(2.615, rel=0.02)
    assert abs(on_h / off_h - 1.0) < 0.02


def test_ui_adds_the_shell_on_enter_and_leaves_the_slider_builders():
    root = H.SW
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    assert "RR_SL_STAGE = 5" in html
    js = (root / "static" / "js" / "sl_room_result.js").read_text(encoding="utf-8")
    assert "function addRoomShell()" in js
    assert "paintMode(enter)" in js
    assert "if (entered && SL_STAGE >= 5)" in js
    cs = (root / "static" / "js" / "colour_surfaces.js").read_text(encoding="utf-8")
    absorb = cs.split("ColourSurfaces.prototype._buildAbsorbSliders")[1].split("ColourSurfaces.prototype._buildEqControls")[0]
    eq = cs.split("ColourSurfaces.prototype._buildEqControls")[1].split("ColourSurfaces.prototype._bindDiffusion")[0]
    assert 'type="range"' in absorb
    assert 'type="range"' in eq
