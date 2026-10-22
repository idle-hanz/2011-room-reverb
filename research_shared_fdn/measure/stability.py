# Stability: extreme diffusion (dffs +0.98 / -0.98 all lines, both banks), long decay, 30 s IR; NaN/Inf, late level, growth.
import json, subprocess, os, math, copy
import numpy as np
H=os.path.dirname(os.path.abspath(__file__)); PRO=H+'/../proto'
exec(open(H+'/measure.py').read().split('ONLY=')[0])
V2={'m0':PRO+'/v3/m0.wasm','cand':PRO+'/v3/cand.wasm','fx':PRO+'/v3/fx.wasm'}
S.update({'stab_big_2src':({**base,**big,**vio,'two_sources':True,'source_balance':0.3,'decay_s':10.0},30),
          'stab_bin_big':({**base,**big,'mic_setup':'binaural','decay_s':10.0},30)})
res={}
for k in ('stab_big_2src','stab_bin_big'):
    p=json.load(open(params(k)))
    for dv in (0.98,-0.98):
        q=copy.deepcopy(p)
        for m in 'lcr':
            for key in list(q['buses'][m].keys()):
                if key.startswith('dffs'): q['buses'][m][key]=[dv if x!=0 else 0.0 for x in q['buses'][m][key]] if isinstance(q['buses'][m][key],list) else q['buses'][m][key]
        pj=f'{H}/p_{k}_d{dv:+.2f}.json'; json.dump(q,open(pj,'w'))
        for v,w in V2.items():
            out=f'/tmp/stab_{v}.f32'
            r=subprocess.run(['node',LIB+'/wasm_run.js',SW,pj,'{}','ir',str(S[k][1]),out],capture_output=True,text=True,env=dict(os.environ,WASM=w))
            if r.returncode: raise SystemExit(r.stderr[-300:])
            y=np.fromfile(out,np.float32).reshape(-1,2).astype(float)
            seg=[10*math.log10(np.mean(y[i:i+SR]**2)+1e-300) for i in range(0,len(y)-SR+1,SR)]
            d=np.diff(seg[2:])
            res[f'{k}|dffs{dv:+.2f}|{v}']={'finite':bool(np.all(np.isfinite(y))),'peak':round(float(np.max(np.abs(y))),4),'lvl_1s_db':[round(s,1) for s in seg[:3]],'lvl_last_s_db':round(seg[-1],1),
                 'max_rise_db_per_s_after_2s':round(float(np.max(d)),2) if len(d) else None,'t30_1k_L':t30(band(y[:,0],1000))}
            print(k,dv,v,res[f'{k}|dffs{dv:+.2f}|{v}'],flush=True)
json.dump(res,open(H+'/stability_results.json','w'),indent=1)
