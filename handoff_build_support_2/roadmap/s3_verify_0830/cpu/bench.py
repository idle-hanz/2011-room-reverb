import json, subprocess, sys, os
import numpy as np
sys.path.insert(0, '/workspace/build_support_2/3_phase_acceptance_tests/harness')
from run_all import SCENES
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'
LIB=B+'/3_phase_acceptance_tests/harness/lib'
SW={'0709':B+'/snapshot_2026-10-02_0709/software','0830':B+'/snapshot_2026-10-02_0830/software'}
C=B+'/work/s3_0830/cpu'
SCEN_ALL={'t19':(dict(SCENES['std_lock18'],source_radiation='talking_head',source_radiation_b='trumpet_byu',source_yaw=35.0,source_yaw_b=-25.0,two_sources=True),{},(4,10)),
      't15_2src_omni':(dict(SCENES['std_lock18']),{"two_sources":True},(4,10))}
scen={k:v for k,v in SCEN_ALL.items() if k in os.environ.get('SCN',','.join(SCEN_ALL)).split(',')}
pj={}
for s,(body,over,_) in scen.items():
    for v,sw in SW.items():
        out=f'{C}/p_{s}_{v}.json'
        subprocess.run([P,LIB+'/dump_params.py',sw,json.dumps(body),out,'48000'],check=True)
        pj[s,v]=out
    print(s,'params identical 0709 vs 0830:',open(pj[s,'0709']).read()==open(pj[s,'0830']).read(), flush=True)
var={'ship0709':(SW['0709']+'/static/wasm/live_stereo.wasm','0709'),'ship0830':(SW['0830']+'/static/wasm/live_stereo.wasm','0830'),
     'zig0709':(C+'/v0.wasm','0709'),'zig0830':(C+'/v1.wasm','0830'),'noskip':(C+'/v1_noskip.wasm','0830'),'fixedN':(C+'/v1_fixedN.wasm','0830')}
def run(w,v,s,mode,*a):
    r=subprocess.run(['node',LIB+'/wasm_run.js',SW[v],pj[s,v],json.dumps(scen[s][1]),mode,*map(str,a)],env=dict(os.environ,WASM=w),capture_output=True,text=True)
    if r.returncode: raise SystemExit(r.stderr[-500:])
    return r.stdout
if 'ir' in sys.argv:
    for s in scen:
        irs={}
        for k,(w,v) in var.items():
            out=f'{C}/ir_{k}_{s}.f32'; run(w,v,s,'ir',3,out); irs[k]=np.fromfile(out,np.float32)
        ref=irs['ship0830']
        print(s,{k:float(np.max(np.abs(x-ref))) for k,x in irs.items()},flush=True)
rounds=int(os.environ.get('ROUNDS','4'))
res={}
order=[k for k in var if k in os.environ.get('ONLY',','.join(var)).split(',')]
for r_ in range(rounds):
    seq=order if r_%2==0 else order[::-1]
    for k in seq:
        for s in scen:
            d=json.loads(run(*var[k],s,'bench',*scen[s][2]))
            res.setdefault((k,s),[]).append((round(d['play_mean_ms'],3),(round(d['silence_late_mean_ms'],3) if d.get('silence_late_mean_ms') is not None else -1)))
    print('round',r_,flush=True)
out={}
for (k,s),v in res.items():
    pm=[a for a,b in v]; sm=[b for a,b in v]
    out[f'{s}|{k}']={'play':pm,'sil':sm,'play_med':float(np.median(pm)),'sil_med':float(np.median(sm))}
    print(f'{s:15s} {k:9s} play med {np.median(pm):.3f} {pm}  sil med {np.median(sm):.3f} {sm}')
json.dump(out,open(C+'/bench_results.json','w'),indent=1)
