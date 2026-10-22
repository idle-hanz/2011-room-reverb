"""Generate Play + Render IRs for one software tree (box, read-only snapshots). argv: sw_dir out_dir
Uses the 1600 harness (backward compatible: only adds surf_cascade/shared_tail forwarding and medians)."""
import sys, os, json, types, copy, numpy as np
B='/workspace/build_support_2'; HAR=B+'/snapshot_2026-10-03_1600/3_phase_acceptance_tests/harness'
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
SW, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT+'/cache', exist_ok=True)
c=RA.Ctx(types.SimpleNamespace(sw=SW,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=OUT+'/cache'))
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.update({"direct_wet":1.0,"early_wet":1.0,"fdn_wet":1.0})
def flat(b):
    for s in b['surfaces'].values():
        m=sum(s['absorb'])/len(s['absorb']); s['absorb']=[m]*len(s['absorb'])
        for k in ('low_shelf_db','peak_db','high_shelf_db'): s['eq'][k]=0
def parity(b): b['reaktor_parity']=True
def hs6_all(b):
    for s in b['surfaces'].values(): s['eq']['high_shelf_db']=6.0
CASES={'default':None,'flat':flat,'parity':parity,'hs6_all':hs6_all}
BUS={'mix':{},'fdn':{"direct_wet":0.0,"early_wet":0.0},'early':{"direct_wet":0.0,"fdn_wet":0.0}}
for cn,fn in CASES.items():
    for bn,ov in BUS.items():
        if cn in ('parity',) and bn=='early': continue
        b=dict(copy.deepcopy(base),**ov)
        if fn: fn(b)
        c.render_ir(b,1500).astype(np.float32).tofile(f'{OUT}/render_{cn}_{bn}.f32')
        c.play_ir(b,{},1.5).astype(np.float32).tofile(f'{OUT}/play_{cn}_{bn}.f32')
        print(cn,bn,flush=True)
# t19 scene (std_lock18 + two radiating sources), Play, shared tail off, 2 s
key=RA.find_key(c, r'source_(?:pattern|radiation|directivity)[a-z_]*')
p=c.params('std_lock18',{key:'talking_head','source_radiation_b':'trumpet_byu','source_yaw':35.0,'source_yaw_b':-25.0,'two_sources':True})
c.play(p,{'shared_tail':False},'ir',2.0,f'{OUT}/play_t19.f32')
json.dump({'params':str(p)},open(f'{OUT}/t19_params_path.json','w'))
print('t19 done')
