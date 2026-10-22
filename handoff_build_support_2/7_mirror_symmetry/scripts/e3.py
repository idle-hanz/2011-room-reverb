from mirror_lib import *
import json, sys, time
res = {}
for tree in sys.argv[1].split(','):
    for col in ['measured']:
        t0 = time.time()
        A = render(tree, 'oneA', colour_mode=col); B = render(tree, 'oneB', colour_mode=col)
        res[f'{tree}_{col}'] = compare(A, B, f'{tree:8s} RENDER one A vs B-pos {col}')
        print('   secs', round(time.time()-t0, 1))
        P = play(tree, 'oneA', colour_mode=col)
        res[f'{tree}_{col}_play_vs_render'] = compare(A, P[:, ::-1], f'{tree:8s} Render A vs Play A (same side) {col}')
json.dump(res, open('e3_' + sys.argv[1].replace(',', '_') + '.json', 'w'), indent=1, default=float)
