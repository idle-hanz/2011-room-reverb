"""T2 draft: the L/R button mapping (lr_buttons.js) never changes the speaker weights.

Runs the JS mapping in node, posts the before/after bodies through the real
app_server.params_from_body + desk_matrix.fold_for, and requires identical weights.
Copy to software/tests/ with _harness.py; needs node on PATH (skip otherwise)."""
from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path
import pytest
import _harness as H

JS = Path(__file__).resolve().parent / "lr_buttons.js"
if not JS.exists():  # prebuild layout: ../t2_mixer/lr_buttons.js
    JS = Path(__file__).resolve().parents[1] / "t2_mixer" / "lr_buttons.js"
NODE = shutil.which("node")
ROUTES = ["l", "r", "s", "both", "centre", "pan"]


def _map(route, phase, pan, ms_mid):
    src = (f"const M=require({json.dumps(str(JS))});"
           f"const f=M.fromRoute({json.dumps(route)},{phase},false,{{msMid:{str(ms_mid).lower()},pan:{pan}}});"
           f"const t=M.toRoute(f.btn,{{msMid:{str(ms_mid).lower()},legacyBoth:f.legacyBoth,forcePan:f.forcePan}});"
           "console.log(JSON.stringify({t,f}));")
    out = subprocess.run([NODE, "-e", src], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


@pytest.mark.skipif(NODE is None, reason="node not installed")
@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("phase", [1, -1])
def test_mapping_is_a_null_on_the_c_strip(route, phase):
    for ms_mid in (False, True):
        for pan in ([-1.0, -0.4, 0.0, 0.3, 1.0] if route == "pan" else [0.0]):
            pair_mode = "ms" if ms_mid else "independent"
            before = H.body(pair_mode=pair_mode, ms_m="c", mic_route_c=route, mic_phase_c=float(phase),
                            mic_pan_c=pan, mic_gain_c=0.8, mic_gain_l=0.0, mic_gain_r=0.0)
            m = _map(route, phase, pan, ms_mid)
            t, f = m["t"], m["f"]
            pan2 = 0.0 if f["patch"].get("pan") == 0 else pan
            after = dict(before, mic_route_c=t["route"], mic_phase_c=float(t["phase"]), mic_pan_c=pan2)
            wb, wa = H.weights(before), H.weights(after)
            for k in H.KEYS:
                assert abs(wb[k] - wa[k]) < 1e-12, (route, phase, ms_mid, pan, k, wb, wa)
