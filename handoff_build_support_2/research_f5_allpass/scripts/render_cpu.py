"""Render loop cost: R_cur (M solve, 2 matvecs/sample) vs R_z1 (1 matvec/sample). 32 lines, Dffs on, 0.5 s at 48 k, min of 3."""
import sys, time, json, importlib.util as U, numpy as np
R='/workspace/build_support_2/research_f5_allpass'
res={}
for t in ('R_cur','R_z1'):
    sp=U.spec_from_file_location('fdn_'+t,f'{R}/sw/{t}/software/engine/fdn.py'); m=U.module_from_spec(sp); sys.path.insert(0,f'{R}/sw/{t}/software/engine'); sp.loader.exec_module(m)
    rng=np.random.default_rng(0); delays=[int(x) for x in rng.integers(400,2400,32)]; dffs=list(rng.uniform(-0.9,0.9,32))
    ts=[]
    for k in range(3):
        f=m.FDN(delays,g=1/np.sqrt(32),room=(6.,3.,8.),peaking=False,n=32,dffs=dffs)
        inj=np.zeros((24000,32)); inj[0,:]=1
        t0=time.perf_counter(); f.process_block_poly(inj); ts.append(time.perf_counter()-t0)
    res[t]=round(min(ts),3); print(t,ts,flush=True)
res['ratio_z1_over_cur']=round(res['R_z1']/res['R_cur'],3)
json.dump(res,open(f'{R}/data/render_cpu.json','w'),indent=1); print(res)
