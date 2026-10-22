import json, subprocess, sys, os
import numpy as np
sys.path.insert(0, '/workspace/build_support_2/3_phase_acceptance_tests/harness')
from run_all import SCENES
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__))
SW={'0830':B+'/snapshot_2026-10-02_0830/software','1140':B+'/snapshot_2026-10-02_1140/software'}
body=dict(SCENES['std_lock18'],source_radiation='talking_head',source_radiation_b='trumpet_byu',source_yaw=35.0,source_yaw_b=-25.0,two_sources=True)
pj={}
for v,sw in SW.items():
    pj[v]=f'{HERE}/p_t19_{v}.json'; subprocess.run([P,LIB+'/dump_params.py',sw,json.dumps(body),pj[v],'48000'],check=True,capture_output=True)
print('params identical:', open(pj['0830']).read()==open(pj['1140']).read())
def run(v,mode,*a):
    r=subprocess.run(['node',LIB+'/wasm_run.js',SW[v],pj[v],'{}',mode,*map(str,a)],capture_output=True,text=True); return r.stdout
for v in SW: run(v,'ir',2,f'{HERE}/ir_{v}.f32')
a,b=np.fromfile(f'{HERE}/ir_0830.f32',np.float32),np.fromfile(f'{HERE}/ir_1140.f32',np.float32); print('IR max diff 0830 vs 1140:',float(np.max(np.abs(a-b))))
res={v:[] for v in SW}
for r_ in range(8):
    for v in (list(SW) if r_%2==0 else list(SW)[::-1]):
        d=json.loads(run(v,'bench',4,10)); res[v].append(round(d['play_mean_ms'],3))
for v,x in res.items(): print(v,'best',min(x),'median',float(np.median(x)),x)
json.dump(res,open(HERE+'/ab_t19.json','w'),indent=1)
