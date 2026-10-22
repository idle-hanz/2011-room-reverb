"""Sound cost of S5 CPU options in Render (FDN bus, 80 ms+, third-octave, L/R mean, vs exact). argv: case list"""
import os, sys, json, copy, subprocess, numpy as np
H=os.path.dirname(os.path.abspath(__file__)); B='/workspace/build_support_2'; SW=B+'/snapshot_2026-10-03_1600/software'; SR=48000
PY='/workspace/scratch_er_dropout/venv/bin/python'
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.update({"direct_wet":0.0,"early_wet":0.0,"fdn_wet":1.0})
def hs6_all(s):
    for v in s.values(): v['eq']['high_shelf_db']=6.0
CASES={'default':lambda s:None,'hs6_all':hs6_all,
 'carpet_floor':lambda s:s['E'].update(absorb=[0.02,0.06,0.14,0.37,0.60,0.65,0.70]),
 'user_extreme':lambda s:(s['A']['eq'].update(peak_db=12.0,peak_q=4.0,peak_hz=1000),s['C']['eq'].update(low_shelf_db=-12.0),s['E'].update(absorb=[0.01,0.02,0.05,0.2,0.5,0.7,0.9]))}
OPTS=['exact','fit','k3','k2','shared4']
FC=[125,160,200,250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,8000,10000,12500,16000]
def bands(x):
    X=np.abs(np.fft.rfft(x))**2; f=np.fft.rfftfreq(len(x),1/SR); return np.array([X[(f>=c*2**-(1/6))&(f<c*2**(1/6))].sum()+1e-30 for c in FC])
os.makedirs(H+'/opt_irs',exist_ok=True); out={}
for cn in sys.argv[1].split(','):
    b=copy.deepcopy(base); CASES[cn](b['surfaces']); irs={}
    for o in OPTS:
        f=f'{H}/opt_irs/{cn}_{o}.f32'; lg=f'{H}/opt_irs/{cn}_{o}.json'
        if not os.path.exists(f):
            r=subprocess.run(['timeout','300',PY,H+'/render_ir_opt.py',SW,json.dumps(b),f,'1500',str(SR)],env=dict(os.environ,OPT=o,OPTLOG=lg,OMP_NUM_THREADS='1'),capture_output=True,text=True)
            if r.returncode: print(cn,o,'FAIL',r.stderr[-500:],flush=True); continue
        irs[o]=np.fromfile(f,np.float32).reshape(-1,2).astype(np.float64)
    s=int(0.08*SR); ref=[bands(irs['exact'][s:,ch]) for ch in (0,1)]; out[cn]={}
    for o in OPTS[1:]:
        if o not in irs: continue
        d=np.mean([10*np.log10(bands(irs[o][s:,ch])/ref[ch]) for ch in (0,1)],axis=0)
        lg=f'{H}/opt_irs/{cn}_{o}.json'; L=json.load(open(lg)) if os.path.exists(lg) else {}
        lines=L.get('line_err_db') or L.get('line_dev_db') or [0]
        out[cn][o]={'tail_delta_db':[round(float(x),3) for x in d],'tail_max_abs_db':round(float(np.max(np.abs(d))),3),
                    'line_max_err_db':round(float(max(lines)),3),'line_median_err_db':round(float(np.median(lines)),3),**({'shared_fit_err_db':round(L['shared_fit_err_db'],3)} if 'shared_fit_err_db' in L else {})}
        print(cn,o,'tail max|d|',out[cn][o]['tail_max_abs_db'],'line max',out[cn][o]['line_max_err_db'],'median',out[cn][o]['line_median_err_db'],flush=True)
json.dump({'fc':FC,'cases':out},open(H+f'/options_sound_{sys.argv[1].replace(",","_")}.json','w'),indent=1)
