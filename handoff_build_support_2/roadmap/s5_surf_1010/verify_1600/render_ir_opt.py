"""Render IR with an S5 inject-cascade option (box probe; 1600 tree read-only). Env OPT:
exact (shipped Render: exact per-line face chain) | kN (per-line fit with exactly N biquads, N=2,3,4) |
fit (shipped Play fit = fit_line_cascade, K<=4 at defaults) | shared4 (one K=4 cascade for all lines, fitted to the
inject-energy-weighted power mean of the per-line exact chains; models a shared diffuse-lane position). Args as harness render_ir.py."""
import os, sys, runpy, json, numpy as np
from scipy.signal import lfilter
sw=os.path.abspath(sys.argv[1]); sys.path[:0]=[sw, sw+'/engine']; os.chdir(sw)
import render_pipeline as rp, surface_colour as sc
OPT=os.environ.get('OPT','exact'); LOG=os.environ.get('OPTLOG')
orig=rp._scale_inject_reflect
def run(x,rows):
    for b0,b1,b2,a1,a2 in rows: x=lfilter([b0,b1,b2],[1.0,a1,a2],x)
    return x
def patched(inj, taps, surfaces, sr=None, reaktor_parity=False):
    if OPT=='exact' or not sr or reaktor_parity or inj is None or taps is None or not surfaces: return orig(inj,taps,surfaces,sr=sr,reaktor_parity=reaktor_parity)
    n_t=len(taps); nl=int(inj.shape[1]); sr=float(sr); freq=sc._surf_grid(sr); errs=[]; tg=[]; gs=[]
    for i in range(nl):
        g=rp.tap_reflect_gain(taps[i%n_t].n, surfaces); inj[:,i]*=g; gs.append(g)
        st=rp._surf_rel_stages(surfaces, sc.surfaces_hit_by_n(taps[i%n_t].n), sr) if g!=0.0 else []
        t=sc._db_of([sc._norm5(b) for b in st], sr, freq) if st else np.zeros(len(freq)); tg.append(t)
        if OPT=='shared4' or not st: continue
        if OPT=='fit':
            f=sc.fit_line_cascade(st,sr); rows=f['coef']; errs.append(f['residual_db'])
        else:
            K=int(OPT[1:]); e,xv=sc._fit_one(t,K,sr,freq,1 if K<4 else 8); rows=sc._surf_model(xv,K,sr); errs.append(float(np.max(np.abs(sc._db_of(rows,sr,freq)-t))))
        inj[:,i]=run(inj[:,i],rows)
    if OPT=='shared4':
        w=np.array([float(np.sum(inj[:,i]**2)) for i in range(nl)]); P=np.array([10**(t/10) for t in tg]); tm=10*np.log10((w[:,None]*P).sum(0)/max(w.sum(),1e-30))
        e,xv=sc._fit_one(tm,4,sr,freq,8); rows=sc._surf_model(xv,4,sr)
        for i in range(nl): inj[:,i]=run(inj[:,i],rows)
        errs=[float(np.max(np.abs(sc._db_of(rows,sr,freq)-t))) for t in tg]   # shared filter vs each line's own exact chain
        if LOG: json.dump({'shared_fit_err_db':e,'line_dev_db':errs},open(LOG,'w'))
        return
    if LOG: json.dump({'line_err_db':errs},open(LOG,'w'))
rp._scale_inject_reflect=patched
sys.argv=[sys.argv[0]]+sys.argv[1:]
runpy.run_path('/workspace/build_support_2/snapshot_2026-10-03_1600/3_phase_acceptance_tests/harness/lib/render_ir.py', run_name='__main__')
