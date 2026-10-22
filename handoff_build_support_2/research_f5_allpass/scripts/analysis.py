"""Task 1+2 (analytic + numeric proofs). Per-line transfer of the in-loop Schroeder allpass in Play (z^-1 between
Hadamard and allpass), Render (same-sample solve), Idle's restructure (u = s[n-1]) and a 'split-node' strawman;
closed-loop spectral radius for the 32-line H*D loop with small delays (exact state matrix)."""
import numpy as np, json, os
OUT=os.path.join(os.path.dirname(__file__),'..','data','analysis.json')
D_SIGN=np.array([1,-1,-1,-1,-1,-1,1,-1,-1,1,-1,1,1,1,1,1,-1,1,1,1,-1,1,1,1,-1,1,1,1,-1,1,1,1],float)
def hada(n):
    H=np.array([[1.0]])
    while H.shape[0]<n: H=np.block([[H,H],[H,-H]])
    return H
res={}
# ---- 1. per-line transfers on a fine grid (D = 400 samples, 8.3 ms at 48 k)
D=400; w=np.linspace(0,np.pi,200001); z1=np.exp(-1j*w)
def A(d,lg=1.0,D=D): zd=lg*z1**D; return (zd-d)/(1-d*zd)
per={}
for d in (-0.98,-0.5,0.044,0.5,0.98):
    for lg in (1.0,0.968):
        Tp=z1*A(d,lg); Tr=A(d,lg); Tsplit=(lg*z1**D-d*z1)/(1-d*lg*z1**D)
        k=f'd={d:+.3f}|lg={lg}'
        per[k]=dict(play_maxdev_db=float(np.max(np.abs(20*np.log10(np.abs(Tp))))) if lg==1 else None,
                    render_maxdev_db=float(np.max(np.abs(20*np.log10(np.abs(Tr))))) if lg==1 else None,
                    play_minus_render_mag_db=float(np.max(np.abs(20*np.log10(np.abs(Tp)/np.abs(Tr))))),
                    lossy_ripple_db=[round(float(20*np.log10(np.min(np.abs(Tr)))),3),round(float(20*np.log10(np.max(np.abs(Tr)))),3)],
                    delay_only_loss_db=round(float(20*np.log10(lg)),3),
                    split_node_range_db=[round(float(20*np.log10(np.min(np.abs(Tsplit)))),2),round(float(20*np.log10(np.max(np.abs(Tsplit)))),2)])
res['per_line']=per
# ---- 2. closed-loop state matrices (exact), small random delays
rng=np.random.default_rng(1)
def step_fn(delays,dffs,g,lg,struct):
    n=len(delays); H=hada(n)*(D_SIGN[None,:n] if n==32 else 1)
    offs=np.concatenate([[0],np.cumsum(delays)[:-1]]).astype(int); S=int(sum(delays))
    dim=S+n  # delay buffers (shift registers, newest first) + one register per line (fb or u)
    M=np.linalg.inv(np.eye(n)+g*np.diag(dffs)@H)
    def f(x,xin=None):
        xin=np.zeros(n) if xin is None else xin
        buf=[x[offs[i]:offs[i]+delays[i]] for i in range(n)]; reg=x[S:]
        r=np.array([lg[i]*buf[i][-1] for i in range(n)])  # read D samples ago
        if struct=='render':
            y=M@(r-dffs*xin); s=xin+g*H@y; newreg=0*reg
        elif struct=='play':      # s = xin + fb, fb = g H y[n-1]
            s=xin+reg; y=-dffs*s+r; newreg=g*H@y
        elif struct=='apd':       # Idle: u = s[n-1], s = xin + g H y
            s=reg; y=-dffs*s+r; newreg=xin+g*H@y
        w=s+dffs*y
        nb=np.concatenate([np.concatenate([[w[i]],buf[i][:-1]]) for i in range(n)])
        return np.concatenate([nb,newreg]),y
    F=np.zeros((dim,dim))
    for k in range(dim):
        e=np.zeros(dim); e[k]=1; F[:,k]=f(e)[0]
    return F,f,dim
stab={}
for name,dgen in (('all +0.98',lambda n:np.full(n,0.98)),('all -0.98',lambda n:np.full(n,-0.98)),
                  ('mixed U(-0.98,0.98)',lambda n:rng.uniform(-0.98,0.98,n)),('hall-like |d|<=0.14',lambda n:rng.uniform(-0.14,0.14,n)),
                  ('zero',lambda n:np.zeros(n))):
    n=32; delays=rng.integers(3,17,n); dffs=dgen(n)
    for gname,g,lgv in (('lossless g=1/sqrt32, lg=1',1/np.sqrt(32),1.0),('decay-lock g=0.158, lg=0.97',0.158,0.97)):
        row={}
        for st in ('play','apd','render'):
            F,_,dim=step_fn(delays,dffs,g,np.full(n,lgv),st); ev=np.abs(np.linalg.eigvals(F))
            evn=ev[ev>1e-9]
            row[st]=dict(rho=round(float(ev.max()),9),min_nonzero=round(float(evn.min()),6),dim=dim)
        stab[f'{name} | {gname}']=row; print(name,gname,row,flush=True)
res['closed_loop_spectral_radius']=stab
# ---- 3. APD == Play delayed by one sample (impulse into xin)
n=32; delays=rng.integers(3,17,n); dffs=rng.uniform(-0.98,0.98,n); lg=np.full(n,0.97)
outs={}
for st in ('play','apd'):
    _,f,dim=step_fn(delays,dffs,0.158,lg,st); x=np.zeros(dim); ys=[]
    for t in range(400):
        xin=rng.standard_normal(n)*0 + (np.ones(n) if t==0 else 0)
        x,y=f(x,xin); ys.append(y)
    outs[st]=np.array(ys)
res['apd_equals_play_shifted_1']=float(np.max(np.abs(outs['apd'][1:]-outs['play'][:-1])))
print('apd vs play shifted', res['apd_equals_play_shifted_1'])
json.dump(res,open(OUT,'w'),indent=1)
for k,v in per.items(): print(k,v)
