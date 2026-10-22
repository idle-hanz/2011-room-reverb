# Same measurement as test_binaural_play_tail_coherence_matches_head (8 s decay, tail only, 1/3 oct vs SADIE2_KU100 target), per variant.
import json, subprocess, os, sys
import numpy as np
B='/workspace/build_support_2'; SW=B+'/snapshot_2026-10-02_0830/software'; LIB=B+'/3_phase_acceptance_tests/harness/lib'; SR=48000
sys.path.insert(0, SW+'/../handoff_binaural'); from binaural_fitter import tail_ic as T
PRO=os.path.dirname(os.path.abspath(__file__))+'/../proto'
V={'m0':PRO+'/v3/m0.wasm','m1':PRO+'/v3/m1.wasm','cand':PRO+'/v3/cand.wasm','fx':PRO+'/v3/fx.wasm'}
for j in ('j150_s0','j300_s0','j600_s2'): V[j]=PRO+f'/sweep/{j}.wasm'
BASE={"decay_lock":True,"decay_s":8.0,"humidity":0.5,"early_wet":1.0,"mic_setup":"binaural","binaural_preset":"SADIE2_KU100"}
pj='/tmp/bic_p.json'; subprocess.run([sys.executable,LIB+'/dump_params.py',SW,json.dumps(BASE),pj,str(SR)],check=True,capture_output=True)
ft,ict=T.target_ic('SADIE2_KU100'); want=np.interp(np.log(T.THIRD_OCT),np.log(ft),ict); res={'bands_hz':list(map(float,T.THIRD_OCT)),'target':[round(float(x),3) for x in want]}
for v,w in V.items():
    subprocess.run(['node',LIB+'/wasm_run.js',SW,pj,json.dumps({"early_wet":0,"direct_wet":0}),'ir','4.6','/tmp/bic.f32'],check=True,capture_output=True,env=dict(os.environ,WASM=w))
    x=np.fromfile('/tmp/bic.f32',np.float32).reshape(-1,2).astype(float); a0=int(0.1*SR)+256
    f,c=T.measure_ic(x[a0:,0],x[a0:,1],SR); got=T.band_ic(f,c,T.THIRD_OCT); d=got-want
    res[v]={'got':[round(float(g),3) for g in got],'max_abs_dIC':round(float(np.max(np.abs(d))),3),'rms_dIC':round(float(np.sqrt(np.mean(d**2))),3),'worst_band_hz':float(T.THIRD_OCT[int(np.argmax(np.abs(d)))]),
            'pass_0.15_0.06':bool(np.max(np.abs(d))<=0.15 and np.sqrt(np.mean(d**2))<=0.06)}
    print(v,res[v]['max_abs_dIC'],res[v]['rms_dIC'],res[v]['worst_band_hz'],res[v]['pass_0.15_0.06'],flush=True)
json.dump(res,open(os.path.dirname(os.path.abspath(__file__))+'/binaural_ic_results.json','w'),indent=1)
