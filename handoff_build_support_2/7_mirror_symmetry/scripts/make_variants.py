"""Box-only variant trees for the mirror-asymmetry study. Never touches the PC."""
import shutil, re, os, sys
from pathlib import Path
W = Path('/workspace/build_support_2/work')
OUT = W / 'mirror'
ORIG = [(0,2,0),(0,1,0),(0,0,0),(0,-1,0),(0,-2,0),(0,2,1),(0,1,1),(0,1,1),(0,0,1),(0,0,1),
 (1,2,1),(1,1,1),(1,0,1),(1,-1,1),(1,-2,1),(1,2,0),(1,1,0),(1,0,0),(1,-1,0),(1,-2,0),
 (-1,2,0),(-1,1,0),(-1,0,0),(-1,-2,0),(-1,-2,0),(-1,2,1),(-1,1,1),(-1,0,1),(-1,-1,1),(-1,-2,1),
 (0,1,2),(0,0,2)]
SYM = list(ORIG); SYM[23] = (-1,-1,0)
def tau(i):
    b = [(i >> k) & 1 for k in range(5)]
    b[0], b[2] = b[2], b[0]; b[1], b[3] = b[3], b[1]
    return sum(v << k for k, v in enumerate(b))
def tau_order(imgs):
    fixed = [i for i in range(32) if tau(i) == i]
    pairs = [(i, tau(i)) for i in range(32) if tau(i) > i]
    selfm = [n for n in imgs if n[0] == 0]
    pos = sorted([n for n in imgs if n[0] > 0])
    from collections import Counter
    cnt = Counter(selfm)
    singles = [n for n in dict.fromkeys(selfm) if cnt[n] == 1]
    dups = [n for n in dict.fromkeys(selfm) if cnt[n] == 2]
    assert len(fixed) == len(singles) == 8 and len(pairs) == 12 and len(pos) == 10 and len(dups) == 2, (len(singles), len(dups), len(pos))
    out = [None] * 32
    # direct first fixed slot (0)
    singles.sort(key=lambda n: (n != (0,0,0), n))
    for i, n in zip(fixed, singles): out[i] = n
    for (i, j), n in zip(pairs, pos + dups):
        out[i] = n; out[j] = (-n[0], n[1], n[2])
    assert sorted(out) == sorted(imgs), 'not a permutation'
    for i in range(32):
        a, b = out[i], out[tau(i)]
        assert b == (-a[0], a[1], a[2]) and i % 3 == tau(i) % 3
    return out
TAU = tau_order(SYM)
def fmt(imgs): return 'LIVE_32: Tuple[Tuple[int, int, int], ...] = (\n' + ''.join(f'    {n},\n' for n in imgs) + ')\n'
def make(name, src, imgs=None, nopeak=False):
    d = OUT / name
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(W / src / 'software', d / 'software')
    if not (d / 'mic_fitter').exists(): shutil.copytree(W / 'new1001' / 'mic_fitter', d / 'mic_fitter')
    ef = d / 'software/engine/early_field.py'
    t = ef.read_text()
    if imgs is not None:
        t2 = re.sub(r'LIVE_32: Tuple\[Tuple\[int, int, int\], \.\.\.\] = \(\n.*?\n\)\n', fmt(imgs), t, count=1, flags=re.S)
        assert t2 != t or imgs == ORIG; ef.write_text(t2)
    if nopeak:
        rp = d / 'software/render_pipeline.py'; s = rp.read_text()
        s2 = s.replace('DEFAULT_DEPTH = 1.5', 'DEFAULT_DEPTH = 0.0', 1); assert s2 != s; rp.write_text(s2)
    for p in d.rglob('__pycache__'): shutil.rmtree(p)
    print('made', name)
if __name__ == '__main__':
    print('TAU order:', TAU)
    make('base', 'new1001')
    make('sym', 'new1001', SYM)
    make('tau', 'new1001', TAU)
    make('base_nopeak', 'new1001', None, True)
    make('sym_nopeak', 'new1001', SYM, True)
    make('p6', 'p6')
    make('p6_sym', 'p6', SYM)
    make('p6_tau', 'p6', TAU)
