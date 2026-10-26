"""Polar tab display grids. They call _h_db_grid and do not touch the live path."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SW = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SW), str(SW / "engine")]

import polar_field as pf  # noqa: E402


def test_display_grids_are_h_db_grid():
    got = pf.display_h_db("NeumannU87AiCardioid", hpf_on=False, colour_mode="MEASURED_SHELF")
    from mic_colour.preset_store import get_store

    store = get_store()
    model = store.model_for("NeumannU87AiCardioid")
    hpf = store.hpf_of("NeumannU87AiCardioid")
    az = np.arange(pf.DISPLAY_AZ, dtype=float) * (2.0 * np.pi / float(pf.DISPLAY_AZ))
    rings = np.asarray(pf.RING_HZ, dtype=float)
    expect_rings = pf._h_db_grid(az, rings, "MEASURED_SHELF", model, hpf, False)
    logf = np.geomspace(20.0, 16000.0, pf.DISPLAY_LOG_N)
    ang = np.deg2rad(np.asarray(pf.DISPLAY_ANGLES_DEG, dtype=float))
    expect_angles = pf._h_db_grid(ang, logf, "MEASURED_SHELF", model, hpf, False)
    assert np.allclose(got["h_rings"], expect_rings)
    assert np.allclose(got["h_angles"], expect_angles)
    assert got["angles_deg"] == [0.0, 45.0, 90.0, 135.0, 180.0]
    assert got["freqs_hz"][0] == 20.0
    assert abs(got["freqs_hz"][-1] - 16000.0) < 1e-6
    band = list(pf.RING_HZ).index(1000.0)
    row = np.asarray(got["h_rings"][band], dtype=float)
    front = float(row[0])
    back = float(row[len(row) // 2])
    side = float(row[len(row) // 4])
    assert front - back > 0.0
    assert side < front


def test_display_is_not_on_the_compute_path():
    text = (SW / "polar_field.py").read_text(encoding="utf-8")
    body = text.split("def compute_polar_field", 1)[1].split("\ndef display_h_db", 1)[0]
    assert "display_h_db" not in body
