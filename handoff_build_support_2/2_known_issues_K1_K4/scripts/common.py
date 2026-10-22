"""Shared helpers: import the box copy of software/ read-only."""
import os, sys, json
from pathlib import Path
SW = Path(os.environ.get('RR_SW', '/workspace/build_support_2/work/latest/software')).resolve()
sys.path[:0] = [str(SW), str(SW / 'engine')]
os.chdir(SW)
import app_server as A  # noqa: E402
def params(**over):
    body = dict(A.DEFAULTS); body.update(over)
    return A.params_from_body(body)
CLIENT_ORTF = dict(space=0.17, yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0, toe_half_deg=55.0)  # app.js state defaults (lines 69-73)
def dump(obj, name):
    out = Path(__file__).resolve().parents[1] / 'results' / name
    out.write_text(json.dumps(obj, indent=1, default=float)); return out
