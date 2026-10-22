import sys, os, json, types, copy, numpy as np
B='/workspace/build_support_2'; R=B+'/research_f5_allpass'
HAR=B+'/3_phase_acceptance_tests/harness'
sys.path[:0]=[HAR, HAR+'/lib', B+'/3_phase_acceptance_tests/tests']
import run_all as RA
import parity as PAR
PY='/workspace/scratch_er_dropout/venv/bin/python'
SNAP=B+'/snapshot_2026-10-02_1140/software'
TREES={'R_ship':SNAP,'R_cur':R+'/sw/R_cur/software','R_z1':R+'/sw/R_z1/software'}
WASM={'P_ship':B+'/roadmap/robotic_1240/fixwasm/ship.wasm','P_old':R+'/c/base.wasm','P_apd':R+'/c/apd.wasm','P_f5':R+'/c/f5.wasm'}
SR=48000
def ctx(tree):
    a=types.SimpleNamespace(sw=TREES[tree],python=PY,node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=R+'/data/tmp')
    os.makedirs(a.workdir,exist_ok=True); return RA.Ctx(a)
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
FDN={"direct_wet":0.0,"early_wet":0.0,"fdn_wet":1.0,"dry_gain":0.0}
OVER={"direct_wet":0,"early_wet":0}
def big():
    return dict(copy.deepcopy(base),W=57.0,H=34.241,L=97.0,sx=24.925,sz=72.083,mcx=28.5,mcz=24.25)
def hallp():
    import importlib.util as U
    sp=U.spec_from_file_location('hall_r12',B+'/roadmap/robotic_1240/hall.py'); HL=U.module_from_spec(sp); sp.loader.exec_module(HL)
    return HL.body('1140',{},True)
SCENES={'default':lambda: copy.deepcopy(base),'bigroom':big,'hall_preset':hallp,
        'binaural':lambda: dict(copy.deepcopy(base),mic_setup='binaural')}
OCT=[63,125,250,500,1000,2000,4000,8000]
def edb(x): return 10*np.log10(max(float(np.sum(np.asarray(x)**2)),1e-300))
def tail_level(x): return edb(x[int(.08*SR):SR])
def octaves(x):
    from analyze import band
    s=x[int(.08*SR):SR]; return [round(edb(band(s.mean(1),SR,fc))-edb(s.mean(1)),2) for fc in OCT]
def t30(x):
    m=x.mean(1); sch=np.cumsum((m**2)[::-1])[::-1]; sch=10*np.log10(sch/sch[0]+1e-300)
    i=np.argmax(sch<=-5); j=np.argmax(sch<=-35)
    return round((j-i)/SR*2,3) if j>i else None
def corr(x):
    s=slice(int(.08*SR),SR); l,r=x[s,0],x[s,1]; return round(float(np.dot(l,r)/np.sqrt(np.dot(l,l)*np.dot(r,r)+1e-300)),3)
def comb(x):
    import test_s4b_tail_solo_runaway as T
    return [round(v,2) for v in T._comb_db(x[:int(1.5*SR)],SR)], [round(v,3) for v in T._acmax(x[:int(1.5*SR)],SR)]
def metrics(x):
    c,a=comb(x)
    return dict(tail_db=round(tail_level(x),2),oct_db=octaves(x),T30=t30(x),corr=corr(x),comb_db=c,ac_max=a)
def null(a,b,lag=0):
    if lag: a=a[lag:]; 
    n=min(len(a),len(b)); return [round(RA.null_db(a[:n,c],b[:n,c]),1) for c in (0,1)]
