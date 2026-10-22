"""Analyse IR energy/peak per scenario (Render + Play). Energy gain = output RMS / input RMS for white noise.
K-weighted gain uses BS.1770 48 kHz pre-filter + RLB coefficients."""
import numpy as np, json, glob, os
from scipy.signal import lfilter
O='/workspace/build_support_2/research_ui_wishlist/data/levels/'
b1=[1.53512485958697,-2.69169618940638,1.19839281085285]; a1=[1,-1.69065929318241,0.73248077421585]
b2=[1,-2,1]; a2=[1,-1.99004745483398,0.99007225036621]
def kw(x): return lfilter(b2,a2,lfilter(b1,a1,x))
def an(f):
    x=np.fromfile(f,dtype=np.float32).reshape(-1,2).astype(float)
    e=(x**2).sum(0); ek=np.array([(kw(x[:,c])**2).sum() for c in range(2)])
    # stereo energy gain for mono noise in: mean of L,R
    return {'peak_dbfs':round(20*np.log10(np.abs(x).max()+1e-12),2),
            'E_L_db':round(10*np.log10(e[0]+1e-20),2),'E_R_db':round(10*np.log10(e[1]+1e-20),2),
            'E_mean_db':round(10*np.log10(e.mean()+1e-20),2),'K_mean_db':round(10*np.log10(ek.mean()+1e-20),2),
            'LR_corr':round(float(np.corrcoef(x[:,0],x[:,1])[0,1]),3) if e.min()>0 else None}
res={}
for f in sorted(glob.glob(O+'*.f32')):
    k=os.path.basename(f)[:-4]; res[k]=an(f)
for k,v in res.items(): print(k.ljust(22),v)
json.dump(res,open(O+'levels_summary.json','w'),indent=1)
