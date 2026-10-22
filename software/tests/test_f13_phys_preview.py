"""F13. Two sources with the key absent get a real physical-ceiling preview."""
from __future__ import annotations

import math
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]
import app_server as A  # noqa: E402


def test_two_source_phys_preview_is_on():
    client = TestClient(A.app)
    res = client.post("/api/phys_preview", json={
        "two_sources": True,
        "decay_lock": True,
        "decay_s": 1.8,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["on"] is True
    assert math.isfinite(float(data["k"]))
    assert math.isfinite(float(data["mean_500_1k"]))
