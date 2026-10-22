"""Render scene.body(1, 1, 1.8) in Surfaces room-average mode and print T20.

BRAS fitted alphas are read from BRAS_DIR. They are not copied into the repo.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
SCENE = ROOT / "handoff_build_support" / "research" / "room_validation"
BRAS = Path(os.environ.get("BRAS_DIR", Path(os.environ["TEMP"]) / "bras_sl2"))
os.environ["BRAS_DIR"] = str(BRAS)
sys.path[:0] = [str(SW), str(SW / "tests"), str(SW / "engine"), str(SCENE)]
os.chdir(SW)

import scene  # noqa: E402
import surf_loop as SL  # noqa: E402
import _sl_render as R  # noqa: E402

SR = 48000


def main() -> None:
    body = scene.body(1, 1, 1.8)
    body["decay_mode"] = "surfaces"
    body["surf_directional"] = False
    ir, info = R.render_body(**body)
    t20 = SL.t20_per_octave(np.asarray(ir, float).sum(1), SR)
    bands = [125, 250, 500, 1000, 2000, 4000, 8000]
    report = {
        "ls": 1,
        "mp": 1,
        "decay_s": 1.8,
        "decay_mode": "surfaces",
        "directional": info.get("surf", {}).get("directional"),
        "W": body["W"],
        "H": body["H"],
        "L": body["L"],
        "sr": SR,
        "finite": bool(np.all(np.isfinite(ir))),
        "peak": float(np.max(np.abs(ir))),
        "limiter_db": info.get("limiter_db"),
        "limiter_samples": info.get("limiter_samples"),
        "t20": {str(b): (None if x != x else round(float(x), 4)) for b, x in zip(bands, t20)},
        "target_T_oct": info.get("surf", {}).get("target_T_oct"),
        "stab_max_loop_db": [b["stab"]["max_loop_db"] for b in info.get("surf", {}).get("buses", [])],
    }
    out = Path(__file__).resolve().parent / "measure_cr2.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
