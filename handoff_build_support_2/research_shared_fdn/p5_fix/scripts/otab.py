"""Mirror-safe readout signs: L reads o[i], R reads o[pi(i)], C reads +1. At LF the
L/R correlation of the shared (mirror-symmetric) network scales with o.Po/32 = (32-4m)/32,
m = number of the 12 non-fixed mirror pairs given opposite signs. Ship: o = +1, m = 0."""
import json, sys, random
sys.path.insert(0, '.')
from mirror_dvec import pi
pairs = sorted({tuple(sorted((k, pi(k)))) for k in range(32) if pi(k) != k})
def make(m, seed):
    r = random.Random(seed); o = [1] * 32; ch = r.sample(pairs, m)
    for a, b in ch: o[b] = -1        # flip the higher index of each chosen pair
    return o, ch
if __name__ == '__main__':
    out = {}
    for m in [int(x) for x in sys.argv[1].split(',')]:
        for s in range(1, int(sys.argv[2]) + 1):
            o, ch = make(m, 100 * m + s)
            out[f'o{m}_{s}'] = dict(m=m, seed=100 * m + s, o=o, pairs=ch, oPo=sum(o[k] * o[pi(k)] for k in range(32)))
    json.dump(out, open('../data/otabs.json', 'w'), indent=1)
    print({k: v['oPo'] for k, v in out.items()})
