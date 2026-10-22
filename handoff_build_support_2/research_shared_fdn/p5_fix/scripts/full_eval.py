import sys, json, numpy as np
from multiprocessing import Pool
from p5lib import *
CANDS = {'ship': SW + '/static/wasm/live_stereo.wasm', 'dv133': P + '/c/vd/dv133_s1.wasm', 'dv33_j45': P + '/c/vd/dv33_j45.wasm',
         'j600': P + '/c/v/j600.wasm', 'dv133_s2': P + '/c/vd/dv133_s2.wasm', 'm1019_j45': P + '/c/vm/m1019_j45.wasm', 'm1019_j60': P + '/c/vm/m1019_j60.wasm', 'm1019_j30': P + '/c/vm/m1019_s1.wasm', 'R750s7': P + '/c/vf/f1_2_w750r1j45s7.wasm', 'R500s7': P + '/c/vf/f1_2_w500r1j45s7.wasm', 'R750s1': P + '/c/vf/f1_2_w750r1j45.wasm', 'F12': P + '/c/vf/f1_2.wasm'}
SHIP = CANDS['ship']
def job(a):
    name, what = a; c = ctx(); w = CANDS[name]
    if what == 'p5': return name, what, p5(c, w, off_wasm=SHIP)
    if what == 'hold': return name, what, p5(c, w, scenes=HOLD, off_wasm=SHIP)
    if what == 'p4': return name, what, p4(c, w)
    if what == 'p7': return name, what, p7(c, w)
    if what == 'p9': return name, what, p9(c, w)
    if what == 'comb': return name, what, comb(c, w)
    if what == 'p1':
        out = {}
        for sc, body in {'def_1': dict(BASE), 'def_2': dict(BASE, two_sources=True, source_balance=0.0), 'big_1': dict(BASE, **BIG),
                         'big_2': dict(BASE, **BIG, two_sources=True, source_balance=0.0), 'bin_2': dict(BASE, two_sources=True, source_balance=0.0, mic_setup='binaural')}.items():
            for ov in ({}, {"colour_on": False}):
                a_ = c.play_ir(body, ov, 1.0, wasm=SHIP); b_ = c.play_ir(body, ov, 1.0, wasm=w)
                out[sc + ('_off' if ov else '_on')] = float(np.max(np.abs(a_ - b_)))
        bb = dict(BASE, two_sources=True, source_balance=0.0, mic_setup='binaural', **TAIL)
        out['P8_binaural_flag'] = float(np.max(np.abs(c.play_ir(bb, {"shared_tail": True}, 1.5, wasm=w) - c.play_ir(bb, {"shared_tail": False}, 1.5, wasm=w))))
        return name, what, out
if __name__ == '__main__':
    names = sys.argv[1].split(',') if len(sys.argv) > 1 else list(CANDS)
    whats = sys.argv[2].split(',') if len(sys.argv) > 2 else ['p1', 'p5', 'hold', 'p4', 'p7', 'p9', 'comb']
    try: res = json.load(open(P + '/data/full_eval.json'))
    except Exception: res = {}
    with Pool(8) as pool:
        for n, wt, r in pool.imap_unordered(job, [(n, w) for n in names for w in whats]):
            res.setdefault(n, {})[wt] = r
            if wt in ('p5', 'hold'): print(n, wt, {k: (v['rms'], v['max'], v['p6']) for k, v in r.items()}, flush=True)
            else: print(n, wt, json.dumps(r, default=lambda o: o.item() if hasattr(o, 'item') else str(o))[:400], flush=True)
            json.dump(res, open(P + '/data/full_eval.json', 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
