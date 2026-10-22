"""Pack tests (should PASS now): presets, tables, stability, errors, ITD/ILD signs, reference mapping."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from binaural_fitter.reference import image_to_ears, load_preset, load_table, record_sos
from binaural_fitter.sosfit import sos_db

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "presets" / "binaural"
IDS = ["SADIE2_KU100", "SADIE2_KEMAR", "THK_KU100_FF"]
RATES = [44100, 48000]
MAX_IRS = 64   # live_stereo.c (p5), VERIFIED
MAX_SOS = 6    # live_stereo.c (p5), VERIFIED
MIC_FITTER = Path("/workspace/mic_fitter/presets")


@pytest.mark.parametrize("pid", IDS)
def test_preset_schema_and_honesty(pid):
    p = load_preset(pid)
    assert p["schema"] == "mic_fitter.binaural_preset.v1"
    assert p["honesty"] == "MEASURED"
    assert p["licence"]["id"] in ("Apache-2.0", "CC-BY-SA-3.0")
    assert 0.15 < p["ear_spacing_m"] < 0.20


def test_index_lists_all_and_default():
    idx = json.loads((B / "index.json").read_text())
    assert idx["schema"] == "mic_fitter.binaural_index.v1"
    assert sorted(e["preset_id"] for e in idx["presets"]) == sorted(IDS)
    assert idx["default_preset"] == "SADIE2_KU100"


@pytest.mark.parametrize("pid", IDS)
@pytest.mark.parametrize("sr", RATES)
@pytest.mark.parametrize("K", [3, 6])
def test_table_fits_engine_limits_and_is_stable(pid, sr, K):
    t = load_table(pid, sr, K)
    assert t["schema"] == "colour_sos_grid.v1" and t["fit_fs"] == sr and t["K"] == K
    assert K <= MAX_SOS
    assert len(t["nodes"]) <= MAX_IRS  # mirror-symmetric: one record per node serves both ears
    for rec in t["sos"]["L"]:
        sos = np.asarray(rec, dtype=np.float32).astype(np.float64)  # as pack_record stores it
        assert sos.shape == (K, 5)
        for b0, b1, b2, a1, a2 in sos:
            assert np.max(np.abs(np.roots([1.0, a1, a2]))) < 0.9995
            assert np.max(np.abs(np.roots([b0, b1, b2]))) <= 1.0 + 1e-6  # minimum phase


@pytest.mark.parametrize("pid", IDS)
def test_mirror_symmetry_exact(pid):
    t = load_table(pid, 48000)
    for n, m in enumerate(t["mirror"]):
        a, e = t["nodes"][n]
        am, em = t["nodes"][m]
        assert abs(e - em) < 1e-9
        assert abs(a + am) < 1e-6 or abs(abs(a) - 180) < 1e-6 or abs(e) > 89
        assert t["sos"]["R"][n] == t["sos"]["L"][m]


@pytest.mark.parametrize("pid", IDS)
@pytest.mark.parametrize("sr", RATES)
def test_k6_error_budget(pid, sr):
    m = load_preset(pid)["colour"]["rates"][str(sr)]["metrics"]["K6"]
    assert m["node_fit_rms_db"]["median"] <= 0.6
    assert m["node_fit_max_db"]["p95"] <= 3.5
    assert m["node_fit_max_db"]["max"] <= 4.5
    assert m["holdout_total_rms_db"]["median"] <= 2.0


@pytest.mark.parametrize("pid", IDS)
def test_itd_sign_and_size(pid):
    it = load_preset(pid)["itd"]
    lat = np.array(it["table_lateral_deg"])
    tab = np.array(it["table_itd_us"])
    assert tab[np.argmin(np.abs(lat - 90))] > 600      # left source: left ear leads by > 0.6 ms (measured LF)
    assert tab[np.argmin(np.abs(lat + 90))] < -600
    assert abs(tab[np.argmin(np.abs(lat))]) < 1e-6
    assert it["rms_err_us_tabulated_5deg"] < it["rms_err_us_geometry_only"] / 2


@pytest.mark.parametrize("pid", IDS)
def test_ild_left_source_positive_at_4k(pid):
    t = load_table(pid, 48000)
    n = min(range(len(t["nodes"])), key=lambda i: abs(t["nodes"][i][0] - 80) + abs(t["nodes"][i][1]))
    L = sos_db(record_sos(t, n), [4000.0], 48000)[0]
    R = sos_db(record_sos(t, t["mirror"][n]), [4000.0], 48000)[0]
    assert L - R > 6.0


def test_reference_left_source_earlier_louder_via_colour():
    p = load_preset("SADIE2_KU100")
    t = load_table("SADIE2_KU100", 48000)
    head = (3.0, 1.5, 1.5)
    src = (1.0, 1.5, 1.5)  # 2 m to the LEFT (smaller X) of a head facing +Z
    L, R = image_to_ears(p, t, head, 0.0, src)
    assert L.az == pytest.approx(90.0, abs=1e-6)
    itd_us = 1e3 * (R.delay_ms - L.delay_ms)
    tab = np.array(p["itd"]["table_itd_us"])
    lat = np.array(p["itd"]["table_lateral_deg"])
    assert itd_us == pytest.approx(float(np.interp(90.0, lat, tab)), abs=25.0)  # near-field parallax at 2 m
    assert L.level == R.level  # 1/r^2 from head centre: ILD comes only from the HRTF
    gL = sos_db(record_sos(t, L.record), [4000.0], 48000)[0]
    gR = sos_db(record_sos(t, R.record), [4000.0], 48000)[0]
    assert gL > gR


def test_reference_head_yaw_rotates_ears():
    p = load_preset("SADIE2_KU100")
    t = load_table("SADIE2_KU100", 48000)
    head = (3.0, 1.5, 1.5)
    src = (3.0, 1.5, 4.5)  # straight ahead at yaw 0
    L0, R0 = image_to_ears(p, t, head, 0.0, src)
    assert abs(L0.delay_ms - R0.delay_ms) < 1e-9
    L9, R9 = image_to_ears(p, t, head, 90.0, src)  # head turned to face +X: source now on the LEFT
    assert L9.az == pytest.approx(90.0, abs=1e-6)
    assert R9.delay_ms > L9.delay_ms


def test_unsupported_rate_has_no_table():
    assert load_table("SADIE2_KU100", 32000) is None


@pytest.mark.skipif(not MIC_FITTER.exists(), reason="box-only check")
def test_existing_20_presets_untouched():
    """The 20 MEASURED mic presets and their index are not modified by this pack."""
    idx = json.loads((MIC_FITTER / "index.json").read_text())
    assert idx["schema"] == "mic_fitter.preset_index.v3"
    assert len(idx["presets"]) == 20
    assert all(e.get("honesty") == "MEASURED" for e in idx["presets"])
    snap = json.loads((ROOT / "reports" / "existing_presets_sha1.json").read_text())
    for name, h in snap.items():
        assert hashlib.sha1((MIC_FITTER / name).read_bytes()).hexdigest() == h
