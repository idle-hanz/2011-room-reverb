import json, subprocess, os
import numpy as np
B='/workspace/build_support_2'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
SW=B+'/snapshot_2026-10-02_0830/software'; H=os.path.dirname(os.path.abspath(__file__)); PR=B+'/research_shared_fdn/profile'
V={'ship':SW+'/static/wasm/live_stereo.wasm','m0':H+'/shared_m0.wasm','m1':H+'/shared_m1.wasm','cand':H+'/sweep/j300_s1.wasm','fx':H+'/sweep/fx300_s1.wasm'}
S=['def_1src','def_2src','big_1src','big_2src','bin_def_2src']
def run(w,s,mode,*a):
    r=subprocess.run(['node',LIB+'/wasm_run.js',SW,f'{PR}/p_{s}.json','{}',mode,*map(str,a)],capture_output=True,text=True,env=dict(os.environ,WASM=w))
    if r.returncode: raise SystemExit(r.stderr[-400:])
    return r.stdout
for s in S:
    a=None
    for k in ('ship','m0'):
        out=f'{H}/ir_{k}_{s}.f32'; run(V[k],s,'ir',2,out); x=np.fromfile(out,np.float32)
        if a is None: a=x
        else: print(s,'m0 vs shipped max diff',float(np.max(np.abs(x-a))),flush=True)
res={}
for r in range(int(os.environ.get('ROUNDS','4'))):
    base=['m0','m1','cand','fx']; ks=base[r%4:]+base[:r%4]
    for s in S:
        for k in ks:
            d=json.loads(run(V[k],s,'bench',4,8)); res.setdefault(f'{s}|{k}',[]).append(d['play_mean_ms'])
    print('round',r,flush=True)
out={k:{'min':round(min(v),3),'med':round(float(np.median(v)),3)} for k,v in res.items()}
json.dump(out,open(H+'/bench_variants_v2.json','w'),indent=1)
for k,v in out.items(): print(f'{k:22s} min {v["min"]:.3f} med {v["med"]:.3f}')
