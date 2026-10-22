import json, subprocess, numpy as np, os
PY='/workspace/scratch_er_dropout/venv/bin/python'; SW='/workspace/build_support_2/snapshot_2026-10-02_1140/software'
body=json.load(open('../../s4_verify_1140/measure/client_body_1140.json')); body.update(direct_wet=0,early_wet=0,fdn_wet=1,dry_gain=0,sx=3.0,mcx=3.0)
o={}
for e in ('none','osign'):
    out=os.path.abspath(f'w_sym_{e}.f32'); env=dict(os.environ,EXP=e,DLYMOD=os.path.abspath('mod_exp.py'))
    subprocess.run([PY,'render_ir_mod.py',SW,json.dumps(body),out,'1000','44100'],capture_output=True,text=True,env=env,check=True)
    h=np.fromfile(out,np.float32).reshape(-1,2); o[e]=float(np.max(np.abs(h[:,0]-h[:,1]))/np.max(np.abs(h)))
print('render symmetric max|L-R|/peak',o); json.dump(o,open('render_sym.json','w'))
