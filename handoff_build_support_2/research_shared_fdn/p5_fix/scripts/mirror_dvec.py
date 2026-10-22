"""Mirror-invariant sign vectors for the shared loop. The mirror maps line k to pi(k),
pi = swap index bits (b0 b4)(b1 b3) (fdn.py LOOP_COLUMN_D comment). pi commutes with
Sylvester H, so H.D stays mirror-safe iff d[pi(k)] == d[k]."""
import json, numpy as np, sys
def pi(k):
    b = [(k >> i) & 1 for i in range(5)]; b[0], b[4] = b[4], b[0]; b[1], b[3] = b[3], b[1]
    return sum(v << i for i, v in enumerate(b))
def hada(n):
    h = np.array([[1.0]])
    while h.shape[0] < n: h = np.block([[h, h], [h, -h]])
    return h
H = hada(32)
CS = np.array([1, -1, -1, -1, -1, -1, 1, -1, -1, 1, -1, 1, 1, 1, 1, 1, -1, 1, 1, 1, -1, 1, 1, 1, -1, 1, 1, 1, -1, 1, 1, 1.0])
P = np.zeros((32, 32)); [P.__setitem__((pi(k), k), 1) for k in range(32)]
def inv(d): return all(d[pi(k)] == d[k] for k in range(32))
def walsh_peak(d): return float(np.max(np.abs(H @ d)) / 32)
orbits = sorted({tuple(sorted((k, pi(k)))) for k in range(32)})
def from_seed(seed):
    u = seed & 0xffffffff; d = np.ones(32)
    for o in orbits:
        u = (u * 1664525 + 1013904223) & 0xffffffff; v = -1.0 if (u >> 31) else 1.0
        for k in o: d[k] = v
    if d[0] < 0: d = -d   # d0=+1 (orbit of 0 is {0})
    return d
if __name__ == '__main__':
    print('pi commutes with H:', np.allclose(P @ H @ P.T, H), ' CSIGN_D invariant:', inv(CS), ' walsh peak', walsh_peak(CS), ' orbits', len(orbits))
    seeds = [int(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else list(range(1001, 1025))
    out = {}
    for s in seeds:
        d = from_seed(s); assert inv(d)
        wp = walsh_peak(d)
        if wp >= 0.999: continue
        out[f'm{s}'] = dict(seed=s, d=[int(v) for v in d], walsh_peak=wp, sum=int(d.sum()))
    json.dump(out, open('../data/mirror_dvecs.json', 'w'), indent=1)
    for k, v in out.items(): print(k, v['walsh_peak'], v['sum'])
