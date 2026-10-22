import sys, json, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from analyze import *
sr = 48000
for path in sys.argv[1:]:
    L, R = load_f32_stereo(path)
    x = L
    t = t60_bands(x, sr)
    lt = {fc: round(late_t60(x, sr, fc, 1.0, 2.0), 2) for fc in (500, 2000, 9000, 11000)}
    pk_early = peak_freqs(x[int(1.0*sr):int(3.0*sr)], sr, 4, 2000)
    pk_late = peak_freqs(x[int(4.0*sr):int(8.0*sr)], sr, 4, 2000)
    lv = [round(rms_db(x[int(a*sr):int((a+0.5)*sr)]), 1) for a in (0.0, 1.0, 2.0, 4.0, 8.0)]
    print(path, 'T30', {k: round(v, 2) for k, v in t.items()}, '\n  lateT60(1-3s)', lt, '\n  rms dB @0,1,2,4,8s', lv, '\n  peaks 1-3s', pk_early, ' 4-8s', pk_late)
