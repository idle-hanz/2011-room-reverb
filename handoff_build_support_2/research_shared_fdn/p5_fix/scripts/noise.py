"""Noise floor of the P5 metric: per-mic (off) vs per-mic with the source moved 5/10/20 cm (same room, same mics)."""
import json, numpy as np
from p5lib import *
c = ctx(); ship = SW + '/static/wasm/live_stereo.wasm'; out = {}
for name, (body, t0, t1, secs) in P5_SCENES.items():
    base = c.play_ir(body, {"shared_tail": False}, secs, wasm=ship); c0 = TS._coh(base[:, 0], base[:, 1], t0, t1)
    for dx in (0.05, 0.10, 0.20, 0.40):
        b2 = dict(body); b2['sx'] = body.get('sx', 2.6) + dx   # app_server DEFAULTS sx = 2.6
        y = c.play_ir(b2, {"shared_tail": False}, secs, wasm=ship); c1 = TS._coh(y[:, 0], y[:, 1], t0, t1)
        e = [c1[f] - c0[f] for f in OCT]
        out[f'{name}|dx{dx}'] = dict(rms=round(float(np.sqrt(np.mean(np.square(e)))), 3), max=round(float(np.max(np.abs(e))), 3), dev=[round(v, 3) for v in e])
        print(name, dx, out[f'{name}|dx{dx}'], flush=True)
json.dump(out, open(P + '/data/noise_floor.json', 'w'), indent=1)
