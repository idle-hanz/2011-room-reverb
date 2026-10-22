from mirror_lib import *
for tree in ['tau', 'base']:
    ov = dict(early_wet=1.0, direct_wet=1.0, fdn_wet=0.0)
    A = play(tree, 'twoA', over=ov); B = play(tree, 'twoB', over=ov)
    compare(A, B, f'{tree:5s} direct+early only, measured, two')
    A1 = play(tree, 'oneA', over=ov); B1 = play(tree, 'oneB', over=ov)
    compare(A1, B1, f'{tree:5s} direct+early only, measured, one')
