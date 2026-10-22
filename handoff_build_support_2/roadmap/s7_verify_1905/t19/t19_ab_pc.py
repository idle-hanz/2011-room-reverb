"""t19 A/B on one machine, same minute: alternate wasm files under the same software tree and t19 scene.
Usage (PC, from the folder holding this file):
  python t19_ab_pc.py <software_dir> <harness_dir> <rounds> name=path.wasm [name=path.wasm ...]
  'name=ship' uses the tree's own static/wasm/live_stereo.wasm.
Prints per-round play_mean_ms and min/median per wasm. Read-only: writes only to a temp work dir."""
import sys, os, json, types, tempfile, statistics
sw, har, rounds = sys.argv[1], sys.argv[2], int(sys.argv[3])
sys.path[:0] = [har, os.path.join(har, 'lib')]
import run_all as RA
a = types.SimpleNamespace(sw=sw, python=sys.executable, node='node', golden=os.path.join(har, 'golden'), regen_golden=False,
                          quick=False, perf_scale=1.0, workdir=tempfile.gettempdir())
c = RA.Ctx(a)
key = RA.find_key(c, r'source_(?:pattern|radiation|directivity)[a-z_]*')
p = c.params('std_lock18', {key: 'talking_head', 'source_radiation_b': 'trumpet_byu', 'source_yaw': 35.0,
                            'source_yaw_b': -25.0, 'two_sources': True})
V = [x.split('=', 1) for x in sys.argv[4:]]
res = {n: [] for n, _ in V}
for r in range(rounds):
    for n, w in (V if r % 2 == 0 else V[::-1]):
        j = json.loads(c.play(p, {}, 'bench', 4, 10, wasm=None if w == 'ship' else os.path.abspath(w)))
        res[n].append(round(j['play_mean_ms'], 4))
    print(r, {n: res[n][-1] for n, _ in V}, flush=True)
for n, v in res.items():
    print(f'{n:12s} min {min(v):.3f}  median {statistics.median(v):.3f}  (gate 2.133)')
