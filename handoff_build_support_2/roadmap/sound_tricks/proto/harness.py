"""Sound-tricks prototype harness (box only). Renders an IR through the app's Render path
(render_pipeline.render with a unit impulse), like tests/_harness.py. RR_SOFTWARE picks the tree."""
from __future__ import annotations
import inspect, json, math, os, sys, copy
from pathlib import Path
import numpy as np
SW = Path(os.environ.get("RR_SOFTWARE", "/workspace/st_work/software"))
sys.path[:0] = [str(SW), str(SW / "engine")]
_cwd = os.getcwd(); os.chdir(SW)
import app_server as A  # noqa
from render_pipeline import render  # noqa
os.chdir(_cwd)
SR = 48000
HERE = Path(__file__).resolve().parent
BASE = json.load(open(HERE / "default_body.json"))

def body(**over):
    b = copy.deepcopy(BASE)
    b.update(over)
    return b

def render_ir(b, ir_ms=None, sr=SR, dry=None):
    b = dict(b)
    if ir_ms is not None:
        b["ir_length_ms"] = ir_ms
    os.chdir(SW)
    try:
        p = A.params_from_body(b)
        if dry is None:
            dry = np.zeros(1); dry[0] = 1.0
        kw = {n: p[n] for n in inspect.signature(render).parameters if n not in ("dry", "sr") and n in p}
        kw["desk"] = p
        y_l, y_r, info = render(dry, sr, **kw)
    finally:
        os.chdir(_cwd)
    return np.stack([np.asarray(y_l, float), np.asarray(y_r, float)], axis=1), info, p
