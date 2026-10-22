import sys, json, numpy as np, os
sw=sys.argv[1]; outp=sys.argv[2]; sys.path[:0]=[sw, sw+'/engine']; os.chdir(sw)
import app_server as A
from render_pipeline import render
def go(over):
    b=dict(A.DEFAULTS); b.update({"sample_rate":48000,"ir_length_ms":1500,"air_lp":0.0}); b.update(over)
    p=A.params_from_body(b); kw={k:v for k,v in p.items() if k in render.__code__.co_varnames}
    dry=np.zeros(4800); dry[0]=1; L,R,info=render(dry,48000,**kw); return np.stack([L,R],1)*float(1.0)
std={"decay_lock":True,"decay_s":1.8,"early_wet":1.0}
hall={"decay_lock":True,"decay_s":4.0,"W":20,"H":10,"L":30,"sx":10,"sz":18,"mcx":10,"mcz":6,"ir_length_ms":3000}
out={}
for nm,sc in (('std',std),('hall',hall)):
    for h in (0.0,0.35,1.0):
        np.save(f'{outp}_{nm}_h{h}_rev.npy',go(dict(sc,humidity=h,direct_wet=0.0,dry_gain=0.0)))
for h in (0.0,1.0): np.save(f'{outp}_dir_h{h}.npy',go(dict(std,humidity=h,early_wet=0.0,fdn_wet=0.0,dry_gain=0.0)))
for h in (0.05,0.2,0.5,0.8): np.save(f'{outp}_std_h{h}_rev.npy',go(dict(std,humidity=h,direct_wet=0.0,dry_gain=0.0)))
print('ok')
