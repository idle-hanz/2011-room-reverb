import sys, json, numpy as np, os
sw=sys.argv[1]; outp=sys.argv[2]; sys.path[:0]=[sw, sw+'/engine']; os.chdir(sw)
import app_server as A
from render_pipeline import render
N=1<<17; fr=np.fft.rfftfreq(N,1/48000)
def band(x,lo,hi):
    X=sum(np.abs(np.fft.rfft(x[:,i],N))**2 for i in (0,1)); m=(fr>=lo)&(fr<hi); return float(10*np.log10(X[m].mean()+1e-30))
def go(h,over):
    b=dict(A.DEFAULTS); b.update({"humidity":h,"sample_rate":48000,"ir_length_ms":1200,"decay_lock":True,"decay_s":1.8,"early_wet":1.0,"air_lp":0.0}); b.update(over)
    p=A.params_from_body(b); kw={k:v for k,v in p.items() if k in render.__code__.co_varnames}
    dry=np.zeros(4800); dry[0]=1
    L,R,info=render(dry,48000,**kw); return np.stack([L,R],1)
res={'sweep':{}}; ir={}
for h in (0.0,0.05,0.2,0.35,0.5,0.8,1.0):
    x=go(h,{"direct_wet":0.0,"dry_gain":0.0}); ir[h]=x
    res['sweep'][h]={'hf8_16k_db':round(band(x,8000,16000),3),'b4_8k_db':round(band(x,4000,8000),3)}
d0=go(0.0,{"early_wet":0.0,"fdn_wet":0.0,"dry_gain":0.0}); d1=go(1.0,{"early_wet":0.0,"fdn_wet":0.0,"dry_gain":0.0})
res['render_direct_h1_vs_h0_maxabs']=float(np.max(np.abs(d1-d0)))
np.save(outp+'_h0.npy',ir[0.0]); np.save(outp+'_h035.npy',ir[0.35])
json.dump(res,open(outp+'.json','w'),indent=1); print(json.dumps(res))
