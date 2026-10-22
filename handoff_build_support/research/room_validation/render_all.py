"""Render the model IRs for BRAS CR2 (10 LS/MP pairs x variants) through the real Render path
(engine/tools/render_ir.py -> render_pipeline.render, unit impulse, clip_guard undone).
Trees: snapshot (as on Idle's PC 2026-09-27) and engine/work/sw_fix (F1-F3 tail/denormal fixes).
Usage: python render_all.py [--jobs 4] [--only variant,...]"""
import json, os, subprocess, sys, argparse
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as S, bras_cr2 as B

BS = "/workspace/build_support"
TREES = {"snap": f"{BS}/snapshot_2026-09-27/software", "fix": f"{BS}/engine/work/sw_fix/software"}
PY = os.environ.get("RR_PY", "/workspace/scratch_er_dropout/venv/bin/python")
OUT = os.environ.get("RV_WORK", "/workspace/rv_work")
T20_MEAS_1K = 1.93   # mean T20 @1 kHz over the 10 dodecahedron RIRs (our analysis; BRAS file: 1.92-1.93)
EY = S.eyring_t60(); EY_MID = float(round(0.5 * (EY[500] + EY[1000]), 2))
VARIANTS = {  # name: (tree, decay_s)
    "snap_default": ("snap", 1.8),      # UI default dial (decay_lock on, 1.8 s)
    "snap_eyring": ("snap", EY_MID),    # dial = Eyring prediction from BRAS alphas (what a user could compute)
    "snap_oracle": ("snap", T20_MEAS_1K),  # dial = measured T20 at 1 kHz (best case for a flat dial)
    "fix_eyring": ("fix", EY_MID),
    "fix_oracle": ("fix", T20_MEAS_1K),
}


def job(v, ls, mp):
    tree, dec = VARIANTS[v]
    out = os.path.join(OUT, f"{v}_LS{ls}_MP{mp}.f32")
    if os.path.exists(out):
        return out, "cached"
    body = json.dumps(S.body(ls, mp, dec))
    r = subprocess.run([PY, f"{BS}/engine/tools/render_ir.py", TREES[tree], body, out, "3000", str(B.SR)],
                       capture_output=True, text=True)
    return out, (r.stdout.strip().splitlines() or [r.stderr[-300:]])[-1]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--jobs", type=int, default=4); ap.add_argument("--only", default="")
    a = ap.parse_args(); os.makedirs(OUT, exist_ok=True)
    vs = [v for v in VARIANTS if not a.only or v in a.only.split(",")]
    todo = [(v, ls, mp) for v in vs for ls in B.SOURCES for mp in B.RECEIVERS]
    print("Eyring dial", EY_MID, "variants", vs, flush=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        for (o, msg) in ex.map(lambda t: job(*t), todo):
            print(os.path.basename(o), msg, flush=True)
