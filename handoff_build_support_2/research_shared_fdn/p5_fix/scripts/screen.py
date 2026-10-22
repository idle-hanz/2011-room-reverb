import sys, json, numpy as np
from multiprocessing import Pool
from p5lib import *
VS = sys.argv[1].split(','); OUTF = sys.argv[2] if len(sys.argv) > 2 else 'screen.json'
def one(v):
    c = ctx(); w = P + (f'/c/{v}.wasm' if '/' in v else f'/c/v/{v}.wasm'); ship = SW + '/static/wasm/live_stereo.wasm'
    r = dict(p5=p5(c, w, off_wasm=ship))
    off_d = c.play_ir(dict(BASE, **TAIL), {"shared_tail": False}, 1.0, wasm=w); off_s = c.play_ir(dict(BASE, **TAIL), {"shared_tail": False}, 1.0, wasm=ship)
    r['off_vs_ship'] = float(np.max(np.abs(off_d - off_s)))
    on_d = c.play_ir(dict(BASE, **TAIL), {"shared_tail": True}, 1.0, wasm=w); on_s = c.play_ir(dict(BASE, **TAIL), {"shared_tail": True}, 1.0, wasm=ship)
    r['on_vs_ship'] = float(np.max(np.abs(on_d - on_s)))
    r['comb'] = comb(c, w)
    return v, r
if __name__ == '__main__':
    out = {}
    try: out = json.load(open(P + '/data/' + OUTF))
    except Exception: pass
    with Pool(min(len(VS), 8)) as pool:
        for v, r in pool.imap_unordered(one, VS):
            out[v] = r
            s = ' '.join(f"{k}:{x['rms']:.3f}/{x['max']:.3f}" for k, x in r['p5'].items())
            print(f"{v:9s} off={r['off_vs_ship']:.0e} on={r['on_vs_ship']:.1e} | {s} | comb on {r['comb']['on']['comb_db']} ac19 {r['comb']['on']['ac1936']} acmax {r['comb']['on']['acmax']}", flush=True)
            json.dump(out, open(P + '/data/' + OUTF, 'w'), indent=1)
