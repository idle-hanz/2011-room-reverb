"""S5 / D-UI26=A before/after guitar renders (Render only; box only). before = shipped Render (1010),
after = prototype A (face shape on the FDN inject). Dry = dry_est_0.001.npy (44.1k -> 48k, resample_poly 160/147).
Each pair level-matched: 'after' scaled to the 'before' broadband RMS (gain logged)."""
import sys, os, json, types, copy, numpy as np
from scipy.signal import resample_poly, fftconvolve
from scipy.io import wavfile
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'; HERE=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
def ctx(sw,wd):
    os.makedirs(wd,exist_ok=True)
    return RA.Ctx(types.SimpleNamespace(sw=sw,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=wd))
C0=ctx(B+'/snapshot_2026-10-03_1010/software',HERE+'/work_r0'); CA=ctx(B+'/roadmap/s5_surf_1010/protoA_root/software',HERE+'/work_ra')
MS=3000
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.update({"direct_wet":1.0,"early_wet":1.0,"fdn_wet":1.0})
def hs6_all(b):
    for s in b['surfaces'].values(): s['eq']['high_shelf_db']=6.0
def carpet_floor(b): b['surfaces']['E']['absorb']=[0.02,0.06,0.14,0.37,0.60,0.65,0.70]
dry=resample_poly(np.load(B+'/roadmap/robotic_1240/real/dry_est_0.001.npy').astype(np.float64).ravel(),160,147)[:20*48000]  # first 20 s
CASES={'default':None,'hs6_allfaces':hs6_all,'carpet_floor':carpet_floor}
BUS={'mix':{},'tailonly':{"direct_wet":0.0,"early_wet":0.0}}
log={}
for cn,fn in CASES.items():
    for bn,over in BUS.items():
        b=dict(copy.deepcopy(base),**over)
        if fn: fn(b)
        ys={}
        for tag,C in (('before',C0),('after',CA)):
            ir=C.render_ir(b,MS); ys[tag]=np.stack([fftconvolve(dry,ir[:,ch]) for ch in (0,1)],1)
        rms=lambda y: float(np.sqrt(np.mean(y**2)))
        g=rms(ys['before'])/rms(ys['after']); ys['after']*=g
        pk=max(np.abs(ys['before']).max(),np.abs(ys['after']).max()); norm=0.5/pk
        for tag,y in ys.items():
            wavfile.write(HERE+f'/{cn}_{bn}_{tag}.wav',48000,np.round(np.clip(y*norm,-1,1)*32767).astype(np.int16))
        log[f'{cn}_{bn}']={'after_gain_db':round(20*np.log10(g),3),'shared_norm_db':round(20*np.log10(norm),2),
                           'null_after_vs_before_db':round(RA.null_db(ys['after'].ravel(),ys['before'].ravel()),1)}
        print(cn,bn,log[f'{cn}_{bn}'],flush=True)
json.dump(log,open(HERE+'/guitar_ab.json','w'),indent=1)
