from p5lib import *
c = ctx(); out = {}
for tag, w in (('ship', SW + '/static/wasm/live_stereo.wasm'), ('rebuild', P + '/c/rebuild_1840.wasm')):
    out[tag] = p5(c, w)
    for k, v in out[tag].items(): print(tag, k, v['rms'], v['max'], v['dev'], flush=True)
# bit-exact rebuild check
import numpy as np
for fl in (False, True):
    a = c.play_ir(dict(BASE, **TAIL), {"shared_tail": fl}, 1.0, wasm=SW + '/static/wasm/live_stereo.wasm')
    b = c.play_ir(dict(BASE, **TAIL), {"shared_tail": fl}, 1.0, wasm=P + '/c/rebuild_1840.wasm')
    out[f'rebuild_vs_ship_shared{fl}'] = float(np.max(np.abs(a - b))); print('rebuild diff', fl, out[f'rebuild_vs_ship_shared{fl}'])
# plain H (loop_semantics 1) for both off and on
out['plainH'] = p5(c, SW + '/static/wasm/live_stereo.wasm', over_on={"loop_semantics": 1}) if False else None
json.dump(out, open(P + '/data/baseline.json', 'w'), indent=1)
