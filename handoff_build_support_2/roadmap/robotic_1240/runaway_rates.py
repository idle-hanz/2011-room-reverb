import json, subprocess, os, numpy as np
P='/workspace/scratch_er_dropout/venv/bin/python'; B='/workspace/build_support_2'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
SW=B+'/snapshot_2026-10-02_1140/software'; FW=os.path.abspath('fixwasm')+'/'
os.makedirs('w',exist_ok=True)
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
HALL=dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0,sx_b=33.0,sz_b=60.0,two_sources=True,mirror_b=True,decay_lock=True)
SC={'hall_2src_decay8':dict(HALL,decay_s=8.0),'hall_binaural_decay8':dict(HALL,decay_s=8.0,mic_setup='binaural'),'hall_binaural_decay4':dict(HALL,decay_s=4.0,mic_setup='binaural'),
    'default_decay8':dict(decay_s=8.0),'default_decay20':dict(decay_s=20.0)}
res={}
for sr in (44100,48000):
  for sn,ov in SC.items():
    b=dict(base,**ov); pj=os.path.abspath(f'w/rr_{sn}_{sr}.json')
    subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(b),pj,str(sr)],check=True,capture_output=True)
    for wn in ('ship','fix_fs'):
        f=os.path.abspath(f'w/rr_{sn}_{sr}_{wn}.f32'); secs='40' if sn=='default_decay20' else '20'
        r=subprocess.run(['node',LIB+'/wasm_run.js',SW,pj,json.dumps({"direct_wet":0,"early_wet":0}),'ir',secs,f],capture_output=True,text=True,env=dict(os.environ,WASM=FW+wn+'.wasm')); assert r.returncode==0,r.stderr[-400:]
        x=np.fromfile(f,np.float32).reshape(-1,2).astype(float); m=x.mean(1); n=len(m)//sr
        lv=[round(float(10*np.log10(np.mean(m[i*sr:(i+1)*sr]**2)+1e-300)),1) for i in range(0,n,2)]
        res[f'{sn}|{sr}|{wn}']=dict(finite=bool(np.all(np.isfinite(x))),levels_every2s=lv,dc_last_s=round(float(np.mean(m[-sr:])),6))
        print(sn,sr,wn,res[f'{sn}|{sr}|{wn}'],flush=True)
json.dump(res,open('runaway_rates.json','w'),indent=1)
