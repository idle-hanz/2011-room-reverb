"""S7 verify (19:05 snapshot): Play vs Render nulls with equal trims, Render 1905 vs 1815 (pre-S7) tail delta,
Render 1905 vs research prototype R_z1 (x -1.70 dB), no-Dffs path, reaktor_parity. Box only, read-only trees."""
import sys, os, json, types, copy, time, numpy as np
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'; HERE=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[HAR, HAR+'/lib', B+'/3_phase_acceptance_tests/tests']
import run_all as RA, parity as PAR
PY='/workspace/scratch_er_dropout/venv/bin/python'; SR=48000
TREES={'S1905':B+'/snapshot_2026-10-02_1905/software','S1815':B+'/snapshot_2026-10-02_1815/software',
       'R_z1':B+'/research_f5_allpass/sw/R_z1/software'}
def ctx(t):
    a=types.SimpleNamespace(sw=TREES[t],python=PY,node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=HERE+'/work/'+t)
    os.makedirs(a.workdir,exist_ok=True); return RA.Ctx(a)
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
FDN={"direct_wet":0.0,"early_wet":0.0,"fdn_wet":1.0,"dry_gain":0.0}; OVER={"direct_wet":0,"early_wet":0}
sys.path.insert(0,B+'/roadmap/robotic_1240'); import hall as HL
def big(): return dict(copy.deepcopy(base),W=57.0,H=34.241,L=97.0,sx=24.925,sz=72.083,mcx=28.5,mcz=24.25)
SCENES={'default':lambda: copy.deepcopy(base),'bigroom':big,'hall_preset':lambda: HL.body('1140',{},True),
        'default_parity':lambda: dict(copy.deepcopy(base),reaktor_parity=True),
        'default_nodffs':lambda: dict(copy.deepcopy(base),diffusion_master=0.0)}
def edb(x): return 10*np.log10(max(float(np.sum(np.asarray(x)**2)),1e-300))
def tail(x): return round(edb(x[int(.08*SR):SR]),2)
def null(a,b,lag=0):
    if lag: a=a[lag:]
    n=min(len(a),len(b)); return [round(RA.null_db(a[:n,c],b[:n,c]),1) for c in (0,1)]
only=sys.argv[1].split(',') if len(sys.argv)>1 else list(SCENES)
C={t:ctx(t) for t in TREES}
res=json.load(open(HERE+'/data/s7_measure.json')) if os.path.exists(HERE+'/data/s7_measure.json') else {}
TRIM=10**(-1.70/20)
for sc in only:
  for cm,oc,ov in (('col',{},{}),('byp',{"colour_mode":"BYPASS"},{"colour_on":False})):
    b=dict(SCENES[sc](),**FDN,**oc); o=dict(OVER,**ov); r={}
    P=C['S1905'].play_ir(b,o,3.0)
    p=json.load(open(C['S1905'].params(b,None)))
    r['dffs_c_absmax']=round(max(abs(v) for v in p['buses']['c']['dffs']),4); r['loop_semantics']=p.get('loop_semantics'); r['g']=p['g']
    R={}
    for t in TREES:
        t0=time.time(); R[t]=C[t].render_ir(b,3000); r[f'render_secs_{t}']=round(time.time()-t0,1)
    r['tail_db']={'play':tail(P),**{t:tail(x) for t,x in R.items()}}
    r['render1905_minus_1815_tail_db']=round(r['tail_db']['S1905']-r['tail_db']['S1815'],2)
    r['null_play_vs_render1905']=null(P,R['S1905'])
    r['null_render1905_vs_Rz1_x_trim']=null(R['S1905'],R['R_z1']*TRIM)
    r['null_render1905_vs_1815_x_trim']=null(R['S1905'],R['S1815']*TRIM)
    m=PAR.full_metrics(P,R['S1905'])
    r['t13_like']=dict(tail_level_db=round(m['tail_level_diff_db_80ms_1s'],2),bal=m['tail_octave_balance_diff_db_(norm)'],
        t30_ratio={k:round(m['t30_play'][k]/m['t30_render'][k],3) for k in m['t30_play'] if m['t30_render'][k]})
    for t,x in R.items(): np.asarray(x,np.float32).tofile(f'{HERE}/work/ir_{sc}_{cm}_{t}.f32')
    np.asarray(P,np.float32).tofile(f'{HERE}/work/ir_{sc}_{cm}_play1905.f32')
    res[f'{sc}|{cm}']=r; print(sc,cm,json.dumps(r),flush=True)
    json.dump(res,open(HERE+'/data/s7_measure.json','w'),indent=1)
