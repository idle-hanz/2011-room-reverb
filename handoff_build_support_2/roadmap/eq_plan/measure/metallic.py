import numpy as np, sys, json
from math import erfc, sqrt
SR=48000
def load(n, ch):
    x=np.fromfile(n,np.float32).astype(float)
    return x.reshape(-1,2).mean(1) if ch==2 else x
def envnorm(seg, win=480):
    env=np.sqrt(np.convolve(seg**2,np.ones(win)/win,'same'))+1e-15; return seg/env
def acmax(x,t0,t1):
    s=envnorm(x[int(t0*SR):int(t1*SR)]); F=np.fft.rfft(s,n=2*len(s)); ac=np.fft.irfft(np.abs(F)**2)[:len(s)]; ac/=ac[0]
    lo,hi=int(0.002*SR),int(0.05*SR); k=np.argmax(np.abs(ac[lo:hi]))+lo; return float(abs(ac[k])), float(1000*k/SR)
def ned(x,t):
    w=int(0.02*SR); i=int(t*SR); s=x[max(0,i-w//2):i+w//2]; sd=np.std(s); return float(np.mean(np.abs(s)>sd)/erfc(1/sqrt(2)))
def peaky(x,t0,dur=0.5,f0=200,f1=5000):
    s=envnorm(x[int(t0*SR):int((t0+dur)*SR)]); P=np.abs(np.fft.rfft(s*np.hanning(len(s))))**2; f=np.fft.rfftfreq(len(s),1/SR); b=(f>f0)&(f<f1)
    return float(10*np.log10(np.percentile(P[b],99.5)/np.median(P[b])))
def flatness(x,t0,t1,N=2048):
    vals=[]
    for s in range(int(t0*SR),int(t1*SR)-N,N//2):
        P=np.abs(np.fft.rfft(x[s:s+N]*np.hanning(N)))**2+1e-30; f=np.fft.rfftfreq(N,1/SR); b=(f>200)&(f<5000)
        vals.append(np.exp(np.mean(np.log(P[b])))/np.mean(P[b]))
    return float(np.mean(vals))
def t60spread(x,t0,t1,N=8192):
    hop=N//4; w=np.hanning(N); fr=[];ts=[]
    for s in range(int(t0*SR),int(t1*SR)-N,hop): fr.append(np.abs(np.fft.rfft(x[s:s+N]*w))**2); ts.append((s+N/2)/SR)
    S=10*np.log10(np.array(fr)+1e-30); ts=np.array(ts); f=np.fft.rfftfreq(N,1/SR); b=(f>150)&(f<6000)
    A=np.vstack([ts,np.ones_like(ts)]).T; sl=np.linalg.lstsq(A,S[:,b],rcond=None)[0][0]; t60=-60/np.minimum(sl,-1e-3); m=np.median(t60)
    return float(m), float(np.percentile(t60,99)/m)
def hf(x,t0,t1):
    s=x[int(t0*SR):int(t1*SR)]; P=np.abs(np.fft.rfft(s))**2; f=np.fft.rfftfreq(len(s),1/SR)
    return float(10*np.log10(P[(f>8000)&(f<16000)].mean()/P[(f>500)&(f<2000)].mean()))
res={}
for spec in sys.argv[1:]:
    n,ch,t0,t1=spec.split(':'); ch=int(ch); t0=float(t0); t1=float(t1)
    x=load(n,ch)
    a,lag=acmax(x,t0,t1)
    m,p99=t60spread(x,t0*0.5,t1)
    res[n]=dict(acmax=round(a,3),aclag_ms=round(lag,2),ned={str(t):round(ned(x,t),2) for t in (0.05,0.1,0.2,0.4)},
        peak995_db=round(peaky(x,t0),2),flatness=round(flatness(x,t0,t1),3),t60_med=round(m,2),t60_p99_over_med=round(p99,2),hf_tilt_db=round(hf(x,t0,t1),1))
    print(n, json.dumps(res[n]))
json.dump(res,open('metallic_'+str(abs(hash(' '.join(sys.argv[1:])))%10**6)+'.json','w'),indent=1)
