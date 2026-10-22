import numpy as np
SR=48000
def metal(x, t0=0.15, t1=1.4, fmin=150, fmax=6000, N=8192):
    """Per-bin decay spread: metallic tails have some bins ringing much longer than the rest."""
    m=x.mean(1) if x.ndim>1 else x
    hop=N//4; w=np.hanning(N); frames=[]; ts=[]
    for s in range(int(t0*SR), int(t1*SR)-N, hop):
        frames.append(np.abs(np.fft.rfft(m[s:s+N]*w))**2); ts.append((s+N/2)/SR)
    S=10*np.log10(np.array(frames)+1e-30); ts=np.array(ts); f=np.fft.rfftfreq(N,1/SR); band=(f>fmin)&(f<fmax)
    A=np.vstack([ts,np.ones_like(ts)]).T
    slope=np.linalg.lstsq(A,S[:,band],rcond=None)[0][0]   # dB/s per bin (negative)
    t60=-60/np.minimum(slope,-1e-3)
    med=np.median(t60)
    # residual roughness around each bin's fit: modal beating
    return dict(t60_med=round(float(med),3), t60_p95_over_med=round(float(np.percentile(t60,95)/med),3), t60_p99_over_med=round(float(np.percentile(t60,99)/med),3),
                slope_std_dBps=round(float(np.std(slope)),2), frac_bins_ring_1p5x=round(float(np.mean(t60>1.5*med)),4))
