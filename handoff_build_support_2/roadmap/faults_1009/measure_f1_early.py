"""Early-only distance check and a 0.30 m centre (screenshot height gap).

The solo-C early rows in measure_f1_f2.py were silent: early is L/R only
and that body set those gains to 0. This pass keeps L and R at gain 1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
OUT = ROOT / "handoff_build_support_2" / "roadmap" / "faults_1009"
sys.path.insert(0, str(OUT))

import measure_f1_f2 as m  # noqa: E402


def main() -> None:
    rows = []
    print("--- early pair, L/R on the stand, C off, Direct and FDN down ---", flush=True)
    for d in (0.5, 2.0, 8.0):
        body = m.ortf(
            W=24.0, H=6.0, L=24.0,
            sx=12.0, sy=1.5, sz=16.0,
            mcx=12.0, my=1.5, mcz=16.0 - d,
            third_mic="off", mic_gain_c=0.0,
            fdn_wet=0.0, direct_wet=0.0, early_wet=1.0,
        )
        rows.append(m.coeffs(f"early pair {d:.1f}m", body))

    print("--- C 0.30 m from source, L/R stay on the boot stand ---", flush=True)
    near = m.ortf(
        third_mic="room", mic_gain_c=1.0,
        mic_x_c=2.6, mic_y_c=1.5, mic_z_c=4.75,
        yaw_c_deg=0.0,
    )
    # 0.30 m vertical gap, same floor spot as the source. Screenshot 555 heights.
    near["mic_y_c"] = 1.5
    near["sy"] = 1.2
    rows.append(m.coeffs("shot C 0.30m up", near))

    renders = []
    for d in (0.5, 8.0):
        body = m.ortf(
            W=24.0, H=6.0, L=24.0,
            sx=12.0, sy=1.5, sz=16.0,
            mcx=12.0, my=1.5, mcz=16.0 - d,
            third_mic="off", mic_gain_c=0.0,
            fdn_wet=0.0, direct_wet=0.0, early_wet=1.0,
        )
        try:
            renders.append(m.render_level(f"early pair {d:.1f}", body))
        except Exception as exc:
            renders.append({"label": f"early pair {d:.1f}", "error": str(exc)})
            print("RENDER FAIL", d, exc, flush=True)
    out = {"coeffs": rows, "renders": renders}
    OUT.joinpath("f1_early.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("done", flush=True)


if __name__ == "__main__":
    main()
