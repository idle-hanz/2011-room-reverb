import json, subprocess, os, math, sys
import numpy as np
from scipy import signal
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
SW=B+'/snapshot_2026-10-02_0830/software'; H=os.path.dirname(os.path.abspath(__file__)); PRO=B+'/research_shared_fdn/proto'
SR=48000
V={k:PRO+f'/shared_{k}.wasm' for k in ('m0','m1','m2','m1j03','m1j1')}
base=dict(toe_half_deg=55, space=0.17, decay_lock=True, decay_s=1.8, humidity=0.5, early_wet=1.0, mirror_b=True)
big=dict(W=57.0,H=34.2,L=97.0, sx=24.0, sz=60.0, mcx=28.5, mcz=30.0, decay_s=4.0)
vio=dict(source_radiation='violin_byu', source_yaw=180.0)
S={'def_omni':(base,3),'def_violin':({**base,**vio},3),'big_omni':({**base,**big},7),'big_violin':({**base,**big,**vio},7),
   'bin_def_omni':({**base,'mic_setup':'binaural'},3),'bin_big_omni':({**base,**big,'mic_setup':'binaural'},7),
   'def_hall_lock40':({**base,'decay_s':4.0,'W':20,'H':10,'L':30,'sx':10,'sz':18,'mcx':10,'mcz':6},6)}
for bal in (-1.0,1.0):
    S[f'mir_omni_{bal:+.0f}']=({**base,'two_sources':True,'source_balance':bal},3)
    S[f'mir_violin_{bal:+.0f}']=({**base,**vio,'two_sources':True,'source_balance':bal},3)
TAIL={'early_wet':0,'direct_wet':0,'dry_gain':0}
def params(k):
    out=f'{H}/p_{k}.json'
    if not os.path.exists(out): subprocess.run([P,LIB+'/dump_params.py',SW,json.dumps(S[k][0]),out,str(SR)],check=True,capture_output=True)
    return out
def ir(v,k,over,tag):
    if v not in ('m0','m1','m2','m1j03','m1j1'): pass
    out=f'{H}/ir_{v}_{k}_{tag}.f32'
    if not os.path.exists(out):
        r=subprocess.run(['node',LIB+'/wasm_run.js',SW,params(k),json.dumps(over),'ir',str(S[k][1]),out],capture_output=True,text=True,env=dict(os.environ,WASM=V[v]))
        if r.returncode: raise SystemExit(r.stderr[-400:])
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
OCT=[250,500,1000,2000,4000,8000]
def band(x,fc):
    sos=signal.butter(4,[fc/2**.5,min(fc*2**.5,0.45*SR)],btype='band',fs=SR,output='sos'); return signal.sosfiltfilt(sos,x)
def t30(x):
    e=np.cumsum(x[::-1]**2)[::-1]; e=10*np.log10(e/e[0]+1e-30)
    i5=np.argmax(e<=-5); i35=np.argmax(e<=-35)
    if i35<=i5: return None
    t=np.arange(i5,i35)/SR; a,b=np.polyfit(t,e[i5:i35],1); return round(-60/a,3)
def coh(L,R,t1,t2):
    a,b=int(t1*SR),int(t2*SR)
    f,C=signal.coherence(L[a:b],R[a:b],fs=SR,nperseg=2048)
    return {fc: round(float(np.sqrt(np.mean(C[(f>=fc/2**.5)&(f<fc*2**.5)]))),3) for fc in OCT}
def third(x,a,b):
    X=np.abs(np.fft.rfft(x[a:b]))**2; f=np.fft.rfftfreq(b-a,1/SR); out={}
    for fc in [125,250,500,1000,2000,4000,8000,12500]:
        m=(f>=fc/2**(1/6))&(f<fc*2**(1/6)); out[fc]=10*math.log10(np.sum(X[m])+1e-30)
    return out
ONLY=os.environ.get('ONLY','').split(',') if os.environ.get('ONLY') else None
res=json.load(open(H+'/measure_results.json')) if ONLY else {}
for k in [x for x in S if not x.startswith('mir_') and (not ONLY or x in ONLY)]:
    win=(0.08,1.0) if not k.startswith(('big','bin_big')) else (0.25,2.5)
    if k=='def_hall_lock40': win=(0.15,2.0)
    r={}
    for v in V:
        y=ir(v,k,TAIL,'tail'); yf=ir(v,k,{},'full')
        a,b=int(win[0]*SR),int(win[1]*SR)
        r[v]={'t30_L':{fc:t30(band(y[:,0],fc)) for fc in OCT},'t30_R':{fc:t30(band(y[:,1],fc)) for fc in OCT},
              'coh_LR_tail':coh(y[:,0],y[:,1],*win),'coh_LR_full':coh(yf[:,0],yf[:,1],*win),
              'tail_third_L':third(y[:,0],a,b),'tail_third_R':third(y[:,1],a,b),
              'tail_rms_db':round(10*math.log10(np.mean(y[a:b]**2)+1e-30),2),
              'peak_full':round(float(np.max(np.abs(yf))),4),'finite':bool(np.all(np.isfinite(yf))),
              'end_db':round(10*math.log10(np.mean(yf[-int(0.2*SR):]**2)+1e-30)-10*math.log10(np.mean(yf[a:b]**2)+1e-30),1)}
    for v in [x for x in V if x!='m0']:
        r[v]['spec_diff_vs_m0_L']={fc:round(r[v]['tail_third_L'][fc]-r['m0']['tail_third_L'][fc],2) for fc in r['m0']['tail_third_L']}
        r[v]['spec_diff_vs_m0_R']={fc:round(r[v]['tail_third_R'][fc]-r['m0']['tail_third_R'][fc],2) for fc in r['m0']['tail_third_R']}
    res[k]=r
    print(k, {v:(r[v]['t30_L'][1000],r[v]['coh_LR_tail'],r[v]['tail_rms_db']) for v in V}, flush=True)
# mirror symmetry (tail only): B.L vs A.R
for kind in (('omni','violin') if not ONLY else ()):
    r={}
    for v in V:
        A=ir(v,f'mir_{kind}_-1',TAIL,'tail'); Bm=ir(v,f'mir_{kind}_+1',TAIL,'tail')
        a,b=int(0.0*SR),int(1.0*SR)
        null=20*math.log10(np.max(np.abs(Bm[a:b,0]-A[a:b,1]))/np.max(np.abs(A[a:b]))+1e-30)
        tA=third(A[:,1],int(0.08*SR),int(1.0*SR)); tB=third(Bm[:,0],int(0.08*SR),int(1.0*SR))
        r[v]={'swap_null_db':round(null,1),'band_diff_B.L_minus_A.R':{fc:round(tB[fc]-tA[fc],2) for fc in tA}}
    res[f'mirror_{kind}']=r; print('mirror',kind,{v:r[v]['swap_null_db'] for v in V},flush=True)
json.dump(res,open(H+'/measure_results.json','w'),indent=1,default=str)
