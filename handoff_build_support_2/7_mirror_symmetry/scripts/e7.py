from mirror_lib import *
import subprocess, json, sys
def r2(tree, kind):
    b = body(kind); b['ir_length_ms'] = 2500
    out = f'/tmp/r2_{tree}_{kind}.f32'
    r = subprocess.run([sys.executable, 'render2_ir.py', f'/workspace/build_support_2/work/mirror/{tree}/software', json.dumps(b), out, '2500', '48000'], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-800:])
    return np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)
res = {}
for tree in sys.argv[1].split(','):
    A = r2(tree, 'twoA'); B = r2(tree, 'twoB')
    res[tree] = compare(A, B, f'{tree:6s} RENDER two-source A vs mirB measured')
    P = play(tree, 'twoA')
    compare(A, P[:, ::-1], f'{tree:6s} RENDER twoA vs PLAY twoA (same side)')
json.dump(res, open('e7.json', 'w'), indent=1, default=float)
