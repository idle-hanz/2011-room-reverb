"""Find a mirror pairing that commutes with the Sylvester H (bit-permutation involution), keeps i%3,
and keeps as many LIVE_32 images at their original index as possible (index 0 must stay (0,2,0))."""
import itertools, numpy as np
from scipy.optimize import linear_sum_assignment
from make_variants import ORIG, SYM
def perm_from_bits(swaps):
    def f(i):
        b = [(i >> k) & 1 for k in range(5)]
        for a, c in swaps: b[a], b[c] = b[c], b[a]
        return sum(v << k for k, v in enumerate(b))
    return f
cands = {'(b0b2)(b1b3)': [(0,2),(1,3)], '(b0b4)(b1b3)': [(0,4),(1,3)], '(b2b4)(b1b3)': [(2,4),(1,3)]}
best = None
for name, sw in cands.items():
    t = perm_from_bits(sw)
    assert all(i % 3 == t(i) % 3 for i in range(32))
    fixed = [i for i in range(32) if t(i) == i]; pairs = [(i, t(i)) for i in range(32) if t(i) > i]
    singles = [n for n in dict.fromkeys(SYM) if n[0] == 0 and SYM.count(n) == 1]
    dups = [n for n in dict.fromkeys(SYM) if n[0] == 0 and SYM.count(n) == 2]
    pos = sorted(set(n for n in SYM if n[0] > 0))
    # cost: -kept positions vs ORIG (SYM index 23 counts as its original slot for (-1,-1,0))
    def kept(i, n): return 1 if SYM[i] == n else 0
    # singles -> fixed
    C = np.array([[-(kept(i, n)) + (100 if (i == 0 and n != (0, 2, 0)) else 0) for i in fixed] for n in singles])
    r, c = linear_sum_assignment(C); out = [None] * 32
    for a, b in zip(r, c): out[fixed[b]] = singles[a]
    items = [(n, (-n[0], n[1], n[2])) for n in pos] + [(d, d) for d in dups]
    C2 = np.zeros((len(items), len(pairs))); orient = {}
    for a, (p, q) in enumerate(items):
        for b, (i, j) in enumerate(pairs):
            k1 = kept(i, p) + kept(j, q); k2 = kept(i, q) + kept(j, p)
            C2[a, b] = -max(k1, k2); orient[(a, b)] = k1 >= k2
    r, c = linear_sum_assignment(C2)
    for a, b in zip(r, c):
        (p, q), (i, j) = items[a], pairs[b]
        if orient[(a, b)]: out[i], out[j] = p, q
        else: out[i], out[j] = q, p
    assert sorted(out) == sorted(SYM)
    for i in range(32): assert out[t(i)] == (-out[i][0], out[i][1], out[i][2])
    nk = sum(kept(i, out[i]) for i in range(32))
    print(name, 'kept', nk, 'direct at', out.index((0, 0, 0)), 'idx0', out[0])
    if best is None or nk > best[0]: best = (nk, name, out)
print('BEST', best[1], best[0]); print(best[2])
import json; json.dump({'tau': best[1], 'order': best[2]}, open('tau2.json', 'w'))
