# Measure a model exactly like round 2 did: 1 kHz static, quadrature step attack, burst timing.
import numpy as np, json, sys
sys.path.insert(0, '/workspace/uad2/scripts'); sys.path.insert(0, '/workspace/uad3')
import io2, siglib2, BD, QA, dyn3
SR = 48000; LV = list(range(-45, 13, 3)); ST = 72000; KEEP = 24000
X1K = np.load(io2.I + 'st_1000_1p5.npy').astype(float)
UNIT = {'natural': 'la2as_pr50', 'glue': 'ssl_4_auto', 'room_crush': 'fet_all', 'nuke': 'dis_nuke', 'swell': 'fc_t5'}
QAID = {'room_crush': 'qa_fet_all_att4.0', 'nuke': 'qa_dis_nuke_att4.5', 'natural': 'qa_la2as_pr50_def', 'glue': 'qa_ssl_4_auto_att10.0', 'swell': 'qa_fc_t2_l_t5.0_r_t5.0'}
FIT = json.load(open('/workspace/uad2/an/static_fit.json'))
def static(p, P):
    y, _ = dyn3.run(p, X1K, P)
    seg = np.stack([y[(i + 1) * ST - KEEP:(i + 1) * ST] for i in range(len(LV))])
    g = 20 * np.log10(np.sqrt(2 * np.mean(seg ** 2, 1))) - np.array(LV); return g[0] - g
def attack(p, P):
    base = QAID[p]; sp = io2.job(base + '_s')['spec']; out = []
    for nm in ('s', 'c'):
        x = np.concatenate([np.zeros(SR), siglib2.make(io2.job(base + '_' + nm)['spec'])]); y, _ = dyn3.run(p, x, P); out.append(y[SR:])
    gr, i0, i1 = QA.gr_trace(out[0], out[1], sp); return QA.met(gr, i0, i1)
_BDIDS = None
def bursts(p, P):
    rows = []
    for id_ in sorted(k for k in io2._J if k.startswith('bd_%s_' % UNIT[p])):
        sp = io2.job(id_)['spec']; x = np.concatenate([np.zeros(SR), siglib2.make(sp)]); y, _ = dyn3.run(p, x, P)
        m, _ = BD.metrics(BD.env(x[SR:]), BD.env(y[SR:]), sp)
        ei, eo, dec = io2.env_rec(id_); mu, _ = BD.metrics(ei, eo[0], sp)
        rows.append((id_.split('_')[-2], sp['burst_s'], mu, m))
    return rows
UAD_STATIC = {p: np.array(FIT[p]['gr_uad']) for p in FIT}
