import sys, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from analyze import *
sr=48000
for path in sys.argv[1:]:
    L,R=load_f32_stereo(path)
    print(path)
    for fc in (None,250,1000,4000,9000,11000):
        y=L if fc is None else band(L,sr,fc)
        e=[round(rms_db(y[int(a*sr):int((a+0.1)*sr)]),1) for a in (0.05,0.25,0.5,0.75,1.0,1.5,2,3,4,6)]
        print('  ',fc or 'bb',e)
