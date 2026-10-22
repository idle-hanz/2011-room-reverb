import sys, json, time, numpy as np
from harness import *
import freqdecay as FD
name, mode = sys.argv[1], sys.argv[2]; ov = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
b = body(**ov); p = A.params_from_body(dict(b))
if mode != "none":
    r = FD.enable(p["W"], p["H"], p["L"], float(p["decay_s"]), float(p["humidity"]), p["surfaces"], mode)
    print(name, "target T(f) at octaves:", [round(float(x) * p["decay_s"], 3) for x in r(FD.BANDS)], flush=True)
t = time.time(); ir, info, _ = render_ir(b); np.save(f"ir_{name}.npy", ir)
import fdn as F
rep = (F.FREQ_DECAY or {}).get("report", [])
print(name, "secs", round(time.time() - t, 1), "worst line T60 error at octaves:", [round(x * 100, 2) for x in rep], flush=True)
