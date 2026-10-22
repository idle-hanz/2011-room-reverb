import json, subprocess, os
import numpy as np
B='/workspace/build_support_2'; LIB=B+'/3_phase_acceptance_tests/harness/lib'; SW=B+'/snapshot_2026-10-02_0830/software'; H=os.path.dirname(os.path.abspath(__file__))
V={'m0':H+'/v3/m0.wasm','skipc':H+'/v3/m0_skipc.wasm'}
P={'bin_def_2src':B+'/research_shared_fdn/profile/p_bin_def_2src.json','bin_def_1src':B+'/research_shared_fdn/measure/p_bin_def_omni.json','bin_big_1src':B+'/research_shared_fdn/measure/p_bin_big_omni.json'}
res={}
for r in range(6):
    for s,p in P.items():
        for k in (['m0','skipc'] if r%2==0 else ['skipc','m0']):
            o=subprocess.run(['node',LIB+'/wasm_run.js',SW,p,'{}','bench','4','8'],capture_output=True,text=True,env=dict(os.environ,WASM=V[k]),check=True).stdout
            res.setdefault(f'{s}|{k}',[]).append(json.loads(o)['play_mean_ms'])
    print('round',r,flush=True)
out={k:{'min':round(min(v),3),'med':round(float(np.median(v)),3)} for k,v in res.items()}
json.dump(out,open(H+'/bench_skipc.json','w'),indent=1)
for k,v in out.items(): print(k,v)
