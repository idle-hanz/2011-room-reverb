import numpy as np, soundfile as sf, json
x,sr=sf.read('play_robotic_tmpvf2xxu9a.wav')
h=np.fromfile('w_heard_default_fdn_only.f32',np.float32).reshape(-1,2).astype(float)
t0,t1=372,412
y=x[(t0-2)*sr:t1*sr]
n=1<<int(np.ceil(np.log2(len(y)+len(h))))
Y=[np.fft.rfft(y[:,c],n) for c in range(2)]; Hf=[np.fft.rfft(h[:,c],n) for c in range(2)]
den=np.abs(Hf[0])**2+np.abs(Hf[1])**2
res={}
for lam in (1e-1,1e-2,1e-3):
    reg=lam*np.median(den)
    D=(Y[0]*np.conj(Hf[0])+Y[1]*np.conj(Hf[1]))/(den+reg)
    d=np.fft.irfft(D,n)[:len(y)]
    # re-convolve and null against the real render (skip first 2 s pre-roll)
    yr=[np.fft.irfft(np.fft.rfft(d,n)*Hf[c],n)[:len(y)] for c in range(2)]
    a=2*sr
    null=[20*np.log10(np.std(yr[c][a:]-y[a:,c])/np.std(y[a:,c])) for c in range(2)]
    res[lam]=[round(v,1) for v in null]; print('lam',lam,'null dB',res[lam],flush=True)
    np.save(f'dry_est_{lam}.npy',d.astype(np.float32))
json.dump({str(k):v for k,v in res.items()},open('deconv_null.json','w'))
