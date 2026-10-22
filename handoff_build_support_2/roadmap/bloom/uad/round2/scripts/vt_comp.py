# Volterra-only test on compressors: fit a static (gain-blind) generalised Hammerstein to the compressor's
# own ESS records at 4 levels, then predict program material. Compares with our preset model (+UAD linear FR).
import numpy as np, sys, csv, json
sys.path.insert(0, '.')
import io2, volterra as V
rows = []
for unit, preset in (('ssl_4_auto', 'glue'), ('la2as_pr50', 'natural'), ('fet_all', 'room_crush'), ('fc_t5', 'swell'), ('dis_nuke_room', 'nuke')):
    recs = []
    for L in (-30, -18, -6, 6):
        id_ = 'cess_%s_%+d' % (unit, L)
        if id_ in io2._J: recs.append(io2.rec(id_))
    for N in (1, 5):
        K = V.fit_hammerstein(recs, N=N, M=2048)
        for pk in ('mix', 'drums', 'vocal'):
            for ab, lab in (('a', 'base'), ('b', '+8 dB')):
                id_ = 'prog_%s_%s_%s' % (unit, pk, ab)
                if id_ not in io2._J: continue
                x, y = io2.rec(id_); yh = V.apply_hammerstein(x, K)
                c = np.dot(y, yh) / np.dot(yh, yh); sl = slice(4096, len(x) - 4096)
                e = V.nmse_db(y, c * yh, sl)
                rows.append(dict(unit=unit, preset=preset, model='volterra_ham%d' % N, program=pk, level=lab, null_db=round(e, 1), n_records=len(recs)))
                print(rows[-1], flush=True)
with open('/workspace/uad2/an/vt_comp.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
