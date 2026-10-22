from mirror_lib import *
import json, sys
res = {}
def play_json(tree, pj, secs=3.0):
    c = ctx(tree); out = c.work / f'hack_{tree}.f32'
    if out.exists(): out.unlink()
    c.play(pj, {}, 'ir', secs, out)
    return np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)
for tree in sys.argv[1].split(','):
    c = ctx(tree)
    pB = json.load(open(c.params(body('twoB')))); p1 = json.load(open(c.params(body('oneB'))))
    col = dict(p1['colour']); col['direct_b'] = p1['colour']['direct']; col['early_b'] = p1['colour']['early']
    pB['colour'] = col
    hp = c.work / f'hackB_{tree}.json'; json.dump(pB, open(hp, 'w'))
    A = play(tree, 'twoA'); Bh = play_json(tree, hp)
    res[tree] = compare(A, Bh, f'{tree:8s} two A vs mirB, B with its OWN fdn colour map')
    print('   fdn map A l[:12]', pB.get('colour') and json.load(open(c.params(body('twoA'))))['colour']['fdn']['l'][:12], ' B-own l[:12]', p1['colour']['fdn']['l'][:12], 'n_irs A', len(json.load(open(c.params(body('twoA'))))['colour']['irs']), 'B-own', len(p1['colour']['irs']))
json.dump(res, open('e2.json', 'w'), indent=1, default=float)
