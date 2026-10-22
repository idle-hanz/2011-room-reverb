import json, numpy as np
SR=48000
def load(i, d="/workspace/uad/out"):
    m=json.load(open(f"{d}/{i}.json")); z=np.load(f"{d}/{i}.npz"); return m,{k:z[k] for k in z.files}
def stair(i):
    m,z=load(i); dec=int(z["dec"]); fs=SR/dec
    ei,eo=z["env_in"].astype(float),z["env_out"].astype(float)
    st=m["sig"]["step_s"]; L=m["sig"]["levels"]; rows=[]
    for k,lv in enumerate(L):
        a=int((k+1)*st*fs-0.3*fs); b=int((k+1)*st*fs-0.02*fs)
        g=np.median(eo[a:b]/ei[a:b]); rows.append((lv,20*np.log10(np.median(eo[a:b])),20*np.log10(g)))
    rows=np.array(rows); return m,rows

from scipy.optimize import curve_fit
def burst(i):
    m,z=load(i); dec=int(z["dec"]); fs=SR/dec
    ei,eo=z["env_in"].astype(float),z["env_out"].astype(float)
    s=m["sig"]; n0=int(s["pre_s"]*fs); n1=n0+int(round(s["burst_s"]*fs))
    g=20*np.log10(np.maximum(eo,1e-12)/np.maximum(ei,1e-12))
    G0=np.median(g[int(n0-0.4*fs):n0-int(0.01*fs)])
    gr=g-G0
    return m,fs,gr,n0,n1
def first_cross(x, thr, above=True):
    idx=np.where(x>=thr)[0] if above else np.where(x<=thr)[0]
    return idx[0] if len(idx) else None
def rel_metrics(i, fit=2, t_skip=0.003, gr_floor=0.05):
    m,fs,gr,n0,n1=burst(i)
    r=gr[n1:]; t=np.arange(len(r))/fs
    GR0=np.mean(gr[n1-int(0.006*fs):n1-int(0.002*fs)])
    out={"GR0":GR0}
    for nm,thr in [("t_half",GR0/2),("t63",GR0*0.3679),("t_3dB",-3),("t_1dB",-1),("t_0p5dB",-0.5)]:
        k=first_cross(r[int(t_skip*fs):],thr); out[nm]=None if (k is None or thr<GR0) else (k+int(t_skip*fs))/fs
    out["resid_end"]=float(np.mean(r[-int(0.2*fs):]))
    return m,out,t,r
def fit_exp(t,r,n=2,t0=0.003,tmax=None,floor=-0.05,p0=None,domain=None):
    sel=(t>=t0)&(r<floor)
    if tmax: sel&=(t<=tmax)
    tt,rr=t[sel],r[sel]
    if n==1:
        f=lambda t,a,ta: a*np.exp(-t/ta); p0=p0 or [rr[0],0.1]
    elif n==2:
        f=lambda t,a,ta,b,tb: a*np.exp(-t/ta)+b*np.exp(-t/tb); p0=p0 or [rr[0]*0.6,0.05,rr[0]*0.4,1.0]
    else:
        f=lambda t,a,ta,b,tb,c,tc: a*np.exp(-t/ta)+b*np.exp(-t/tb)+c*np.exp(-t/tc); p0=p0 or [rr[0]*0.4,0.05,rr[0]*0.3,1.0,rr[0]*0.3,8.0]
    w=np.ones_like(tt)
    p,_=curve_fit(f,tt,rr,p0=p0,maxfev=40000)
    res=float(np.sqrt(np.mean((f(tt,*p)-rr)**2)))
    return p,res,f
def att_metrics(i):
    m,fs,gr,n0,n1=burst(i)
    a=gr[n0:n1]; GRf=np.mean(a[-int(0.02*fs):]); t=np.arange(len(a))/fs
    o={"GRf":GRf}
    for nm,fr in [("t63",0.632),("t90",0.9),("t10",0.1)]:
        k=first_cross(a,GRf*fr,above=False); o[nm]=None if k is None else k/fs
    return m,o,t,a
