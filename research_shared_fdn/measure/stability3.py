# Stability at the UI's max decay (8 s) and 4 s; default diffusion and dffs 0.9 on every line; 30 s impulse response.
import json, subprocess, os, math, copy
import numpy as np
H=os.path.dirname(os.path.abspath(__file__)); PRO=H+'/../proto'
exec(open(H+'/measure.py').read().split('ONLY=')[0])
V2={'m0':PRO+'/v3/m0.wasm','cand':PRO+'/v3/cand.wasm'}
res={}
for dec in (8.0,4.0):
    for nm,body in (('big_2src',{**base,**big,**vio,'two_sources':True,'source_balance':0.3}),('bin_big',{**base,**big,'mic_setup':'binaural'}),('def_1src',{**base,**vio})):
        k=f'st3_{nm}_dec{dec:g}'; S[k]=({**body,'decay_s':dec},30); p=json.load(open(params(k)))
        for dv in ((None,0.9) if dec==8.0 else (None,)):
            q=copy.deepcopy(p)
            if dv is not None:
                for m in 'lcr':
                    for key in list(q['buses'][m].keys()):
                        if key.startswith('dffs') and isinstance(q['buses'][m][key],list): q['buses'][m][key]=[dv if x!=0 else 0.0 for x in q['buses'][m][key]]
            pj=f'{H}/p_{k}_d{(dv or 0):+.2f}.json'; json.dump(q,open(pj,'w'))
            for v,w in V2.items():
                out=f'/tmp/st3_{v}.f32'
                subprocess.run(['node',LIB+'/wasm_run.js',SW,pj,'{}','ir','30',out],check=True,capture_output=True,env=dict(os.environ,WASM=w))
                y=np.fromfile(out,np.float32).reshape(-1,2).astype(float)
                seg=[10*math.log10(np.mean(y[i:i+SR]**2)+1e-300) for i in range(0,len(y)-SR+1,SR)]
                key=f'{k}|dffs{(dv or 0):+.2f}|{v}'
                res[key]={'finite':bool(np.all(np.isfinite(y))),'peak':round(float(np.max(np.abs(y))),4),'lvl_db_every_5s':[round(s,1) for s in seg[::5]],'lvl_last_s_db':round(seg[-1],1),
                          'dc_last_s':float(np.mean(y[-SR:,0])),'min_lvl_db':round(min(seg),1),'grows_after_min':bool(seg[-1]>min(seg)+6)}
                print(key,res[key],flush=True)
json.dump(res,open(H+'/stability_results.json','w'),indent=1)
