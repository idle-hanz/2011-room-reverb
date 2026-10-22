import numpy as np, soundfile as sf, json
x,sr=sf.read('play_robotic_tmpvf2xxu9a.wav')
out={}
for name in ['heard_default_fdn_only','ctl_room7x9','ctl_decay1','exp_osign']:
    h=np.fromfile(f'w_{name}.f32',np.float32).reshape(-1,2).astype(float)
    y=x[370*sr:412*sr]; n=1<<int(np.ceil(np.log2(len(y)+len(h))))
    Y=[np.fft.rfft(y[:,c],n) for c in range(2)]; Hf=[np.fft.rfft(h[:,c],n) for c in range(2)]
    den=np.abs(Hf[0])**2+np.abs(Hf[1])**2; D=(Y[0]*np.conj(Hf[0])+Y[1]*np.conj(Hf[1]))/(den+1e-3*np.median(den))
    d=np.fft.irfft(D,n)[:len(y)]; a=2*sr
    out[name]=[round(float(20*np.log10(np.std(np.fft.irfft(np.fft.rfft(d,n)*Hf[c],n)[:len(y)][a:]-y[a:,c])/np.std(y[a:,c]))),1) for c in range(2)]
    print(name,out[name],flush=True)
json.dump(out,open('deconv_null_controls.json','w'),indent=1)
d=np.load('dry_est_0.001.npy'); print('dry_est peak',np.max(np.abs(d)),'rms dB',20*np.log10(np.std(d)))
