import sys, json
from multiprocessing import Pool
from p5lib import *
import screen
VS = sys.argv[1].split(','); OUTF = sys.argv[2]
def one(v):
    v, r = screen.one(v); r['p7'] = p7(ctx(), P + f'/c/{v}.wasm'); return v, r
if __name__ == '__main__':
    out = {}
    try: out = json.load(open(P + '/data/' + OUTF))
    except Exception: pass
    with Pool(8) as pool:
        for v, r in pool.imap_unordered(one, VS):
            out[v] = r
            s = ' '.join(f"{k}:{x['rms']:.3f}/{x['max']:.3f}" for k, x in r['p5'].items())
            allok = all(x['p5_ok'] for x in r['p5'].values())
            print(f"{v:12s} {'PASS' if allok else '----'} p7={r['p7']['null_db']} off={r['off_vs_ship']:.0e} | {s} | comb {r['comb']['on']['comb_db']} ac19 {r['comb']['on']['ac1936']} acmax {r['comb']['on']['acmax']}", flush=True)
            json.dump(out, open(P + '/data/' + OUTF, 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
