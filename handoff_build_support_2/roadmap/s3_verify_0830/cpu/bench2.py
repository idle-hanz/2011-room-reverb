import json, subprocess, os, sys
import numpy as np
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
SW=B+'/snapshot_2026-10-02_0830/software'; C=B+'/work/s3_0830/cpu'
mic=dict(toe_half_deg=55, space=0.17, decay_lock=True, decay_s=1.8, humidity=0.5, early_wet=1.0, two_sources=True, mirror_b=True)
big=dict(W=57.0,H=34.2,L=97.0, sx=24.0, sz=60.0, mcx=28.5, mcz=30.0, decay_s=4.0)
dirAB=dict(source_radiation='violin_byu', source_yaw=180.0)   # B inherits (intended fix behaviour)
dirA_only=dict(source_radiation='violin_byu', source_radiation_b='omni', source_yaw=180.0)
omni=dict(source_radiation='omni', source_radiation_b='omni')
S={'def_omni2':{**mic,**omni}, 'def_dirA_Bomni':{**mic,**dirA_only}, 'def_dirAB':{**mic,**dirAB},
   'big_omni2':{**mic,**big,**omni}, 'big_dirAB':{**mic,**big,**dirAB},
   'bin_def_dirAB':{**mic,**dirAB,'mic_setup':'binaural'}, 'bin_big_dirAB':{**mic,**big,**dirAB,'mic_setup':'binaural'}}
pj={}
for k,b in S.items():
    out=f'{C}/p2_{k}.json'
    r=subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(b),out,'48000'],capture_output=True,text=True)
    if r.returncode: print(k,'dump fail',r.stderr[-300:]); continue
    d=json.load(open(out)); src=d.get('src_rad') or []
    print(k,'src_rad head',src[:2],'binaural' ,bool(d.get('binaural') or d.get('hrtf') or d.get('bin')), flush=True); pj[k]=out
res={}
for r_ in range(int(os.environ.get('ROUNDS','4'))):
    ks=list(pj) if r_%2==0 else list(pj)[::-1]
    for k in ks:
        r=subprocess.run(['node',LIB+'/wasm_run.js',SW,pj[k],'{}','bench','4','10'],capture_output=True,text=True)
        if r.returncode: print(k,'bench fail',r.stderr[-300:]); continue
        d=json.loads(r.stdout); res.setdefault(k,[]).append((d['play_mean_ms'],d['silence_late_mean_ms']))
    print('round',r_,flush=True)
out={}
for k,v in res.items():
    pm=[a for a,_ in v]; sm=[b for _,b in v]
    out[k]=dict(play_min=round(min(pm),3),play_med=round(float(np.median(pm)),3),sil_med=round(float(np.median(sm)),3),play=pm)
    print(f'{k:16s} play min {min(pm):.3f} med {np.median(pm):.3f}  sil med {np.median(sm):.3f}')
json.dump(out,open(C+'/bench2_results.json','w'),indent=1)
