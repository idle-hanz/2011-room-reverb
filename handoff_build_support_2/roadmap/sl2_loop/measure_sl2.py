"""SL2 room-average numbers. Does not retune. Writes measure_sl2.json next to this file."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "tests"), str(SW / "engine")]
os.chdir(SW)

import _sl_render as R  # noqa: E402
import render_pipeline as RP  # noqa: E402
import surf_loop as SL  # noqa: E402

OUT = Path(__file__).resolve().parent
SR = 48000


def _err(ir, info):
    t20 = SL.t20_per_octave(np.asarray(ir, float).sum(1), SR)
    tgt = np.asarray(info["surf"]["target_T_oct"], float)
    err = np.asarray(t20, float) / tgt - 1.0
    return t20, err


def _render_recorded(body):
    seen = []
    orig = RP.makeup_at_stand

    def wrap(*args, **kwargs):
        value = orig(*args, **kwargs)
        seen.append(float(value))
        return value

    RP.makeup_at_stand = wrap
    try:
        ir, info = R.render_body(**body)
    finally:
        RP.makeup_at_stand = orig
    return ir, info, seen


def main() -> None:
    body = R.room_body("real_default", 1.8, surf_directional=False)
    ir_s, info_s, mk_s = _render_recorded(body)
    t20, err = _err(ir_s, info_s)
    flat = dict(body, decay_mode="flat")
    ir_f, info_f, mk_f = _render_recorded(flat)
    same = ir_f.tobytes() == ir_s.tobytes()
    report = {
        "directional": info_s.get("surf", {}).get("directional"),
        "t20": [None if x != x else round(float(x), 4) for x in t20],
        "target_T_oct": info_s["surf"]["target_T_oct"],
        "err_pct": [None if x != x else round(100.0 * float(x), 2) for x in err],
        "peak": float(np.max(np.abs(ir_s))),
        "finite": bool(np.all(np.isfinite(ir_s))),
        "limiter_db": info_s.get("limiter_db"),
        "limiter_samples": info_s.get("limiter_samples"),
        "flat_limiter_db": info_f.get("limiter_db"),
        "flat_limiter_samples": info_f.get("limiter_samples"),
        "stab_max_loop_db": [b["stab"]["max_loop_db"] for b in info_s["surf"]["buses"]],
        "makeup_surfaces": [round(x, 8) for x in mk_s],
        "makeup_flat": [round(x, 8) for x in mk_f],
        "makeup_equal": mk_s == mk_f,
        "surfaces_equals_flat_samples": same,
        "gate_125_250": bool((-0.40 <= err[0] <= 0.0) and (-0.40 <= err[1] <= 0.0)),
        "gate_500_up": bool(np.max(np.abs(err[2:])) <= 0.15),
    }
    (OUT / "measure_sl2.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
