"""FDN-only level vs diffusion_master and air_lp (std scene, source pinned). Usage: python diffusion_sensitivity.py /path/to/software"""
import sys, argparse, numpy as np
H='/workspace/build_support_2/3_phase_acceptance_tests/harness'; sys.path[:0]=[H,H+'/lib']
import run_all as RA
ns=argparse.Namespace(sw=sys.argv[1],python=sys.executable,node='node',golden=H+'/golden',regen_golden=False,quick=True,perf_scale=1.0,workdir='/tmp')
c=RA.Ctx(ns)
e=lambda x: round(10*np.log10(float(np.sum(x*x))),2)
for dm in (-0.5,-0.25):
  for air in (0.25,0.0):
    b=dict(RA.SCENES['std_lock18'],sx=3.0,sy=1.5,fdn_wet=1.0,direct_wet=0.0,early_wet=0.0,diffusion_master=dm,air_lp=air)
    print(dm,air,'play',e(c.play_ir(b,{},3.0)),'render',e(c.render_ir(b,3000)),flush=True)
