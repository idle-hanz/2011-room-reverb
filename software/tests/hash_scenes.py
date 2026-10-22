"""Render reference scenes through a software tree and print sha256 of the float64 output.
usage: RR_SOFTWARE=<tree> python hash_scenes.py [scene ...]   (box proof for the SL2 Flat bit-exact claim)"""
import hashlib, inspect, json, os, sys, time
from pathlib import Path
import numpy as np
SW = Path(os.environ["RR_SOFTWARE"]).resolve()
sys.path[:0] = [str(SW), str(SW / "engine")]
os.chdir(SW)
import app_server as A
from render_pipeline import render

def scenes():
    d = dict(A.DEFAULTS)
    yield "default_golden_body", dict(d)
    yield "default_lock_off", dict(d, decay_lock=False)
    yield "default_explicit_flat", dict(d, decay_mode="flat")
    yield "default_flat_with_rows", dict(d, decay_mode="flat", surf_treatment=[{"id": "x", "face": "D", "type": "membrane", "f0": 125, "q": 2, "amax": 0.6, "coverage": 0.5}], surf_cal=[1.2] * 7)
    yield "ortf_c_on", dict(d, mic_setup="ortf", space=0.17, toe_half_deg=55.0)
    yield "two_sources", dict(d, two_sources=True, source_balance=0.0)
    yield "dry_short_lock_off", dict(d, decay_lock=False, ir_length_ms=400)
    ui = json.loads((Path(__file__).resolve().parent / "fixture_ui_default_body.json").read_text())
    yield "ui_default_body", dict(ui)
    yield "ui_default_body_flat_rows", dict(ui, decay_mode="flat", surf_treatment=[{"id": "s", "face": "A", "type": "shell", "f0": 90, "q": 1, "amax": 0.35, "coverage": 0.3}])

def run(names):
    out = {}
    for name, b in scenes():
        if names and name not in names:
            continue
        t = time.time()
        p = A.params_from_body(b)
        dry = np.zeros(64); dry[0] = 1.0
        kw = {n: p[n] for n in inspect.signature(render).parameters if n not in ("dry", "sr") and n in p}
        kw["desk"] = p
        yl, yr, info = render(dry, 48000, **kw)
        x = np.stack([np.asarray(yl, np.float64), np.asarray(yr, np.float64)], 1)
        out[name] = dict(sha256=hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest(), n=int(x.shape[0]),
                         peak=float(np.max(np.abs(x))), secs=round(time.time() - t, 1), surf=("surf" in (info or {})))
        print(name, out[name], flush=True)
    return out

if __name__ == "__main__":
    res = run(sys.argv[1:])
    print("JSON " + json.dumps(res))
