import numpy as np, soundfile as sf
x,sr=sf.read('play_robotic_tmpvf2xxu9a.wav')
seg=x[-50*sr:-2*sr]
for ch,name in [(seg[:,0],'L'),(seg[:,1],'R'),(seg.mean(1),'M')]:
    n=1<<22; F=np.fft.rfft(ch,n); ac=np.fft.irfft(np.abs(F)**2)[:int(0.5*sr)]; ac/=ac[0]
    lag0=int(0.0005*sr)
    idx=np.argsort(np.abs(ac[lag0:]))[::-1][:12]+lag0
    print(name,'ac top', [(round(i/sr*1000,2),round(float(ac[i]),3)) for i in sorted(idx)])
# spectrum peaks wide list
m=seg.mean(1); N=1<<17; w=np.hanning(N); P=0
for k in range(0,len(m)-N,N//2): P=P+np.abs(np.fft.rfft(m[k:k+N]*w))**2
f=np.fft.rfftfreq(N,1/sr); Pd=10*np.log10(P+1e-30)
from scipy.ndimage import median_filter
base=median_filter(Pd,size=301); ex=Pd-base
from scipy.signal import find_peaks
pk,_=find_peaks(ex,height=10,distance=20)
print('n peaks >10 dB over local median',len(pk))
print([(round(f[i],1),round(ex[i],1)) for i in pk[:80]])
np.save('end_spec.npy',np.vstack([f,Pd]))
