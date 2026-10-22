import sys, json, types, numpy as np
H = '/workspace/audit_1852/3_phase_acceptance_tests/harness'
sys.path[:0] = [H, H + '/lib']
import run_all as RA
from analyze import t60_bands
a = types.SimpleNamespace(sw=sys.argv[1], python=sys.executable, node='node', golden=H + '/golden', regen_golden=False, quick=False, perf_scale=1.0, workdir=None)
ctx = RA.Ctx(a); SR = 48000; out = {}
for scene in ('small_lock08', 'std_lock18'):
    body = dict(RA.SCENES[scene]); body.update({"colour_on": False, "early_wet": 0, "direct_wet": 0})
    x = ctx.render_ir(body, int(1000 * max(4, 2.5 * body['decay_s'])))
    t = t60_bands(x[:, 0], SR, bands=[250, 500, 1000, 2000, 4000, 8000])
    out[scene] = {str(k): round(float(v), 3) for k, v in t.items()} | {'dial': body['decay_s'], 'rms': float(np.sqrt(np.mean(x ** 2)))}
    print(scene, out[scene])
json.dump(out, open(sys.argv[2], 'w'), indent=1)
