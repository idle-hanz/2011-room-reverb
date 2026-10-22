"""Bit-exactness of rebuilt / F1 / F2 wasm vs shipped a80209d2e69c (1010 snapshot). Play IR 2 s, shared tail off/on,
t19 scene (two sources, radiation), default client body, parity snapshot, binaural."""
import sys, os, json, types, numpy as np
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'; HERE=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
a=types.SimpleNamespace(sw=B+'/snapshot_2026-10-03_1010/software',python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=HERE+'/work')
os.makedirs(a.workdir,exist_ok=True); c=RA.Ctx(a)
key=RA.find_key(c, r'source_(?:pattern|radiation|directivity)[a-z_]*')
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
scenes={'t19':c.params('std_lock18',{key:'talking_head','source_radiation_b':'trumpet_byu','source_yaw':35.0,'source_yaw_b':-25.0,'two_sources':True}),
        'default':c.params(base),'parity':c.params(dict(base,reaktor_parity=True)),'binaural':c.params(dict(base,mic_setup='binaural',binaural=True)),
        'hall':c.params('hall_lock40')}
VAR={'ship':None,'rebuilt':HERE+'/rebuilt_1010.wasm','F1':HERE+'/F1.wasm','F2':HERE+'/F2.wasm'}
out={}
for sn,p in scenes.items():
    for sh in (False,True):
        ref=None
        for v,w in VAR.items():
            o=os.path.join(a.workdir,f'{sn}_{int(sh)}_{v}.f32'); c.play(p,{'shared_tail':sh},'ir',2.0,o,wasm=w)
            x=np.fromfile(o,np.float32).astype(np.float64)
            if ref is None: ref=x; out[f'{sn}_shared{int(sh)}_rms_db']=round(10*np.log10(np.mean(ref**2)+1e-300),2)
            else: out[f'{sn}_shared{int(sh)}_{v}_maxabs']=float(np.max(np.abs(x-ref)))
        print(sn, sh, {k:v for k,v in out.items() if k.startswith(f'{sn}_shared{int(sh)}')}, flush=True)
json.dump(out,open(HERE+'/exact_1010.json','w'),indent=1)
