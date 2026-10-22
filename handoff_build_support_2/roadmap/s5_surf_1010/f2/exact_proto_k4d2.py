import sys, os, json, types, numpy as np
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'; HERE=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
a=types.SimpleNamespace(sw=B+'/snapshot_2026-10-03_1010/software',python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=HERE+'/work')
c=RA.Ctx(a); key=RA.find_key(c, r'source_(?:pattern|radiation|directivity)[a-z_]*')
p=c.params('std_lock18',{key:'talking_head','source_radiation_b':'trumpet_byu','source_yaw':35.0,'source_yaw_b':-25.0,'two_sources':True})
ref=np.fromfile(HERE+'/work/t19_0_ship.f32',np.float32)
for k in ('4D2',):
    o=HERE+f'/work/t19_0_surfK{k}.f32'; c.play(p,{'shared_tail':False},'ir',2.0,o,wasm=HERE+f'/SURF_K{k}.wasm')
    print(k, float(np.max(np.abs(np.fromfile(o,np.float32)-ref))))
