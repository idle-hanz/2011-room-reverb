# Runs ON THE PC. Real-music validation (nulls, GR error) + listen clips. Real audio never leaves the PC.
# usage: python real_eval.py <R3DIR> <LISTENDIR>
import os, sys, json, csv, wave, numpy as np
R3 = sys.argv[1]; LST = sys.argv[2]; BOX = os.path.join(R3, 'box').replace('\\', '/')
os.environ['UADROOT'] = BOX; sys.path.insert(0, BOX + '/uad3'); sys.path.insert(0, BOX + '/uad2/scripts')
KZ = np.load(BOX + '/uad3/kernels.npz')
import an_prog_lib as AP
AP._H1.update({k[3:]: KZ[k] for k in KZ.files if k.startswith('h1_')}); AP.g_ss = lambda u: float(KZ['gss_' + u])
import prelib; prelib._K.update({(k[5:], 8192): KZ[k] for k in KZ.files if k.startswith('klin_')})
import prog3, models as Mo
SR = 48000; J = {j['id']: j for j in json.load(open(os.path.join(R3, 'jobs_r3.json')))}
def rec(i):
    j = J[i]; x = np.load(os.path.join(R3, 'inputs', j['input'])).astype(np.float32)
    if x.ndim == 2: x = x[0]
    x = (x * np.float32(10 ** (j.get('gain_db', 0) / 20))).astype(float)
    y = np.load(os.path.join(R3, 'out', i + '.npz'))['y'].astype(float); y = y[0] if y.ndim == 2 else y
    n = min(len(x), len(y)); return x[:n], y[:n]
def wav24(path, v):
    q = np.clip(np.round(v * 8388607), -8388608, 8388607).astype('<i4'); b = q.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(path, 'wb') as w: w.setnchannels(1); w.setsampwidth(3); w.setframerate(SR); w.writeframes(b)
def kweight_rms(v):  # loudness match on K-weighted RMS (BS.1770 pre-filter, ungated)
    from scipy.signal import lfilter
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1, -2, 1], [1, -1.99004745483398, 0.99007225036621]
    return np.sqrt(np.mean(lfilter(b2, a2, lfilter(b1, a1, v)) ** 2))
def write_set(name, sigs, a0=int(0.5 * SR), a1=int(5.5 * SR)):
    os.makedirs(LST, exist_ok=True); seg = {k: v[a0:a1] for k, v in sigs.items()}
    L = {k: kweight_rms(v) for k, v in seg.items()}; ref = min(L.values())
    n = int(0.01 * SR); w = np.ones(a1 - a0); w[:n] = np.linspace(0, 1, n); w[-n:] = w[:n][::-1]
    out = {k: v * ref / L[k] * w for k, v in seg.items()}; g = 10 ** (-1 / 20) / max(np.abs(v).max() for v in out.values())
    for k, v in out.items(): wav24(os.path.join(LST, '%s__%s.wav' % (name, k)), v * g)
UNITP = Mo.PRESET_UNIT; PROGS = ('drums', 'bass', 'guitar', 'vocal', 'mix')
LISTEN_PROG = {'natural': ['vocal', 'mix'], 'room_crush': ['drums', 'mix'], 'nuke': ['drums', 'bass'], 'swell': ['mix', 'guitar'], 'glue': ['mix', 'drums']}
if __name__ == '__main__':
    what = sys.argv[3] if len(sys.argv) > 3 else 'all'
    if what in ('all', 'comp'):
        rows = []
        for p, u in UNITP.items():
            for pk in PROGS:
                for ab in ('a', 'b'):
                    x, y = rec('rprog_%s_%s_%s' % (u, pk, ab)); r, sig = prog3.compare(p, u, x, y, 'real_%s_%s' % (pk, ab)); rows.append(r)
                    print(*r.values(), flush=True)
                    if ab == 'b' and pk in LISTEN_PROG[p]:
                        write_set('comp_%s_real_%s_hot' % (p, pk), {'A_uad_%s' % u: y, 'B_bloom_current': sig['yc'], 'B3_proto': sig['ype']})
            with open(os.path.join(R3, 'real_comp_nulls.csv'), 'w', newline='') as f:
                w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
    if what in ('all', 'pre'):
        CH = json.load(open(BOX + '/uad3/pre_choice.json')); rows = []
        for pre in ('neve', 'u610a'):
            m = prelib.Pre(pre, CH[pre]['cfg']); th = CH[pre]['th']
            for pk in PROGS:
                for L in ('+0', '-6'):
                    i = 'rpprog_%s_%s_%s' % (pre, pk, L); x, y = rec(i)
                    yl = prelib.lin(x, m.k); ym = m.run(x, th)
                    sl = slice(4096, len(x) - 4096); nl = lambda a, b: 10 * np.log10(np.sum((prelib.bl(a)[sl] - prelib.bl(b)[sl]) ** 2) / np.sum(prelib.bl(a)[sl] ** 2))
                    r = dict(pre=pre, prog=pk, drive=L, null_linear_db=round(nl(y, yl), 2), null_model_db=round(nl(y, ym), 2))
                    r['gain_db'] = round(r['null_model_db'] - r['null_linear_db'], 2); rows.append(r); print(*r.values(), flush=True)
                    if L == '+0' and pk in ('vocal', 'drums', 'mix'):
                        write_set('pre_%s_real_%s_drive' % (pre, pk), {'A_uad': y, 'B_bloom_current_linear': yl, 'B3_proto': ym})
        with open(os.path.join(R3, 'real_pre_nulls.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
