from mirror_lib import *
import json
res = {}
for tree in ['base', 'tau', 'p6', 'p6_tau']:
    ov = dict(decay_lock=False, fdn_g=1.0)
    for col in ['measured', 'bypass']:
        A = play(tree, 'twoA', colour_mode=col, over=ov); B = play(tree, 'twoB', colour_mode=col, over=ov)
        res[f'{tree}_{col}_unlocked_two'] = compare(A, B, f'{tree:7s} UNLOCKED fdn_g1 {col:8s} two')
        A1 = play(tree, 'oneA', colour_mode=col, over=ov); B1 = play(tree, 'oneB', colour_mode=col, over=ov)
        res[f'{tree}_{col}_unlocked_one'] = compare(A1, B1, f'{tree:7s} UNLOCKED fdn_g1 {col:8s} one')
for tree in ['tau', 'p6_tau']:
    ov = dict(space=0.17)
    A1 = play(tree, 'oneA', over=ov); B1 = play(tree, 'oneB', over=ov)
    res[f'{tree}_space017_one'] = compare(A1, B1, f'{tree:7s} space 0.17 measured one')
json.dump(res, open('e4.json', 'w'), indent=1, default=float)
