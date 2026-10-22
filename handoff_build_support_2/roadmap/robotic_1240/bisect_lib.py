import numpy as np
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
