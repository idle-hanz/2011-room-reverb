from mirror_lib import *
import json
res = {}
for tree in ['base', 'p6']:
    A = play(tree, 'twoA'); B = play(tree, 'twoB')
    res[f'{tree}_play_two'] = compare(A, B, f'{tree} Play two-source A vs mirrored B')
    A1 = play(tree, 'oneA'); B1 = play(tree, 'oneB')
    res[f'{tree}_play_one'] = compare(A1, B1, f'{tree} Play one-source A vs one at B')
    res[f'{tree}_play_twoB_vs_oneB'] = compare(B1, 2*B[:, ::-1], f'{tree} twoB*2 vs oneB (same side)')
json.dump(res, open('e0.json', 'w'), indent=1, default=float)
