"""Acceptance tests for Build's BINAURAL mic mode.

Point RR_SW at a software/ tree (default: the box p5 tree). The API names used here are the
ones proposed in BINAURAL_MODE_BRIEF.md section 7; if Build picks other names, adapt the
helpers at the top, not the assertions.

Reference numbers come from this pack (presets/binaural/, binaural_fitter/reference.py).
Locked decisions (DECISIONS_LOCKED_2026-09-30.md): diffuse IC tail, SADIE2_KU100 default, K=6 one mirror table,
1/r^2 from head centre, rear images (BINAURAL_REAR32). The pack-side proofs pass in test_binaural_locked.py.
"""
import importlib
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pytest

PACK = Path(__file__).resolve().parents[1]
SW = Path(os.environ.get("RR_SW", "/workspace/build_support_2/work/p5/software"))
PRESET = "SADIE2_KU100"

ROOM = (6.0, 3.0, 8.0)
HEAD = (3.0, 1.5, 1.5)
LEFT_SRC = (1.0, 1.5, 1.5)      # 2 m to the left of a head facing +Z (L = smaller X, K1 convention)


def _sw():
    if str(SW) not in sys.path:
        sys.path.insert(0, str(SW))
    ef = importlib.import_module("engine.early_field")
    return ef


def _stand(ef, yaw=0.0, **kw):
    """Proposed: MicStand.binaural(...) classmethod -> stand with binaural=True."""
    return ef.MicStand.binaural(cx=HEAD[0], cy=HEAD[1], cz=HEAD[2], head_yaw_deg=yaw, preset=PRESET, **kw)


def _colour(sr):
    mod = importlib.import_module("mic_colour.binaural")
    return mod.BinauralColour(PRESET, sr)


def _pack_preset():
    return json.loads((PACK / "presets" / "binaural" / f"{PRESET}.json").read_text())


def _params_path() -> Path:
    """RR_PARAMS, else this repo's software/parameters.csv."""
    env = os.environ.get("RR_PARAMS")
    if env:
        return Path(env)
    local = Path(__file__).resolve().parents[2] / "software" / "parameters.csv"
    if local.is_file():
        return local
    if (SW / "parameters.csv").is_file():
        return SW / "parameters.csv"
    return Path("/workspace/build_support/planning/parameters.csv")


def test_binaural_in_mic_setup_dropdown():
    html = (SW / "static" / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<option value="binaural"', html)
    assert "headphones" in html.lower()  # the "binaural needs headphones" note


def test_centre_capsule_muted():
    ef = _sw()
    taps = ef.compute_taps(ROOM, LEFT_SRC, _stand(ef), hadamard_n=32)
    assert all(t.level_c == 0.0 and t.press_c == 0.0 and t.grad_c == 0.0 for t in taps)


def test_ear_spacing_fixed_and_space_ignored():
    ef = _sw()
    st = _stand(ef)
    assert st.space == pytest.approx(_pack_preset()["ear_spacing_m"], abs=1e-9)
    st2 = _stand(ef, space=0.50)  # user Space must not change the head
    assert st2.space == pytest.approx(st.space)


def test_patterns_and_capsule_yaw_locked():
    ef = _sw()
    st = _stand(ef, pattern_l="fig8", yaw_l_deg=-30)
    assert st.pattern_l == st.pattern_r == "omni"          # HRTF colour replaces the pattern
    assert math.degrees(st.mlalr) == pytest.approx(-90.0) and math.degrees(st.mralr) == pytest.approx(90.0)


def test_itd_sign_correct_for_left_source():
    ef = _sw()
    t = ef.compute_taps(ROOM, LEFT_SRC, _stand(ef), hadamard_n=32)
    direct = [x for x in t if x.order == 0][0]
    itd_us = 1e3 * (direct.delay_ms_r - direct.delay_ms_l)
    p = _pack_preset()
    want = float(np.interp(90.0, p["itd"]["table_lateral_deg"], p["itd"]["table_itd_us"]))
    assert itd_us > 0
    assert itd_us == pytest.approx(want, abs=30.0)


def test_head_yaw_rotates_ears_as_one_unit():
    ef = _sw()
    ahead = (3.0, 1.5, 4.5)
    d0 = [x for x in ef.compute_taps(ROOM, ahead, _stand(ef, 0.0), hadamard_n=32) if x.order == 0][0]
    d9 = [x for x in ef.compute_taps(ROOM, ahead, _stand(ef, 90.0), hadamard_n=32) if x.order == 0][0]
    assert abs(d0.delay_ms_r - d0.delay_ms_l) < 1e-6
    assert d9.delay_ms_r - d9.delay_ms_l > 0.5  # head faces +X: source now on the left


@pytest.mark.parametrize("sr", [44100, 48000])
def test_ild_left_source_within_tolerance(sr):
    ef = _sw()
    from mic_colour.sos_fit import sos_db, unpack_record
    col = _colour(sr)
    t = [x for x in ef.compute_taps(ROOM, LEFT_SRC, _stand(ef), hadamard_n=32) if x.order == 0][0]
    rl = unpack_record(col.record_for("l", t.az_head_deg, t.el_head_deg))
    rr = unpack_record(col.record_for("r", t.az_head_deg, t.el_head_deg))
    ild = sos_db(rl, [4000.0], sr)[0] - sos_db(rr, [4000.0], sr)[0]
    # pack reference at the same node (SADIE KU100, az 80-100 el 0 nodes): > 6 dB, left louder
    assert ild > 6.0
    assert t.level_l == pytest.approx(t.level_r)  # 1/r^2 from head centre (LOCKED 2026-09-30)


@pytest.mark.parametrize("sr", [44100, 48000])
def test_binaural_filters_stable(sr):
    from mic_colour.sos_fit import unpack_record
    col = _colour(sr)
    for rec in col.all_records():
        sos = unpack_record(rec)
        for b0, b1, b2, a1, a2 in sos:
            assert np.max(np.abs(np.roots([1.0, a1, a2]))) < 1.0


@pytest.mark.parametrize("yaw", [0.0, 90.0, 180.0])
def test_binaural_bank_fits_max_irs_with_two_sources(yaw):
    """With rear images (BINAURAL_REAR32) the pack reference needs 24-36 records here (reports/rear_images.json)."""
    ef = _sw()
    col = _colour(48000)
    ta = ef.compute_taps(ROOM, (2.6, 1.2, 4.75), _stand(ef, yaw), hadamard_n=32)
    tb = ef.compute_taps(ROOM, (3.4, 1.2, 4.75), _stand(ef, yaw), hadamard_n=32)
    bank = col.bank_for(ta, tb, n=32, direct_index=ef.direct_line_index(ta, 32))
    assert bank["on"] is True
    assert len(bank["irs"]) <= 64


@pytest.mark.parametrize("sr", [32000, 88200, 96000])
def test_binaural_unsupported_rate_off_with_notice(sr):
    col = _colour(sr)
    assert col.measured is False
    assert "44.1 and 48 kHz" in col.notice


def test_direct_path_gets_hrtf():
    ef = _sw()
    col = _colour(48000)
    t = [x for x in ef.compute_taps(ROOM, LEFT_SRC, _stand(ef), hadamard_n=32) if x.order == 0][0]
    assert col.record_for("l", t.az_head_deg, t.el_head_deg) is not None
    assert col.record_for("r", t.az_head_deg, t.el_head_deg) is not None


def test_parameters_csv_has_binaural_rows():
    csv = _params_path().read_text(encoding="utf-8")
    for key in ("head_yaw_deg", "binaural_preset", "binaural_itd_mode", "binaural_tail_mode",
                "binaural_image_set", "binaural_level_ref", "binaural_K"):
        assert re.search(rf"^{key},", csv, re.M), key


# ---------- locked 2026-09-30 ----------

def test_binaural_locked_defaults():
    if str(SW) not in sys.path:
        sys.path.insert(0, str(SW))
    D = importlib.import_module("app_server").DEFAULTS
    assert D["binaural_preset"] == "SADIE2_KU100"
    assert D["binaural_tail_mode"] == "diffuse_ic"
    assert D["binaural_level_ref"] == "head_centre"
    assert int(D["binaural_K"]) == 6 and D["binaural_symmetric"] is True
    assert D["binaural_image_set"] == "binaural_rear32"


def test_binaural_image_set_has_rear_images():
    ef = _sw()
    want = [tuple(n) for n in json.loads((PACK / "presets/binaural/image_sets/binaural_rear32.json").read_text())["indices"]]
    taps = ef.compute_taps(ROOM, (2.6, 1.2, 4.75), _stand(ef), hadamard_n=32)
    assert [tuple(t.n) for t in taps] == want
    assert sum(1 for t in taps if t.n[2] < 0) == 5
    assert ef.direct_line_index(taps, 32) == 2


def test_rear_images_lateralised_and_front_back_coloured():
    ef = _sw()
    from mic_colour.sos_fit import sos_db, unpack_record
    col = _colour(48000)
    band = np.geomspace(1000, 8000, 40)
    for t in ef.compute_taps(ROOM, (2.6, 1.2, 4.75), _stand(ef), hadamard_n=32):
        if t.n[2] >= 0:
            continue
        assert abs(t.az_head_deg) > 90.0                       # arrives from behind (head yaw 0)
        rl = unpack_record(col.record_for("l", t.az_head_deg, t.el_head_deg))
        rr = unpack_record(col.record_for("r", t.az_head_deg, t.el_head_deg))
        ild = float(np.mean(sos_db(rl, band, 48000) - sos_db(rr, band, 48000)))
        if t.n[0] == -1:                                       # rear-left (smaller X)
            assert t.delay_ms_r > t.delay_ms_l and ild > 3.0
        elif t.n[0] == 1:                                      # rear-right
            assert t.delay_ms_l > t.delay_ms_r and ild < -3.0
        front = col.record_for("l", math.copysign(180.0 - abs(t.az_head_deg), t.az_head_deg), t.el_head_deg)
        assert front != col.record_for("l", t.az_head_deg, t.el_head_deg)  # front/back get different colour


def test_binaural_tail_coherence_matches_head():
    """Proposed: render_pipeline.render_binaural_fdn_ir(...) -> (L, R) FDN tail in diffuse_ic mode."""
    if str(SW) not in sys.path:
        sys.path.insert(0, str(SW))
    rp = importlib.import_module("render_pipeline")
    sys.path.insert(0, str(PACK))
    from binaural_fitter import tail_ic as T
    ef = _sw()
    taps = ef.compute_taps(ROOM, (2.6, 1.2, 4.75), _stand(ef), hadamard_n=32)
    L, R = rp.render_binaural_fdn_ir(taps, ROOM, 48000, 340.0, 4000.0, 0.999, rp.DEFAULT_DEPTH,
                                     preset=PRESET, tail_mode="diffuse_ic")
    a0 = int(0.1 * 48000) + 256
    f, c = T.measure_ic(L[a0:], R[a0:], 48000)
    got = T.band_ic(f, c, T.THIRD_OCT)
    ft, ict = T.target_ic(PRESET)
    want = np.interp(np.log(T.THIRD_OCT), np.log(ft), ict)
    assert np.max(np.abs(got - want)) <= 0.15
    assert np.sqrt(np.mean((got - want) ** 2)) <= 0.06
