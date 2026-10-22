# Gate audit: P0.2 'T60 independent of Dffs' (exact method of test_p0_2_t60_play_independent_of_dffs) with H·D (shipped 16:30)
# vs plain H (16:30, g_csign=0) vs shipped 11:40. Plus the std/small/hall dial scenes for context.
import sys, json, argparse, numpy as np, tempfile
B='/workspace/build_support_2'; H=B+'/3_phase_acceptance_tests'
sys.path[:0]=[H+'/harness',H+'/harness/lib']
import run_all as RA
from analyze import t60_bands
S16=B+'/snapshot_2026-10-02_1630/software'; S11=B+'/snapshot_2026-10-02_1140/software'; W=B+'/work/s4b_1630/w'
V={'HD_1630':(S16,None),'plainH_1630':(S16,W+'/nocsign.wasm'),'ship_1140':(S11,None)}
BANDS=[250,500,1000,2000,4000,8000]; FDN_ONLY={"colour_on": False, "early_wet": 0, "direct_wet": 0}
res={}
for v,(sw,w) in V.items():
    ns=argparse.Namespace(sw=sw,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=H+'/harness/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=tempfile.mkdtemp())
    c=RA.Ctx(ns)
    base=json.loads(open(c.params('std_lock18')).read())
    for d in (0.0,-0.5,-0.9,None):
        b=json.loads(json.dumps(base))
        if d is not None:
            for ch in 'lcr': b['buses'][ch]['dffs']=[d]*32
        pj=c.work/f'p_{d}.json'; pj.write_text(json.dumps(b)); out=c.work/f'o_{d}.f32'
        c.play(pj,FDN_ONLY,'ir',5,out,wasm=w)
        x=np.fromfile(out,np.float32).reshape(-1,2).astype(float)
        tl=t60_bands(x[:,0],48000,bands=BANDS); tr=t60_bands(x[:,1],48000,bands=BANDS)
        r={'L':{b_:round(float(tl[b_]),3) for b_ in BANDS},'R':{b_:round(float(tr[b_]),3) for b_ in BANDS}}
        r['L_err_pct']={b_:round(100*(float(tl[b_])/1.8-1),1) for b_ in BANDS}
        res[f'{v}|dffs={d}']=r; print(v,'dffs',d,r['L'],r['L_err_pct'],'R',r['R'],flush=True)
    for sc in ('std_lock18','small_lock08','hall_lock40'):
        dial=RA.SCENES[sc]['decay_s']; x=c.play_ir(sc,FDN_ONLY,max(4,2.5*dial),wasm=w)
        t=t60_bands(x[:,0],48000,bands=BANDS); res[f'{v}|{sc}']={b_:round(float(t[b_]),3) for b_ in BANDS}; print(v,sc,dial,res[f'{v}|{sc}'],flush=True)
json.dump(res,open('t30_dffs_audit.json','w'),indent=1)
