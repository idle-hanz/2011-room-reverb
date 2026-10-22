import json, subprocess, os, sys, glob
import numpy as np
sys.argv=[sys.argv[0]]
H=os.path.dirname(os.path.abspath(__file__)); PRO=H+'/../proto'
exec(open(H+'/measure.py').read().split('res={}')[0].split('ONLY=')[0])
V.clear(); V['m1']=PRO+'/shared_m1.wasm'
for f in sorted(glob.glob(PRO+'/sweep/*.wasm')): V[os.path.basename(f)[:-5]]=f
ref=json.load(open(H+'/measure_results.json'))
out={}
for k,win in (('def_omni',(0.08,1.0)),('big_omni',(0.25,2.5)),('bin_def_omni',(0.08,1.0))):
    m0=ref[k]['m0']['coh_LR_tail']
    for v in V:
        y=ir(v,k,TAIL,'tail'); c=coh(y[:,0],y[:,1],*win)
        e=[c[f]-float(m0[str(f)]) for f in OCT]
        out.setdefault(v,{})[k]={'coh':c,'dev':[round(x,3) for x in e],'rms':round(float(np.sqrt(np.mean(np.square(e)))),3),'max':round(float(np.max(np.abs(e))),3),'t30_1k':t30(band(y[:,0],1000))}
    print(k,flush=True)
for v in out: print(v,{k:(out[v][k]['rms'],out[v][k]['max']) for k in out[v]})
json.dump(out,open(H+'/sweep_results.json','w'),indent=1,default=str)
