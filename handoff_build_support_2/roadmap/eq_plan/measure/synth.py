import numpy as np, subprocess, json
SR=48000; n=192001
for name,T in (('defsyn',1.8),('boxsyn',0.8)):
    for seed in range(3):
        rng=np.random.default_rng(seed); t=np.arange(n)/SR
        x=rng.standard_normal((n,2))*np.exp(-6.9078*t/T)[:,None]
        x.astype(np.float32).tofile(f'{name}{seed}.f32')
