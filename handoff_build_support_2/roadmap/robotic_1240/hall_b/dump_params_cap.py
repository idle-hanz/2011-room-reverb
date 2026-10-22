"""dump_params.py + optional cap on diffusion_scale_from_room (env DIFCAP, metres^2 units of the scale)."""
import sys, json, os
sw = os.path.abspath(sys.argv[1]); sys.path[:0] = [sw, os.path.join(sw, 'engine')]; os.chdir(sw)
import app_server as A
import render_pipeline as RP
cap = os.environ.get('DIFCAP')
if cap:
    _o = RP.diffusion_scale_from_room
    RP.diffusion_scale_from_room = lambda room, *a, **k: min(_o(room, *a, **k), float(cap))
body = dict(A.DEFAULTS); body.update(json.loads(sys.argv[2]))
if len(sys.argv) > 4: body['sample_rate'] = int(sys.argv[4])
p = A.params_from_body(body); out = A.live_fdn_params(p)
json.dump(out, open(sys.argv[3], 'w'))
print(json.dumps({'dffs_c': [round(v, 3) for v in out['buses']['c']['dffs']], 'parity': p.get('reaktor_parity')}))
