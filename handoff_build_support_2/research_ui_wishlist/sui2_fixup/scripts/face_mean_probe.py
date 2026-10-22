"""Control: does face A's MEAN absorption reach the FDN tail? (absorb +0.30 in every band). FDN-only bus, Render and Play."""
import sys, json, types, copy, numpy as np
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
SW=B+'/snapshot_2026-10-03_0818/software'; OUT=B+'/research_ui_wishlist/sui2_fixup/'
a=types.SimpleNamespace(sw=SW,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir='/tmp')
c=RA.Ctx(a); SR=48000; MS=1500
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
base.update({"direct_wet":0.0,"early_wet":0.0,"fdn_wet":1.0})
b1=copy.deepcopy(base); b1['surfaces']['A']['absorb']=[min(0.95,x+0.3) for x in b1['surfaces']['A']['absorb']]
res={}
for eng in ('render','play'):
    get=(lambda b: c.render_ir(b,MS)) if eng=='render' else (lambda b: c.play_ir(b,{},MS/1000))
    x0=get(base); x1=get(b1); n80=int(0.08*SR)
    res[eng]={'tail_energy_delta_db':[round(10*np.log10(np.sum(x1[n80:,ch]**2)/np.sum(x0[n80:,ch]**2)),2) for ch in (0,1)],
              'tail_null_db':[round(RA.null_db(x1[n80:,ch],x0[n80:,ch]),1) for ch in (0,1)]}
    print(eng,res[eng],flush=True)
json.dump(res,open(OUT+'data/face_mean_probe.json','w'),indent=1)
