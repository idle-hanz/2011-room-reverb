#!/usr/bin/env python3
"""TEST TOOL: replace every colour FIR in a live_fdn_params JSON by a K-biquad SOS record
[-2011, K, b0 b1 b2 a1 a2 ...] fitted to that FIR's magnitude (min-phase RBJ sections).
Usage: sosify_params.py in.json out.json [K=3]
Prints fit time and the worst dB error. (The proposed production path fits from the preset
parameters via a per-mic w-table instead: see FINDINGS.md.)"""
import sys, json, base64, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sos_fit as SF

src, dst = sys.argv[1], sys.argv[2]; K = int(sys.argv[3]) if len(sys.argv) > 3 else 3
P = json.load(open(src)); c = P.get('colour') or {}
fs = int(c.get('sr') or 48000); NF = 1 << 16
t0 = time.time(); worst = 0.0; out = []
for s in c.get('irs', []):
    ir = np.frombuffer(base64.b64decode(s), dtype=np.float32).astype(np.float64)
    H = np.fft.rfft(ir, NF); fr = np.fft.rfftfreq(NF, 1 / fs)
    db = 20 * np.log10(np.maximum(np.abs(H), 1e-12))
    tgt = lambda f: np.interp(f, fr, db)
    sos, _ = SF.fit(tgt, fs, K)
    worst = max(worst, SF.errors(sos, tgt, fs)[0])
    rec = np.concatenate([[-2011.0, float(K)], sos.reshape(-1)]).astype(np.float32)
    out.append(base64.b64encode(rec.tobytes()).decode('ascii'))
c['irs'] = out; P['colour'] = c
json.dump(P, open(dst, 'w'))
print(json.dumps({'n_irs': len(out), 'K': K, 'fit_s': round(time.time() - t0, 2), 'worst_db_20_20k': round(worst, 3)}))
