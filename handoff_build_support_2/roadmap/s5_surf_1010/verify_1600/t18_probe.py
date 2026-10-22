"""t18 on the box (1600 tree + 9b7cdf) and its cause: Render with Play's fitted cascade (OPT=fit) vs Play."""
import sys, os, json, types, subprocess, numpy as np
H=os.path.dirname(os.path.abspath(__file__)); B='/workspace/build_support_2'; HAR=B+'/snapshot_2026-10-03_1600/3_phase_acceptance_tests/harness'
sys.path[:0]=[HAR,HAR+'/lib']; import run_all as RA
SW=B+'/snapshot_2026-10-03_1600/software'; os.makedirs(H+'/work_t18',exist_ok=True)
c=RA.Ctx(types.SimpleNamespace(sw=SW,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=H+'/work_t18'))
body=dict(RA.SCENES['std_lock18']); body.update({"early_wet":0,"direct_wet":0,"fdn_wet":1,"colour_mode":"BYPASS"})
R=c.render_ir(body,2000); P=c.play_ir('std_lock18',{"colour_on":False,"early_wet":0,"direct_wet":0},2.0)
out={'t18_exact_null_db':[round(RA.null_db(R[:,k],P[:,k]),1) for k in (0,1)]}
f=H+'/work_t18/render_fit.f32'
if not os.path.exists(f):
    subprocess.run(['timeout','300','/workspace/scratch_er_dropout/venv/bin/python',H+'/render_ir_opt.py',SW,json.dumps(body),f,'2000','48000'],env=dict(os.environ,OPT='fit',OMP_NUM_THREADS='1'),check=True,capture_output=True)
RF=np.fromfile(f,np.float32).reshape(-1,2).astype(np.float64)
out['t18_render_with_play_fit_null_db']=[round(RA.null_db(RF[:,k],P[:,k]),1) for k in (0,1)]
out['render_fit_vs_render_exact_null_db']=[round(RA.null_db(R[:,k],RF[:,k]),1) for k in (0,1)]
print(out); json.dump(out,open(H+'/t18_probe.json','w'),indent=1)
