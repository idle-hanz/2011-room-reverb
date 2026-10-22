import json,numpy as np
SR=48000
def sweep(T=4.0,L=0):
    f1,f2=10.0,23000.0;n=int(T*SR);t=np.arange(n)/SR;Lr=T/np.log(f2/f1)
    x=np.sin(2*np.pi*f1*Lr*(np.exp(t/Lr)-1));fade=int(0.02*SR);w=np.ones(n);w[:fade]=0.5-0.5*np.cos(np.pi*np.arange(fade)/fade);w[-fade:]=w[:fade][::-1]
    return x*w*10**(L/20),Lr
def fr(i,d="/workspace/uad/out"):
    m=json.load(open(f"{d}/{i}.json")); y=np.load(f"{d}/{i}.npz")["y"].astype(float)
    x,Lr=sweep(m["sig"]["dur_s"],m["sig"]["level_db"])
    N=1<<int(np.ceil(np.log2(len(y)+len(x))))
    X=np.fft.rfft(x,N);Y=np.fft.rfft(y,N)
    H=Y*np.conj(X)/(np.abs(X)**2+1e-3*np.max(np.abs(X))**2*1e-6)
    h=np.fft.irfft(H,N)
    # linear IR around 0 (allow small negative times wrap)
    pre=int(0.01*SR); hl=np.concatenate([h[-pre:],h[:int(0.2*SR)]])
    w=np.ones_like(hl); r=int(0.005*SR); w[:r]=0.5-0.5*np.cos(np.pi*np.arange(r)/r)
    hl=hl*w
    F=np.fft.rfftfreq(1<<18,1/SR); A=20*np.log10(np.abs(np.fft.rfft(hl,1<<18))+1e-20)
    ref=np.interp(1000,F,A); return m,F,A-ref,ref
