"""Shared helpers for the SL prebuild tests. In the app: copy next to the tests in software/tests/.
On the box: RR_SOFTWARE=/workspace/sl_work/B/software (the patched copy)."""
from __future__ import annotations
import copy, json, os, sys
from pathlib import Path
SW = Path(os.environ.get("RR_SOFTWARE", Path(__file__).resolve().parents[1])).resolve()
sys.path[:0] = [str(SW), str(SW / "engine")]
HERE = Path(__file__).resolve().parent
_cwd = os.getcwd(); os.chdir(SW)
import app_server as A  # noqa: E402
os.chdir(_cwd)
import surf_panels as P  # noqa: E402

SETS = {  # proto2/rooms.py (library ids)
    "real_default": {"A": "plaster_smooth", "C": "plaster_smooth", "B": "plaster_smooth", "D": "plaster_smooth", "E": "wood_parquet", "F": "plaster_smooth"},
    "studio_panelled": {"A": "plywood_panel", "C": "plywood_panel", "B": "plywood_panel", "D": "plywood_panel", "E": "carpet_on_concrete", "F": "gypsum_painted"},
    "bare_brick_plaster": {"A": "brick_unglazed", "C": "brick_unglazed", "B": "plaster_smooth", "D": "plaster_smooth", "E": "concrete_painted", "F": "plaster_smooth"},
}


def default_params():
    os.chdir(SW)
    try:
        return A.params_from_body(dict(A.DEFAULTS))
    finally:
        os.chdir(_cwd)


def room(name="real_default"):
    p = default_params()
    s = copy.deepcopy(p["surfaces"])
    for k, mid in SETS[name].items():
        c = P.load_material(mid, SW / "presets" / "surfaces")
        s[k].update(absorb=c["absorb"], absorb_hz=c["absorb_hz"], material=mid)
    return p["W"], p["H"], p["L"], s, float(p["humidity"])


def fixture(name):
    return json.loads((HERE / name).read_text())
