"""Box preview of the narrowed early-parity gate (D-S5c-4), new tree 9b7cdf: |dPlay - dRender| third-octave 125 Hz-16 kHz, L/R mean.
default: shaped minus flat. face A / all faces HS+6: case minus default. Windows 0-80 ms and 80 ms+. Buses mix and early."""
import sys, os, json, types, copy, numpy as np
H=os.path.dirname(os.path.abspath(__file__)); B='/workspace/build_support_2'; HAR=B+'/snapshot_2026-10-03_1600/3_phase_acceptance_tests/harness'
sys.path[:0]=[HAR,HAR+'/lib']; import run_all as RA
SW=B+'/snapshot_2026-10-03_1600/software'; N=H+'/new_9b7cdf'; os.makedirs(N+'/cache',exist_ok=True); SR=48000
c=RA.Ctx(types.SimpleNamespace(sw=SW,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=N+'/cache'))
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.update({"direct_wet":1.0,"early_wet":1.0,"fdn_wet":1.0})
BUS={'mix':{},'early':{"direct_wet":0.0,"fdn_wet":0.0}}
for bn,ov in BUS.items():
    f=f'{N}/play_hs6_A_{bn}.f32'
    if not os.path.exists(f):
        b=dict(copy.deepcopy(base),**ov); b['surfaces']['A']['eq']['high_shelf_db']=6.0
        c.render_ir(b,1500).astype(np.float32).tofile(f'{N}/render_hs6_A_{bn}.f32'); c.play_ir(b,{},1.5).astype(np.float32).tofile(f)
FC=[125,160,200,250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,8000,10000,12500,16000]
def bands(x):
    X=np.abs(np.fft.rfft(x))**2; f=np.fft.rfftfreq(len(x),1/SR); return np.array([X[(f>=q*2**-(1/6))&(f<q*2**(1/6))].sum()+1e-30 for q in FC])
def ld(n): return np.fromfile(f'{N}/{n}.f32',np.float32).reshape(-1,2).astype(np.float64)
W={'0-80ms':(0,int(.08*SR)),'80ms+':(int(.08*SR),None)}
out={}
for case,(num,den) in {'default_vs_flat':('default','flat'),'faceA_hs6':('hs6_A','default'),'allfaces_hs6':('hs6_all','default')}.items():
    for bus in ('mix','early'):
        for w,(a,b) in W.items():
            if bus=='early' and w=='80ms+': continue
            d=lambda e: np.mean([10*np.log10(bands(ld(f'{e}_{num}_{bus}')[a:b,ch])/bands(ld(f'{e}_{den}_{bus}')[a:b,ch])) for ch in (0,1)],axis=0)
            g=np.abs(d('play')-d('render')); i=int(np.argmax(g)); out[f'{case}|{bus}|{w}']={'max_abs_db':round(float(g.max()),3),'at_hz':FC[i]}
            print(case,bus,w,out[f'{case}|{bus}|{w}'],flush=True)
json.dump(out,open(H+'/parity_cases.json','w'),indent=1)
