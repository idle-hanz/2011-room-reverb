"""How many biquads (K) does a per-line hit-face product need? (S5 / D-UI26=A, box only)
Target H_i(f) = prod over hit letters of [absorb peaks relative to card mean] x [face EQ] (same stages as protoA).
Fit: K=2 -> LS+HS, K=3 -> LS+HS+1 peak, K=4 -> +2 peaks, K=6 -> +4 peaks. Error in dB on a log grid 50 Hz-18 kHz."""
import sys, json, copy, itertools, numpy as np
from scipy.optimize import least_squares
from scipy.signal import sosfreqz
sys.path.insert(0,'/workspace/build_support_2/roadmap/s5_surf_1010/protoA_root/software')
import surface_colour as sc, render_pipeline as rp
SR=48000.; F=np.geomspace(50,18000,240)
def resp(stages):
    h=np.ones(len(F),complex)
    for b0,b1,b2,a0,a1,a2 in stages:
        _,hh=sosfreqz([[b0/a0,b1/a0,b2/a0,1,a1/a0,a2/a0]],worN=F,fs=SR); h*=hh
    return 20*np.log10(np.abs(h))
def model(p,K):
    st=[sc.rbj_lowshelf(SR,np.exp(p[0]),p[1]),sc.rbj_highshelf(SR,np.exp(p[2]),p[3])]
    for k in range(K-2): st.append(sc.rbj_peaking(SR,np.exp(p[4+3*k]),np.exp(p[5+3*k]),p[6+3*k]))
    return st
def fit(t,K):
    best=None
    x0=[np.log(250),t[F<300].mean()-t.mean()*0,np.log(4000),t[F>5000].mean()-t[(F>300)&(F<3000)].mean()]
    lo=[np.log(30),-24,np.log(800),-24]; hi=[np.log(2000),24,np.log(16000),24]
    for fk in (np.geomspace(150,10000,K-2) if K>2 else []): x0+= [np.log(fk),np.log(1.0),0.0]; lo+=[np.log(60),np.log(0.3),-24]; hi+=[np.log(16000),np.log(8),24]
    for trial in range(4):
        x=np.array(x0,float)
        if trial: x[4::3]=np.log(np.random.default_rng(trial).uniform(80,12000,K-2)) if K>2 else x[4::3]
        r=least_squares(lambda p: resp(model(p,K))-t, x, bounds=(lo,hi), max_nfev=400)
        e=np.max(np.abs(r.fun))
        if best is None or e<best[0]: best=(e,r.x)
    return best
base=json.load(open('/workspace/build_support_2/roadmap/s4_verify_1140/measure/client_body_1140.json'))['surfaces']
def case(fn): s=copy.deepcopy(base); fn(s); return s
CASES={'default':lambda s:None,
 'hs6_A':lambda s:s['A']['eq'].update(high_shelf_db=6.0),
 'user_extreme':lambda s:(s['A']['eq'].update(peak_db=12.0,peak_q=4.0,peak_hz=1000),s['C']['eq'].update(low_shelf_db=-12.0),s['E'].update(absorb=[0.01,0.02,0.05,0.2,0.5,0.7,0.9])),
 'carpet_floor':lambda s:s['E'].update(absorb=[0.02,0.06,0.14,0.37,0.60,0.65,0.70])}
ns=sorted({n for n in itertools.product(range(-3,4),repeat=3) if sum(map(abs,n))<=4}, key=lambda n:sum(map(abs,n)))
res={}
for cname,fn in CASES.items():
    S=case(fn); sets={}
    for n in ns:
        hit=tuple(sc.surfaces_hit_by_n(n))
        if hit and hit not in sets: sets[hit]=n
    out={}
    for K in (2,3,4,6):
        errs=[]
        for hit in sets:
            st=rp._surf_rel_stages(S,list(hit),SR); t=resp(st) if st else np.zeros(len(F))
            errs.append(0.0 if not st else fit(t,K)[0])
        out[K]={'max_err_db':round(float(max(errs)),3),'p95_err_db':round(float(np.percentile(errs,95)),3),'n_sets':len(errs),
                'exact_stage_count_max':max(len(rp._surf_rel_stages(S,list(h),SR)) for h in sets)}
        print(cname,K,out[K],flush=True)
    res[cname]=out
json.dump(res,open('fit_k.json','w'),indent=1)
