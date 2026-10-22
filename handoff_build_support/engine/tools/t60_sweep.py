import sys, json, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from analyze import *
sr = 48000
rows = []
for spec in sys.argv[1:]:
    name, path, dial = spec.split(',')
    L, R = load_f32_stereo(path)
    t = t60_bands(L, sr, bands=[250, 1000, 4000, 8000])
    lt = late_t60(L, sr, 10000, float(dial) * 0.6, float(dial) * 0.8)
    print(f"{name:28s} dial {float(dial):4.1f}s | T30 250 {t[250]:6.2f} 1k {t[1000]:6.2f} 4k {t[4000]:6.2f} 8k {t[8000]:6.2f} bb {t['broadband']:6.2f} | 10k late {lt:6.2f}")
