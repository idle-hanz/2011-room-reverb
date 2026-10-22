import json, subprocess, sys, os, numpy as np
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+'/w'; os.makedirs(W,exist_ok=True)
SNAPS=os.environ.get('SNAPS','2026-10-01_1550,2026-10-01_2210,2026-10-02_0615,2026-10-02_0709,2026-10-02_0830,2026-10-02_1140').split(',')
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
big=dict(W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0,sx_b=33.0,sz_b=60.0)
SC={'def1':{}, 'def2':dict(two_sources=True,mirror_b=True),
    'def2v':dict(two_sources=True,mirror_b=True,source_radiation='violin_byu',source_yaw=173.0,source_pitch=5.0),
    'big1':dict(big), 'big2':dict(big,two_sources=True,mirror_b=True),
    'big2v':dict(big,two_sources=True,mirror_b=True,source_radiation='violin_byu',source_yaw=168.0)}
SC={k:v for k,v in SC.items() if k in os.environ.get('SCN',','.join(SC)).split(',')}
FDN_ONLY={"direct_wet":0,"early_wet":0}
def metrics(x, sr=48000):
    m=x.mean(1) if x.ndim>1 else x
    L=x[:,0]; R=x[:,1]
    out={}
    seg=m[int(0.15*sr):int(1.5*sr)]
    # autocorr of late segment (periodicity)
    n=len(seg); f=np.fft.rfft(seg,2*n); ac=np.fft.irfft(np.abs(f)**2)[:n]; ac/=ac[0]+1e-30
    lo=int(0.002*sr); hi=int(0.3*sr); k=np.argmax(ac[lo:hi])+lo
    out['ac_peak']=float(ac[k]); out['ac_lag_ms']=round(k/sr*1000,2)
    # spectral peakiness: average power spectrum of 0.15-1.5s in 4096-pt frames
    N=8192; fr=[seg[i:i+N]*np.hanning(N) for i in range(0,len(seg)-N,N//2)]
    S=np.mean([np.abs(np.fft.rfft(a))**2 for a in fr],0); f_=np.fft.rfftfreq(N,1/sr)
    dB=10*np.log10(S+1e-30); band=(f_>100)&(f_<8000)
    # smooth over 1/3 octave
    sm=np.array([np.mean(S[(f_>=fc/2**(1/6))&(f_<fc*2**(1/6))]) if fc>0 else S[0] for fc in f_])
    dev=dB-10*np.log10(sm+1e-30)
    out['spec_dev_p99']=round(float(np.percentile(dev[band],99)),2); out['spec_dev_max']=round(float(dev[band].max()),2)
    out['spec_dev_std']=round(float(dev[band].std()),2)  # ~5.6 dB for dense noise-like averaged? (averaged frames -> lower)
    # echo density (Abel & Huang), 20 ms window
    def ned(t):
        w=int(0.02*sr); c=int(t*sr); a=m[c-w//2:c+w//2]; s=a.std()
        return float(np.mean(np.abs(a)>s)/0.3173) if s>0 else 0
    out['ned']={t:round(ned(t),2) for t in (0.05,0.1,0.2,0.4,0.8)}
    # decay
    e=np.cumsum((m**2)[::-1])[::-1]; edc=10*np.log10(e/e[0]+1e-30)
    i5=np.argmax(edc<-5); i35=np.argmax(edc<-35); out['T30_s']=round(float((i35-i5)/sr*2),3) if i35>i5 else None
    out['lr_corr']=round(float(np.dot(L[int(.15*sr):],R[int(.15*sr):])/np.sqrt(np.dot(L[int(.15*sr):],L[int(.15*sr):])*np.dot(R[int(.15*sr):],R[int(.15*sr):])+1e-30)),3)
    return out
res={}
for sname,ov in SC.items():
    body=dict(base); body.update(ov)
    for sn in SNAPS:
        sw=f'{B}/snapshot_{sn}/software'; pj=f'{W}/p_{sname}_{sn}.json'; irf=f'{W}/ir_{sname}_{sn}.f32'
        r=subprocess.run([P,LIB+'/dump_params.py',sw,json.dumps(body),pj,'48000'],capture_output=True,text=True)
        if r.returncode: res[f'{sname}|{sn}']={'err':r.stderr[-300:]}; print(sname,sn,'ERR',r.stderr[-300:]); continue
        r=subprocess.run(['node',LIB+'/wasm_run.js',sw,pj,json.dumps(FDN_ONLY),'ir','3',irf],capture_output=True,text=True)
        if r.returncode: res[f'{sname}|{sn}']={'err':r.stderr[-300:]}; print(sname,sn,'ERR',r.stderr[-300:]); continue
        x=np.fromfile(irf,np.float32).reshape(-1,2).astype(np.float64)
        p=json.load(open(pj)); bc=p['buses']['c']; d=bc['delay_ms']
        mt=metrics(x); mt.update(g=p['g'],decay=p.get('decay_s'),hn=p.get('hadamard_n'),n_delay=len(d),n_unique_c=len(set(np.round(d,3))),dmin=round(min(d),2),dmax=round(max(d),2),max_delay_ms=p.get('max_delay_ms'),
            dffs_c=[round(v,3) for v in bc.get('dffs',[])][:6], rms=float(np.sqrt(np.mean(x**2))))
        res[f'{sname}|{sn}']=mt; print(sname,sn,json.dumps(mt),flush=True)
json.dump(res,open(HERE+'/bisect_'+os.environ.get('TAG','all')+'.json','w'),indent=1)
