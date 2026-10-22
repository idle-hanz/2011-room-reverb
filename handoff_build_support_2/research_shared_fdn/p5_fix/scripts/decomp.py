"""Why does H*D raise L/R coherence in the shared loop? Per-line output decomposition (DBG_LINE builds:
only line k reaches the mix). L = sum_k L_k, R = sum_k R_k. For each octave:
  coh       : test coherence (sqrt of mean msc in band), full signal
  coh_diag  : coherence if the 32 line signals were mutually incoherent (cross-line CSD terms dropped)
  gainL/R   : P(sum_k L_k) / sum_k P(L_k)  (>1: lines add in phase inside one mic)
  xshare    : |cross-line part of CSD_LR| / |diag part|"""
import sys, json, numpy as np
from scipy import signal
from p5lib import *
c = ctx(); W = P + '/c/dbg/line%d.wasm'
scen = {k: P5_SCENES[k] for k in sys.argv[1].split(',')} if len(sys.argv) > 1 else {k: P5_SCENES[k] for k in ('default', 'ortf_wide', 'big')}
cfgs = {'off_HD': ({"shared_tail": False}, ), 'on_HD': ({"shared_tail": True}, ), 'off_H': ({"shared_tail": False, "loop_semantics": 1}, ), 'on_H': ({"shared_tail": True, "loop_semantics": 1}, )}
def band(f, fc): return (f >= fc / 2 ** 0.5) & (f < fc * 2 ** 0.5)
res = {}
for sn, (body, t0, t1, secs) in scen.items():
    a, b = int(t0 * SR), int(t1 * SR)
    for cn, (over,) in cfgs.items():
        X = [c.play_ir(body, over, secs, wasm=W % k)[a:b] for k in range(32)]
        full = c.play_ir(body, over, secs)[a:b]
        lin_err = float(np.max(np.abs(sum(X) - full)) / np.max(np.abs(full)))
        kw = dict(fs=SR, nperseg=2048)
        f, Sll = signal.welch(full[:, 0], **kw); _, Srr = signal.welch(full[:, 1], **kw); _, Slr = signal.csd(full[:, 0], full[:, 1], **kw)
        dLL = sum(signal.welch(x[:, 0], **kw)[1] for x in X); dRR = sum(signal.welch(x[:, 1], **kw)[1] for x in X)
        dLR = sum(signal.csd(x[:, 0], x[:, 1], **kw)[1] for x in X)
        row = {}
        for fc in OCT:
            m = band(f, fc)
            coh = float(np.sqrt(np.mean(np.abs(Slr[m]) ** 2 / (Sll[m] * Srr[m]))))
            cd = float(np.sqrt(np.mean(np.abs(dLR[m]) ** 2 / (dLL[m] * dRR[m]))))
            row[fc] = dict(coh=round(coh, 3), coh_diag=round(cd, 3), gainL=round(float(np.sum(Sll[m]) / np.sum(dLL[m])), 2),
                           gainR=round(float(np.sum(Srr[m]) / np.sum(dRR[m])), 2), xshare=round(float(np.mean(np.abs(Slr[m] - dLR[m])) / np.mean(np.abs(dLR[m]))), 2))
        res[f'{sn}|{cn}'] = dict(lin_err=lin_err, oct=row)
        print(sn, cn, 'lin', f'{lin_err:.1e}', ' '.join(f"{fc}:{r['coh']}/{r['coh_diag']}/g{r['gainL']}/x{r['xshare']}" for fc, r in row.items()), flush=True)
json.dump(res, open(P + '/data/decomp_' + '_'.join(scen) + '.json', 'w'), indent=1)
