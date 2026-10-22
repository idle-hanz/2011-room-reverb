# IR comb index per channel: fine spectral structure on 103.5 Hz harmonics (150-3000 Hz) vs off-harmonic. Render default FDN-only.
import numpy as np, json
from scipy.ndimage import median_filter
def ci(h,sr):
    out=[]
    for c in range(2):
        x=h[:,c]; N=1<<19; P=np.abs(np.fft.rfft(x,N))**2; f=np.fft.rfftfreq(N,1/sr)
        Pd=10*np.log10(P+1e-30); fine=Pd-median_filter(Pd,size=int(301*N/(1<<17)/(sr/44100)) | 1)
        band=(f>150)&(f<3000); best=-99
        for f0 in np.arange(101.5,105.5,0.05):
            on=np.zeros(len(f),bool)
            for k in range(2,int(3000/f0)): on|=np.abs(f-k*f0)<0.8
            best=max(best,float(np.mean(fine[on&band])-np.mean(fine[(~on)&band])))
        out.append(round(best,2))
    return out
res={}
for sr in (44100,48000):
    for e in ('none','osign','csign'):
        h=np.fromfile(f'w_exp_{e}_{sr}.f32',np.float32).reshape(-1,2).astype(float)
        res[f'render|{sr}|{e}']=ci(h,sr); print(sr,e,res[f'render|{sr}|{e}'])
json.dump(res,open('ir_comb.json','w'),indent=1)
