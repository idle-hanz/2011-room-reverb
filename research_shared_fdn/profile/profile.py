import json, subprocess, os, sys
import numpy as np
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
SW=B+'/snapshot_2026-10-02_0830/software'; C=os.path.dirname(os.path.abspath(__file__))
WASM=os.environ.get('WASM', SW+'/static/wasm/live_stereo.wasm')
base=dict(toe_half_deg=55, space=0.17, decay_lock=True, decay_s=1.8, humidity=0.5, early_wet=1.0, mirror_b=True)
big=dict(W=57.0,H=34.2,L=97.0, sx=24.0, sz=60.0, mcx=28.5, mcz=30.0, decay_s=4.0)
d1=dict(source_radiation='violin_byu', source_yaw=180.0)
d2=dict(source_radiation='violin_byu', source_radiation_b='violin_byu', source_yaw=180.0, two_sources=True)
S={'def_1src':{**base,**d1}, 'def_2src':{**base,**d2}, 'big_1src':{**base,**big,**d1}, 'big_2src':{**base,**big,**d2},
   'bin_def_2src':{**base,**d2,'mic_setup':'binaural'},
   'def_2src_omni':{**base,'two_sources':True}, 'def_1src_omni':{**base}}
OV={'full':{}, 'no_fdn':{'fdn_wet':0}, 'no_early':{'early_wet':0}, 'no_colour':{'colour_on':False},
    'no_colour_no_fdn':{'colour_on':False,'fdn_wet':0}, 'no_fdn_no_early':{'fdn_wet':0,'early_wet':0}}
runs=[(s,o) for s in S for o in OV if not (s.endswith('omni') and o not in ('full','no_fdn'))]
pj={}
for k,b in S.items():
    out=f'{C}/p_{k}.json'
    if not os.path.exists(out): subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(b),out,'48000'],check=True,capture_output=True)
    pj[k]=out
res={}
R=int(os.environ.get('ROUNDS','3'))
for r in range(R):
    seq=runs if r%2==0 else runs[::-1]
    for s,o in seq:
        x=subprocess.run(['node',LIB+'/wasm_run.js',SW,pj[s],json.dumps(OV[o]),'bench','4','8'],capture_output=True,text=True,env=dict(os.environ,WASM=WASM))
        if x.returncode: print('fail',s,o,x.stderr[-200:]); continue
        d=json.loads(x.stdout); res.setdefault(f'{s}|{o}',[]).append(d['play_mean_ms'])
    print('round',r,flush=True)
out={k:{'min':round(min(v),3),'med':round(float(np.median(v)),3),'all':[round(a,3) for a in v]} for k,v in res.items()}
json.dump(out,open(C+f'/profile_{os.environ.get("TAG","ship0830")}.json','w'),indent=1)
for k,v in out.items(): print(f'{k:32s} min {v["min"]:.3f} med {v["med"]:.3f}')
