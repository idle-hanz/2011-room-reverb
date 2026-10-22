"""Image-arrival directions from the p5 engine's own compute_taps (read-only import).

Produces head-relative azimuth/elevation (SOFA convention: az CCW from front,
positive = left; el up) for every image tap, for a few scenes. Used to size the
binaural colour grid against MAX_IRS = 64. Nothing in software/ is modified.
"""
import json, math, sys
from pathlib import Path
P5 = Path('/workspace/build_support_2/work/p5/software')
sys.path.insert(0, str(P5))
from engine import early_field as ef  # noqa: E402

def head_dirs(room, src, head, yaw_deg=0.0, n=32):
    stand = ef.MicStand(cx=head[0], cy=head[1], cz=head[2], space=0.18, car_omni=0.0,
                        mlalr=math.radians(-90), mralr=math.radians(90), pattern_l='omni', pattern_r='omni', pattern_c='omni')
    taps = ef.compute_taps(room, src, stand, hadamard_n=n)
    psi = math.radians(yaw_deg)
    look = (ef.YAW_X_SIGN * math.sin(psi), 0.0, math.cos(psi))
    right = (math.cos(psi), 0.0, -ef.YAW_X_SIGN * math.sin(psi))
    out = []
    for t in taps:
        dx, dy, dz = (t.position[i] - head[i] for i in range(3))
        r = math.sqrt(dx*dx + dy*dy + dz*dz)
        f = (dx*look[0] + dz*look[2]) / r
        rt = (dx*right[0] + dz*right[2]) / r
        az = math.degrees(math.atan2(-rt, f))  # + = left (SOFA)
        el = math.degrees(math.asin(max(-1, min(1, dy / r))))
        out.append({'n': list(t.n), 'az': az, 'el': el, 'r': r, 'order': t.order})
    return out, taps

SCENES = {
    'default_A': dict(room=(6.0, 3.0, 8.0), src=(2.6, 1.2, 4.75), head=(3.0, 1.5, 1.5)),
    'default_B': dict(room=(6.0, 3.0, 8.0), src=(3.4, 1.2, 4.75), head=(3.0, 1.5, 1.5)),
    'small_A': dict(room=(4.0, 2.5, 5.0), src=(1.5, 1.2, 3.5), head=(2.0, 1.2, 1.2)),
    'hall_A': dict(room=(20.0, 10.0, 30.0), src=(8.0, 1.5, 15.0), head=(10.0, 1.5, 5.0)),
}

if __name__ == '__main__':
    res = {}
    for k, s in SCENES.items():
        d, taps = head_dirs(**s)
        res[k] = d
    Path('reports').mkdir(exist_ok=True)
    Path('reports/engine_directions.json').write_text(json.dumps(res, indent=1))
    for k, d in res.items():
        els = sorted(round(x['el']) for x in d)
        print(k, len(d), 'el range', els[0], els[-1], 'orders', sorted(set(x['order'] for x in d)))
