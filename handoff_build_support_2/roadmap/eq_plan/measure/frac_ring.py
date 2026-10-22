import json, numpy as np
from scipy.signal import stft
out={}
# (1) fractional delays: Render int at 48k; Play d = ms*sr/1000
d=json.load(open('p_def.json'))
for sr in (48000,44100):
    res={}
    for b,v in d['buses'].items():
        s=np.array(v['delay_ms'])*1e-3*sr; fr=s-np.floor(s)
        w=2*np.pi*10000/sr
        H=np.abs((1-fr)+fr*np.exp(-1j*w)); db=20*np.log10(H)   # dB per pass at 10 kHz
        dsec=s/sr
        # loss per second per line and loop-gain T60 at 10k vs dial 1.8 (interp only)
        Tl=60/(60/1.8 - db/dsec)          # per-line T60 if that line alone set decay
        Tavg=60/(60/1.8 - np.mean(db/dsec))
        res[b]=dict(maxfrac=float(np.max(np.minimum(fr,1-fr))),db_min=float(db.min()),db_max=float(db.max()),
                    T10k_mean_s=float(Tavg),T10k_line_min=float(Tl.min()),T10k_line_max=float(Tl.max()))
    out['frac_%d'%sr]=res
# (2) default-room engine ringing (Render FDN only, today's engine)
fs=48000
for name in ('def_fdn','def_fdn_d0','defsyn0'):
    x=np.fromfile(name+'.f32',np.float32).reshape(-1,2).astype(float).mean(1)
    seg=x[int(0.3*fs):int(1.3*fs)]
    t=np.arange(len(seg))/fs; seg=seg*10**(3*t/1.8)   # undo dial decay
    X=np.abs(np.fft.rfft(seg*np.hanning(len(seg)))); f=np.fft.rfftfreq(len(seg),1/fs)
    m=(f>100)&(f<8000); L=20*np.log10(X[m]+1e-20)
    # peakiness: std of fine-bin dB after removing 1/3-oct trend
    from scipy.ndimage import median_filter
    tr=median_filter(L,size=301); r=L-tr
    out[name]=dict(peakiness_std_db=float(np.std(r)),rayleigh_ref=5.57,top=sorted([(float(v),float(fq)) for v,fq in zip(r,f[m])],reverse=True)[:5])
json.dump(out,open('frac_ring.json','w'),indent=1)
print(json.dumps(out,indent=1))
