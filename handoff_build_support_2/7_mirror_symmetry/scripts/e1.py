from mirror_lib import *
import json, sys
res = {}
trees = sys.argv[1].split(',')
for tree in trees:
    for col in ['measured', 'bypass']:
        A = play(tree, 'twoA', colour_mode=col); B = play(tree, 'twoB', colour_mode=col)
        res[f'{tree}_{col}_two'] = compare(A, B, f'{tree:11s} {col:8s} two  A vs mirB')
        A1 = play(tree, 'oneA', colour_mode=col); B1 = play(tree, 'oneB', colour_mode=col)
        res[f'{tree}_{col}_one'] = compare(A1, B1, f'{tree:11s} {col:8s} one  A vs B-pos')
        res[f'{tree}_{col}_twoA_oneA'] = compare(A1, 2*A[:, ::-1], f'{tree:11s} {col:8s} twoA*2 vs oneA', verbose=True)
json.dump(res, open('e1_' + '_'.join(trees) + '.json', 'w'), indent=1, default=float)
