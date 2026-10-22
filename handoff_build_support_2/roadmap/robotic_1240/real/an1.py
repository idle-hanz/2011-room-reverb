import numpy as np, soundfile as sf, json
x,sr=sf.read('play_robotic_tmpvf2xxu9a.wav'); print(x.shape,sr, x.dtype)
m=x.mean(1); s=(x[:,0]-x[:,1])/2
pk=np.max(np.abs(x),0); print('peak',pk,'clip samples',int(np.sum(np.abs(x)>=0.9999)))
print('DC',x.mean(0))
hop=int(0.05*sr); n=len(m)//hop
rms=np.sqrt(np.mean(m[:n*hop].reshape(n,hop)**2,1)); db=20*np.log10(rms+1e-12)
print('rms pctl dB', np.percentile(db,[1,5,10,25,50,75,95,99]).round(1))
print('first 2s levels',db[:40].round(0))
print('last 30 s levels (per 1s)', [round(float(20*np.log10(np.sqrt(np.mean(m[i*sr:(i+1)*sr]**2))+1e-12)),1) for i in range(len(m)//sr-30,len(m)//sr)])
c=np.corrcoef(x[:,0],x[:,1])[0,1]; print('LR corr',c, 'side/mid dB',20*np.log10(np.std(s)/np.std(m)))
