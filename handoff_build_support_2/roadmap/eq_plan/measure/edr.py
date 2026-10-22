import numpy as np, json, sys, itertools
SR=48000; C=343.0
ROOMS={'def':(6.0,3.0,8.0,1.8),'box':(3.0,2.4,4.0,0.8),'defsyn0':(6.0,3.0,8.0,1.8),'defsyn1':(6.0,3.0,8.0,1.8),'defsyn2':(6.0,3.0,8.0,1.8),'boxsyn0':(3.0,2.4,4.0,0.8),'boxsyn1':(3.0,2.4,4.0,0.8),'boxsyn2':(3.0,2.4,4.0,0.8)}
def load(n):
    x=np.fromfile(n+'.f32',dtype=np.float32).reshape(-1,2).astype(float); return x
def modes(W,H,L,fmax):
    out=[]
    for nx,ny,nz in itertools.product(range(0,40),range(0,40),range(0,40)):
        if nx==ny==nz==0: continue
        f=C/2*np.sqrt((nx/W)**2+(ny/H)**2+(nz/L)**2)
        if f<=fmax:
            k=sum(v>0 for v in (nx,ny,nz)); out.append((f,(nx,ny,nz),['','axial','tangential','oblique'][k]))
    return sorted(out)
def edr(x, nfft=16384, hop=512, start=0.0):
    m=x.mean(1)
    i0=int(start*SR); m=m[i0:]
    win=np.hanning(nfft)
    nfr=(len(m)-nfft)//hop
    S=np.empty((nfr,nfft//2+1))
    for k in range(nfr):
        S[k]=np.abs(np.fft.rfft(m[k*hop:k*hop+nfft]*win))**2
    E=np.cumsum(S[::-1],0)[::-1]           # Schroeder per bin (EDR)
    E=10*np.log10(E/E[0]+1e-30)
    t=np.arange(nfr)*hop/SR
    f=np.fft.rfftfreq(nfft,1/SR)
    return f,t,E,S
def t_fit(t,E,lo=-5,hi=-25):
    T=np.full(E.shape[1],np.nan)
    for b in range(E.shape[1]):
        e=E[:,b]; i1=np.argmax(e<=lo); i2=np.argmax(e<=hi)
        if i2>i1+3: p=np.polyfit(t[i1:i2],e[i1:i2],1); T[b]=-60/p[0] if p[0]<0 else np.nan
    return T
def smooth_ref(f,T,oct=1/3):
    R=np.full_like(T,np.nan)
    for i,fi in enumerate(f):
        if fi<=0: continue
        s=(f>=fi*2**(-oct/2))&(f<=fi*2**(oct/2))&np.isfinite(T)
        if s.sum()>=3: R[i]=np.median(T[s])
    return R
res={}
for name in sys.argv[1:]:
    room=name.split('_')[0]; W,H,L,dec=ROOMS[room]
    V=W*H*L; fs=2000*np.sqrt(dec/V)
    x=load(name)
    f,t,E,S=edr(x)
    band=(f>=20)&(f<=1000)
    T=t_fit(t,E[:, :])
    R=smooth_ref(f,T)
    ratio=T/R
    sel=band&np.isfinite(ratio)
    # local maxima of ratio above 1.15
    flags=[]
    idx=np.where(sel)[0]
    for i in idx:
        if ratio[i]>1.15 and ratio[i]>=ratio[i-1] and ratio[i]>=ratio[i+1]:
            flags.append((float(f[i]),float(T[i]),float(ratio[i])))
    md=modes(W,H,L,1000)
    mf=np.array([m[0] for m in md])
    def nearest(fr): j=np.argmin(abs(mf-fr)); return float(mf[j]), md[j][1], md[j][2], float(abs(mf[j]-fr))
    # early spectral prominence 0-300 ms of the full signal (level above 1/3-oct smoothed)
    m=x.mean(1); seg=m[:int(0.3*SR)]; P=np.abs(np.fft.rfft(seg,n=1<<16))**2; fp=np.fft.rfftfreq(1<<16,1/SR)
    PdB=10*np.log10(P+1e-30); 
    Pref=np.array([np.median(PdB[(fp>=fi*2**-(1/6))&(fp<=fi*2**(1/6))]) if fi>15 else np.nan for fi in fp[:int(1000*(1<<16)/SR)]])
    prom=PdB[:len(Pref)]-Pref
    fpp=fp[:len(Pref)]
    lfm=(fpp>=20)&(fpp<=fs)
    T_lf=T[(f>=40)&(f<=fs)]; R_lf=R[(f>=40)&(f<=fs)]
    T_mid=T[(f>=fs)&(f<=1000)]; R_mid=R[(f>=fs)&(f<=1000)]
    def flat(Tv,Rv):
        r=np.log(Tv/Rv); r=r[np.isfinite(r)]; return float(np.std(r)), float(np.exp(np.max(r))) if len(r) else None
    tol=3.0
    lowflags=[fl for fl in flags if fl[0]<=fs*1.5]
    match=sum(1 for fl in lowflags if nearest(fl[0])[3]<=tol)
    # chance: random frequencies in same range
    rng=np.random.default_rng(0); rnd=rng.uniform(20,fs*1.5,4000)
    chance=float(np.mean([np.min(abs(mf-r))<=tol for r in rnd]))
    out={'room':[W,H,L],'decay':dec,'V':V,'schroeder_hz':round(fs,1),
         'n_modes_below_fs':int(np.sum(mf<=fs)),
         'axial_first':[round(C/(2*d),1) for d in (W,H,L)],
         'T_median_40_1000':float(np.nanmedian(T[(f>=40)&(f<=1000)])),
         'flat_lf_std_logT':flat(T_lf,R_lf)[0],'max_excess_lf':flat(T_lf,R_lf)[1],
         'flat_mid_std_logT':flat(T_mid,R_mid)[0],'max_excess_mid':flat(T_mid,R_mid)[1],
         'n_flags_20_1000':len(flags),'flags_below_1.5fs':[(round(a,1),round(b,2),round(c,2),nearest(a)[:3]) for a,b,c in lowflags][:25],
         'flag_mode_match_within_3Hz':f'{match}/{len(lowflags)}','chance_rate':round(chance,2),
         'T_at_axial_f0':{str(round(C/(2*d),1)):float(np.nanmedian(T[(f>C/(2*d)-3)&(f<C/(2*d)+3)])) for d in (W,H,L)},
         'early_prom_max_db_20_fs':float(np.nanmax(prom[lfm])),
         'early_prom_peaks':[]}
    # early prominence peaks >6 dB below fs, mode match
    pk=[i for i in np.where(lfm)[0][1:-1] if prom[i]>6 and prom[i]>=prom[i-1] and prom[i]>=prom[i+1]]
    out['early_prom_peaks']=[(round(float(fpp[i]),1),round(float(prom[i]),1),nearest(float(fpp[i]))[:3]) for i in pk][:20]
    np.savez(name+'_edr.npz',f=f,T=T,R=R)
    res[name]=out
json.dump(res,open('edr_'+'_'.join(sys.argv[1:])+'.json','w'),indent=1,default=str)
print(json.dumps(res,indent=1,default=str))
