# Fingerprint: do the fine spectral peaks of Idle's render (signal-free end, 412-460 s) line up with
# the Render IR of the candidate scene? Compare against control scenes.
import numpy as np, soundfile as sf, json, sys
from scipy.ndimage import median_filter
from scipy.signal import find_peaks
x,sr=sf.read('play_robotic_tmpvf2xxu9a.wav'); seg=x[412*sr:460*sr]
N=1<<17
def spec(sig):
    w=np.hanning(N); P=0
    for k in range(0,len(sig)-N,N//2): P=P+np.abs(np.fft.rfft(sig[k:k+N]*w))**2
    return 10*np.log10(P+1e-30)
f=np.fft.rfftfreq(N,1/sr); band=(f>80)&(f<4000)
def fine(Pd): return (Pd-median_filter(Pd,size=301))
real=[fine(spec(seg[:,c])) for c in range(2)]
res={}
for name in sys.argv[1:]:
    h=np.fromfile(f'w_{name}.f32',np.float32).reshape(-1,2).astype(float)
    H=[fine(10*np.log10(np.abs(np.fft.rfft(h[:,c],N))**2+1e-30)) for c in range(2)]
    cc=[float(np.corrcoef(real[c][band],H[c][band])[0,1]) for c in range(2)]
    res[name]=[round(v,3) for v in cc]; print(name,'fine-spectrum corr L/R',res[name])
json.dump(res,open('fingerprint.json','w'),indent=1)
