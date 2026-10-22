# CPU: (a) binaural skip-centre: shipped 16:30 vs 16:30 with cEmpty forced 0 (noskip.wasm), same 16:30 params;
# (b) t19-type stereo default: shipped 16:30 vs shipped 11:40 (each with its own params). Alternating order, 6 rounds, bench 4 8.
import json, subprocess, os, numpy as np
B='/workspace/build_support_2'; LIB=B+'/3_phase_acceptance_tests/harness/lib'; M=B+'/roadmap/s4b_verify_1630/measure'
S16=B+'/snapshot_2026-10-02_1630/software'; S11=B+'/snapshot_2026-10-02_1140/software'; W=B+'/work/s4b_1630/w'
H=os.path.dirname(os.path.abspath(__file__))
A={'skipc_1630':(S16,S16+'/static/wasm/live_stereo.wasm'),'noskip_1630':(S16,W+'/noskip.wasm')}
C={'ship_1630':(S16,S16+'/static/wasm/live_stereo.wasm'),'ship_1140':(S11,S11+'/static/wasm/live_stereo.wasm')}
def pj(sw,k): return f'{M}/p_{os.path.basename(os.path.dirname(sw))}_{k}_48000.json'
JOBS=[(s,A) for s in ('bin_def_1src','bin_def_2src','bin_big')]+[(s,C) for s in ('def_1src','def_2src')]
res={}
for r in range(6):
    for s,V in JOBS:
        ks=list(V) if r%2==0 else list(V)[::-1]
        for k in ks:
            sw,w=V[k]
            o=subprocess.run(['node',LIB+'/wasm_run.js',sw,pj(sw,s),'{}','bench','4','8'],capture_output=True,text=True,env=dict(os.environ,WASM=w),check=True).stdout
            res.setdefault(f'{s}|{k}',[]).append(json.loads(o)['play_mean_ms'])
    print('round',r,flush=True)
out={k:{'min':round(min(v),4),'med':round(float(np.median(v)),4),'all':[round(x,4) for x in v]} for k,v in res.items()}
for s,V in JOBS:
    a,b=list(V)
    out[f'{s}|delta_pct_{a}_vs_{b}']={'min':round(100*(out[f'{s}|{a}']['min']/out[f'{s}|{b}']['min']-1),1),'med':round(100*(out[f'{s}|{a}']['med']/out[f'{s}|{b}']['med']-1),1)}
json.dump(out,open(H+'/bench_s4b.json','w'),indent=1)
for k,v in out.items(): print(k,{kk:vv for kk,vv in v.items() if kk!='all'})
