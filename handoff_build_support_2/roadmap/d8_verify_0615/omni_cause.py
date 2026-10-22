import json, numpy as np
exec(open('play_checks.py').read().split('base=')[0])
sc={"decay_lock":False,"fdn_g":0.8,"early_wet":1.0}
out={}
for h in (0.35,0.5):
    a=play(NEW,dump(NEW,dict(sc,humidity=h),f'u_n{h}'),{"colour_on":False},1.5,f'u_n{h}')
    b=play(OLD,dump(OLD,dict(sc,humidity=h),f'u_o{h}'),{"colour_on":False},1.5,f'u_o{h}')
    out[f'std_unlocked_byp_h{h}_new_vs_2210_maxabs']=float(np.max(np.abs(a-b)))
print(out); json.dump(out,open('omni_cause.json','w'))
