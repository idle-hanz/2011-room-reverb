# Rough standalone demo: virtual omni mics -> virtual speakers -> binaural. See README.md.
import json, numpy as np, soundfile as sf, scipy.signal as ss, itertools, random
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
FS=48000; C=343.0; rng=np.random.default_rng(1)
B='/workspace/build_support_2/'
H=json.load(open(B+'ui_audit_1004/app/software/mic_colour/presets/binaural/sos_tables/48000/SADIE2_KEMAR.json'))
nodes=np.array(H['nodes']); mir=H['mirror']; SOS=H['sos']['L']
def unit(az,el):
    a,e=np.radians(az),np.radians(el); return np.array([np.cos(e)*np.cos(a),np.cos(e)*np.sin(a),np.sin(e)])
NU=np.array([unit(*n) for n in nodes])
imp=np.zeros(256); imp[0]=1
def sosir(n):
    s=np.array(SOS[n]); s=np.hstack([s[:,:3],np.ones((len(s),1)),s[:,3:]]); return ss.sosfilt(s,imp)
HL=[sosir(n) for n in range(len(nodes))]
def hrir(az,el=0.0):
    """Ear pair for head-relative az (deg, +=left): nearest-node magnitude fit + Woodworth ITD."""
    n=int(np.argmax(NU@unit(az,el))); l=HL[n]; r=HL[mir[n]]
    a=np.radians(az); lat=np.arcsin(np.clip(np.sin(a)*np.cos(np.radians(el)),-1,1))
    itd=(0.09/C)*(lat+np.sin(lat))  # >0 => left ear earlier
    d=int(round(abs(itd)*FS)); pad=np.zeros(d)
    return (np.r_[l,pad],np.r_[pad,r]) if itd>=0 else (np.r_[pad,l],np.r_[r,pad])
# Room: x width 6, y length 8, z height 3. Listener faces +y.
L=np.array([6.,8.,3.]); LIS=np.array([3.,3.,1.2])
# reflection coefficients (broadband, ASSUMED plaster walls ~a=0.06, parquet floor ~a=0.10, plaster ceiling 0.06)
alpha={'x0':.06,'x1':.06,'y0':.06,'y1':.06,'z0':.10,'z1':.06}
beta={k:np.sqrt(1-v) for k,v in alpha.items()}
S_=2*(L[0]*L[1]+L[0]*L[2]+L[1]*L[2]); A=sum(alpha[k]*a for k,a in zip(['x0','y0','z0'],[L[1]*L[2],L[0]*L[2],L[0]*L[1]]))*2
RT=0.161*np.prod(L)/A
SRC=LIS+2.5*np.array([-np.sin(np.radians(30)),np.cos(np.radians(30)),0])  # 30 deg left, 2.5 m
ORDER=5; NIR=int(FS*max(1.2*RT,1.0))
def images():
    out=[]
    for nx,ny,nz in itertools.product(range(-ORDER,ORDER+1),repeat=3):
        if abs(nx)+abs(ny)+abs(nz)>ORDER: continue
        for px,py,pz in itertools.product((0,1),repeat=3):
            p=np.zeros(3); g=1.0
            for i,(n,q,k) in enumerate(zip((nx,ny,nz),(px,py,pz),'xyz')):
                p[i]=2*n*L[i]+(1-2*q)*SRC[i]
                g*=beta[k+'0']**abs(n-q)*beta[k+'1']**abs(n)
            out.append((p,g))
    return out
IM=images()
def az_of(v):  # head-relative az, +left, listener faces +y
    return np.degrees(np.arctan2(-v[0],v[1])),np.degrees(np.arcsin(v[2]/np.linalg.norm(v)))
def add(buf,t,x,g):
    i=int(round(t*FS))
    if i+len(x)<len(buf): buf[i:i+len(x)]+=g*x
TMIX=0.08
def tail(seed,n=1):
    """decorrelated late tail: band-shaped noise, freq-dependent exp decay matched to RT (highs decay faster)."""
    r=np.random.default_rng(seed); t=np.arange(NIR)/FS; out=0
    for lo,hi,rtf in [(40,500,1.15),(500,4000,1.0),(4000,16000,0.65)]:
        nz=ss.sosfilt(ss.butter(2,[lo,hi],'band',fs=FS,output='sos'),r.standard_normal(NIR))
        out=out+nz*np.exp(-6.91*t/(RT*rtf))
    w=np.clip((t-TMIX)/0.04,0,1)  # fade in after mixing time
    return out*w
def tail_level(early_energy_ref):  # scale so tail energy ~ diffuse-field level relative to direct at 1 m
    return np.sqrt(16*np.pi/A)  # rough: diffuse energy / direct@1m = 16pi/A
def omni_ir(p,seed):
    h=np.zeros(NIR+512)
    for q,g in IM:
        d=np.linalg.norm(q-p); t=d/C
        if t<TMIX: add(h,t,np.array([1.0]),g/d)
    tl=tail(seed); tl*=tail_level(0)/np.sqrt(np.sum(tl**2)/FS*1.0)*np.sqrt(RT/13.8)
    h[:NIR]+=tl; return h
def binaural_ir():
    h=np.zeros((2,NIR+512))
    for q,g in IM:
        v=q-LIS; d=np.linalg.norm(v); t=d/C
        if t<TMIX:
            a,e=az_of(v); l,r=hrir(a,e); add(h[0],t,l,g/d); add(h[1],t,r,g/d)
    # diffuse tail: 24 random directions, independent noise each, through HRTFs
    dirs=[(rng.uniform(-180,180),np.degrees(np.arcsin(rng.uniform(-1,1)))) for _ in range(24)]
    ref=None
    for k,(a,e) in enumerate(dirs):
        tl=tail(100+k); tl*=tail_level(0)/np.sqrt(np.sum(tl**2)/FS)*np.sqrt(RT/13.8)/np.sqrt(len(dirs))
        l,r=hrir(a,e); h[0,:NIR]+=np.convolve(tl,l)[:NIR]; h[1,:NIR]+=np.convolve(tl,r)[:NIR]
    return h
SPK_AZ=[0,30,-30,110,-110]  # +left: C, L, R, Ls, Rs
def ring(rad):
    return [LIS+rad*np.array([-np.sin(np.radians(a)),np.cos(np.radians(a)),0]) for a in SPK_AZ]
def via_speakers(mics,seed0):
    h=np.zeros((2,NIR+1024))
    for i,(p,a) in enumerate(zip(mics,SPK_AZ)):
        m=omni_ir(p,seed0+i); l,r=hrir(a,0)
        h[0,:len(m)+len(l)-1]+=np.convolve(m,l); h[1,:len(m)+len(r)-1]+=np.convolve(m,r)
    return h
# C: 2L-cube style ~1 m square-ish: mics at 0.5 m radius in same directions (1 m across)
MB=ring(2.0); MC=ring(0.5)
IRS={'A':binaural_ir(),'B':via_speakers(MB,200),'C':via_speakers(MC,300)}
dry,fs=sf.read(B+'research_shared_fdn/wav/dry_test_48k.wav'); assert fs==FS
dry=dry[:int(12.5*FS)]
names={'A':'demo_A_binaural','B':'demo_B_omni_at_speakers','C':'demo_C_omni_cube'}
def rms(x): return np.sqrt(np.mean(x**2))
outs={}
for k,h in IRS.items():
    h=h/np.max(np.abs(h)); sf.write(f'IR_{k}_{names[k][7:]}.wav',(0.5*h).T,FS,subtype='PCM_24')
    y=np.stack([ss.fftconvolve(dry,h[0]),ss.fftconvolve(dry,h[1])])[:, :len(dry)+int(1.5*FS)]
    outs[k]=y
tgt=0.05
for k in outs: outs[k]*=tgt/rms(outs[k])
pk=max(np.max(np.abs(y)) for y in outs.values())
g=min(1.0,0.89/pk)  # common gain keeps match, peak <= -1 dBFS
rep={'RT60_sabine_s':RT,'image_order':ORDER,'n_images':len(IM),'common_gain':g}
key=list('ABC'); random.Random(7).shuffle(key)
for k,y in outs.items():
    y=y*g; sf.write(names[k]+'.wav',y.T,FS,subtype='PCM_24')
    h=IRS[k]; s=int(0.15*FS); tl=h[:,s:]
    ic=np.corrcoef(tl[0],tl[1])[0,1]
    # band IC 200-1000 Hz
    bp=ss.butter(4,[200,1000],'band',fs=FS,output='sos'); icb=np.corrcoef(ss.sosfilt(bp,tl[0]),ss.sosfilt(bp,tl[1]))[0,1]
    lr=20*np.log10(rms(y[0])/rms(y[1]))
    e=int(0.005*FS)+int(np.argmax(np.abs(h).sum(0))); lr_direct=20*np.log10(rms(h[0,:e+96])/rms(h[1,:e+96]))
    rep[k]={'file':names[k]+'.wav','rms_dbfs':20*np.log10(rms(y)),'peak_dbfs':20*np.log10(np.max(np.abs(y))),
            'tail_IC_broadband(>150ms)':ic,'tail_IC_200-1000Hz':icb,'L_minus_R_dB_whole_clip':lr,'L_minus_R_dB_first_arrival':lr_direct}
for blind,k in zip('XYZ',key):
    sf.write(f'blind_{blind}.wav',sf.read(names[k]+'.wav')[0],FS,subtype='PCM_24')
open('BLIND_KEY_dont_peek.txt','w').write('\n'.join(f'{b} = {k} ({names[k]})' for b,k in zip('XYZ',key))+'\n')
json.dump(rep,open('checks.json','w'),indent=1,default=float)
print(json.dumps(rep,indent=1,default=float))
# figure
f,ax=plt.subplots(figsize=(6,8)); ax.add_patch(plt.Rectangle((0,0),6,8,fill=False,lw=2))
ax.plot(*SRC[:2],'r*',ms=16,label='Source (front-left 30°, 2.5 m)')
ax.plot(*LIS[:2],'ko',ms=10,label='Listener (faces up)')
for i,p in enumerate(MB): ax.plot(*p[:2],'bs',ms=9,label='B omni mics = virtual speakers (2 m ring)' if i==0 else None)
for i,p in enumerate(MC): ax.plot(*p[:2],'g^',ms=9,label='C omni mics (≈1 m cube-style array)' if i==0 else None)
for a,p in zip(SPK_AZ,MB): ax.annotate(f'{a:+d}°',p[:2],textcoords='offset points',xytext=(6,6))
ax.set_xlim(-.3,6.3); ax.set_ylim(-.3,8.3); ax.set_aspect('equal'); ax.set_xlabel('width (m)'); ax.set_ylabel('length (m)')
ax.set_title('Plan view, 6 x 8 x 3 m room\n(virtual speakers at the ITU 5.0 angles, 2 m; anechoic)')
ax.legend(loc='upper right',fontsize=8); f.tight_layout(); f.savefig('plan_view.png',dpi=130)
