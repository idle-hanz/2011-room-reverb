from mirror_lib import *
import json
for tree in ['base','p6']:
    c = ctx(tree)
    pa = json.load(open(c.params(body('oneA')))); pb = json.load(open(c.params(body('oneB'))))
    print(tree, 'g', pa['g'], pb['g'], 'makeup', pa['makeup'], pb['makeup'], 'decay', pa['decay_s'], pb['decay_s'], 'mean', pa['mean_delay_ms'], pb['mean_delay_ms'], 'di', pa['direct_index'], pb['direct_index'])
    for bus, mb in (('l','r'),('r','l')):
        A = pa['buses'][bus]; B = pb['buses'][mb]
        print(' bus', bus, 'vs B', mb, 'sorted delays equal?', np.allclose(sorted(A['delay_ms']), sorted(B['delay_ms'])),
              'sum inj^2 A/B dB', round(10*np.log10(np.sum(np.square(A['inject']))/np.sum(np.square(B['inject']))),2),
              'shelf/air keys', [k for k in A if k not in ('delay_ms','inject','dffs','mic_g','air_g','shelf','b','loop_mix')])
        print('  A delays', np.round(A['delay_ms'],1).tolist()); print('  B delays', np.round(B['delay_ms'],1).tolist())
        print('  A inj', np.round(A['inject'],4).tolist()); print('  B inj', np.round(B['inject'],4).tolist())
        print('  dffs A', np.round(A['dffs'],3).tolist()[:8], 'B', np.round(B['dffs'],3).tolist()[:8])
