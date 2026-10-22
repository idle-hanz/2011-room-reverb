from mirror_lib import *
import json
res = {}
for n in (16, 64):
    A = render('base', 'oneA', hadamard_n=n); B = render('base', 'oneB', hadamard_n=n)
    res[n] = compare(A, B, f'base RENDER N={n} one A vs B-pos measured')
json.dump(res, open('e8.json', 'w'), indent=1, default=float)
