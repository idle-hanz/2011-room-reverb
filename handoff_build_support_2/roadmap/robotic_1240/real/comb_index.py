import numpy as np, soundfile as sf, json, glob, os
from scipy.ndimage import median_filter
def ci(path, f0s=None):
    y,sr=sf.read(path); m=y.mean(1); N=1<<17; w=np.hanning(N); P=0
    for k in range(0,len(m)-N,N//2): P=P+np.abs(np.fft.rfft(m[k:k+N]*w))**2
    f=np.fft.rfftfreq(N,1/sr); Pd=10*np.log10(P+1e-30); fine=Pd-median_filter(Pd,size=301)
    o={}
    best={}
    for f0 in np.arange(101.5,105.5,0.05):
        on=np.zeros(len(f),bool)
        for k in range(2,int(3000/f0)): on|=np.abs(f-k*f0)<0.8
        band=(f>150)&(f<3000)
        v=float(np.mean(fine[on&band])-np.mean(fine[(~on)&band]))
        if not best or v>best['comb_db']: best=dict(f0=round(float(f0),2),comb_db=round(v,2))
    o['best_comb_101.5_105.5Hz']=best
    o['fine_peaks_p99_db']=round(float(np.percentile(fine[(f>150)&(f<3000)],99)),2)
    return o
res={os.path.basename(p):ci(p) for p in sorted(glob.glob('ab_real/*.wav'))}
for k,v in res.items(): print(k,v)
json.dump(res,open('ab_real_comb_index.json','w'),indent=1)
