# Golden audit: Build regenerated the 5 goldens at 16:07 ("S4b column signs H*D"). Check (a) 16:30 matches Build's goldens,
# (b) 16:30 with the signs off matches the old (06:58) goldens, i.e. the regen is caused by the signs only.
import sys, argparse, tempfile, json, runpy, numpy as np, subprocess
B='/workspace/build_support_2'; H=B+'/3_phase_acceptance_tests'; sys.path[:0]=[H+'/harness',H+'/harness/lib']
import run_all as RA
null_db=RA.null_db
S16=B+'/snapshot_2026-10-02_1630/software'; NEWG=B+'/work/s4b_1630/x/pc_tests/harness/golden'; OLDG=H+'/harness/golden'; W=B+'/work/s4b_1630/w'
ns=argparse.Namespace(sw=S16,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=OLDG,regen_golden=False,quick=False,perf_scale=1.0,workdir=tempfile.mkdtemp())
c=RA.Ctx(ns); res={}
def cmp(gdir,name,arr):
    ref=np.fromfile(f'{gdir}/{name}.f32',np.float32).reshape(-1,2).astype(float); n=min(len(ref),len(arr))
    return {'null_db':round(float(null_db(ref,arr)),1),'max_abs_diff':float(np.max(np.abs(ref[:n]-arr[:n])))}
for sc in ('std_lock18','std_unlocked'):
    for tag,over in (('byp',{"colour_on":False}),('col',{})):
        nm=f'play_{sc}_{tag}'
        res[nm+'|ship_vs_build_golden']=cmp(NEWG,nm,c.play_ir(sc,over,1.5))
        res[nm+'|nocsign_vs_old_golden']=cmp(OLDG,nm,c.play_ir(sc,over,1.5,wasm=W+'/nocsign.wasm'))
body=dict(RA.SCENES['std_unlocked']); body.update({"colour_mode":"BYPASS","direct_wet":1,"fdn_wet":1})
res['render_std_unlocked_byp|ship_vs_build_golden']=cmp(NEWG,'render_std_unlocked_byp',c.render_ir(body,500))
# Render with the signs off: patch fdn.LOOP_COLUMN_D to all +1 inside the render_ir.py process
pat=f'''import sys,runpy; sys.path[:0]=["{S16}","{S16}/engine"]; import fdn; fdn.LOOP_COLUMN_D[:]=1.0
sys.argv=["render_ir.py","{S16}",{json.dumps(json.dumps(body))},"/tmp/ga_r.f32","500","48000"]; runpy.run_path("{H}/harness/lib/render_ir.py",run_name="__main__")'''
subprocess.run(['/workspace/scratch_er_dropout/venv/bin/python','-c',pat],check=True,capture_output=True)
res['render_std_unlocked_byp|nocsign_vs_old_golden']=cmp(OLDG,'render_std_unlocked_byp',np.fromfile('/tmp/ga_r.f32',np.float32).reshape(-1,2).astype(float))
for k,v in res.items(): print(k,v)
json.dump(res,open('golden_audit.json','w'),indent=1)
