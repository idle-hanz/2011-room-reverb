"""Dump live_fdn_params (the exact JSON the page sends to Play) for a scene.
Usage: python dump_params.py <software_dir> '<json overrides>' out.json [sample_rate]
Runs the snapshot code read-only (imports app_server for params_from_body)."""
import sys, json, os
sw = os.path.abspath(sys.argv[1])
sys.path[:0] = [sw, os.path.join(sw, 'engine')]
os.chdir(sw)
sys.path.insert(0,'/workspace/audit_1852/heights'); import hpatch as _hp; _hp.apply(dict(__import__('json').loads(sys.argv[2])))
import app_server as A
body = dict(A.DEFAULTS)
body.update(json.loads(sys.argv[2]))
if len(sys.argv) > 4: body['sample_rate'] = int(sys.argv[4])
p = A.params_from_body(body)
out = A.live_fdn_params(p)
json.dump(out, open(sys.argv[3], 'w'))
c = out.get('colour') or {}
print(json.dumps({'g': out['g'], 'gsqrtN': out['g'] * 32 ** 0.5, 'mean_delay_ms': out['mean_delay_ms'], 'decay_s': out['decay_s'],
      'makeup': out['makeup'], 'colour_on': c.get('on'), 'colour_sr': c.get('sr'), 'n_irs': len(c.get('irs') or []),
      'dly_c_min_max': [min(out['buses']['c']['delay_ms']), max(out['buses']['c']['delay_ms'])],
      'dffs_c_min_max': [min(out['buses']['c']['dffs']), max(out['buses']['c']['dffs'])]}))
