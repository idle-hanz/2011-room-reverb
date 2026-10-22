# Gate audit: binaural Play tail IC (exact method of test_binaural_play_tail_coherence_matches_head) for
# shipped 16:30 (H·D), 16:30 with g_csign=0 (plain H), shipped 11:40; plus scene/length variants to size estimator noise.
import json, subprocess, os, sys
import numpy as np
B='/workspace/build_support_2'; LIB=B+'/3_phase_acceptance_tests/harness/lib'; SR=48000; PY='/workspace/scratch_er_dropout/venv/bin/python'
S16=B+'/snapshot_2026-10-02_1630/software'; S11=B+'/snapshot_2026-10-02_1140/software'; W=B+'/work/s4b_1630/w'
sys.path.insert(0, S16+'/../handoff_binaural'); from binaural_fitter import tail_ic as T
WA={'HD_1630':(S16,S16+'/static/wasm/live_stereo.wasm'),'plainH_1630':(S16,W+'/nocsign.wasm'),'ship_1140':(S11,S11+'/static/wasm/live_stereo.wasm')}
BASE={"decay_lock":True,"decay_s":8.0,"humidity":0.5,"early_wet":1.0,"mic_setup":"binaural","binaural_preset":"SADIE2_KU100"}
SCN={'test_scene_4.6s':({},4.6),'test_scene_9s':({},9.0),'src_x2':({'sx':2.0},4.6),'src_z5':({'sz':5.0},4.6),'mic_off':({'mcx':2.5},4.6),'two_src':({'two_sources':True},4.6),'decay6':({'decay_s':6.0},4.6)}
ft,ict=T.target_ic('SADIE2_KU100'); want=np.interp(np.log(T.THIRD_OCT),np.log(ft),ict)
res={'bands_hz':[float(x) for x in T.THIRD_OCT],'target':[round(float(x),3) for x in want]}
for sn,(ov,secs) in SCN.items():
  for v,(sw,w) in WA.items():
    body=dict(BASE,**ov); pj=f'/tmp/bica_{v}_{sn}.json'
    subprocess.run([PY,LIB+'/dump_params.py',sw,json.dumps(body),pj,str(SR)],check=True,capture_output=True)
    subprocess.run(['node',LIB+'/wasm_run.js',sw,pj,json.dumps({"early_wet":0,"direct_wet":0}),'ir',str(secs),'/tmp/bica.f32'],check=True,capture_output=True,env=dict(os.environ,WASM=w))
    x=np.fromfile('/tmp/bica.f32',np.float32).reshape(-1,2).astype(float); a0=int(0.1*SR)+256
    f,c=T.measure_ic(x[a0:,0],x[a0:,1],SR); got=T.band_ic(f,c,T.THIRD_OCT); d=got-want
    r={'got':[round(float(g),3) for g in got],'d':[round(float(e),3) for e in d],'max_abs_dIC':round(float(np.max(np.abs(d))),4),'rms_dIC':round(float(np.sqrt(np.mean(d**2))),4),'worst_band_hz':float(T.THIRD_OCT[int(np.argmax(np.abs(d)))])}
    res[f'{sn}|{v}']=r; print(sn,v,r['max_abs_dIC'],r['rms_dIC'],r['worst_band_hz'],flush=True)
json.dump(res,open('binaural_ic_audit.json','w'),indent=1)
