from mirror_lib import *
for tree in ['tau']:
    for nm, ov in [('direct', dict(early_wet=0.0, direct_wet=1.0, fdn_wet=0.0)), ('early', dict(early_wet=1.0, direct_wet=0.0, fdn_wet=0.0))]:
        for col in ['measured', 'bypass']:
            A = play(tree, 'twoA', colour_mode=col, over=ov); B = play(tree, 'twoB', colour_mode=col, over=ov)
            compare(A, B, f'{tree:5s} {nm} only {col} two')
            A1 = play(tree, 'oneA', colour_mode=col, over=ov)
            compare(A1, 2*A[:, ::-1] if False else A1, 'self', verbose=False)
            print('     twoA vs oneA level dB', round(10*np.log10(np.sum(A**2)/np.sum(A1**2)),2), ' null(twoA, oneA scaled)', round(null_db(A1, A*np.sqrt(np.sum(A1**2)/np.sum(A**2))),1))
