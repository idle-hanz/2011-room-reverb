import numpy as np, soundfile as sf
x,sr=sf.read('play_robotic_tmpvf2xxu9a.wav'); m=x.mean(1)
sec=len(m)//sr
lv=[20*np.log10(np.sqrt(np.mean(m[i*sr:(i+1)*sr]**2))+1e-12) for i in range(sec)]
lv=np.array(lv)
# where does level drop below -70
act=np.where(lv>-60)[0]; print('active seconds from',act.min(),'to',act.max(),'of',sec)
print('levels around end', lv[act.max()-5:act.max()+25].round(1))
seg=m[-25*sr:-1*sr]
f=np.fft.rfftfreq(1<<16,1/sr)
w=np.hanning(1<<16); P=np.zeros(len(f))
for k in range(0,len(seg)-(1<<16),1<<15): P+=np.abs(np.fft.rfft(seg[k:k+(1<<16)]*w))**2
P=10*np.log10(P+1e-30); 
idx=np.argsort(P)[::-1][:15]; print('end-seg top bins', [(round(f[i],1),round(P[i]-np.median(P),1)) for i in sorted(idx)])
# band levels
for lo,hi in [(0,20),(20,60),(60,200),(200,1000),(1000,5000),(5000,20000)]:
    sel=(f>=lo)&(f<hi); print(lo,hi, round(10*np.log10(np.sum(10**(P[sel]/10))),1))
