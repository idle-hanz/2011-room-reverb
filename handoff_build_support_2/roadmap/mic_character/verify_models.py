import numpy as np
SR=96000
def harmonics(y,f0,n=5):
    N=len(y); w=np.hanning(N); Y=np.abs(np.fft.rfft(y*w)); fr=np.fft.rfftfreq(N,1/SR)
    h=[Y[np.argmin(abs(fr-k*f0))] for k in range(1,n+1)]
    return [20*np.log10(x/h[0]+1e-15) for x in h]
t=np.arange(SR*2)/SR
print("== asymmetric tanh: y=(tanh(a(x+b))-tanh(ab))/(a sech^2(ab)) ==")
for a,b,A in [(1,0,0.1),(1,0.2,0.1),(2,0.2,0.1),(1,0.2,0.3),(3,0.1,0.2)]:
    x=A*np.sin(2*np.pi*1000*t)
    y=(np.tanh(a*(x+b))-np.tanh(a*b))
    h=harmonics(y,1000)
    tt=np.tanh(a*b)
    hd2=20*np.log10(a*tt*A/2+1e-15); hd3=20*np.log10(a*a*abs(1-3*tt*tt)*A*A/12)
    print(f"a={a} b={b} A={A}: sim H2 {h[1]:.1f} dB (pred {hd2:.1f}), H3 {h[2]:.1f} (pred {hd3:.1f})")
print("== flux-domain transformer: phi=leaky integral of x; y = x + k*d/dt(sat(phi)-phi) ==")
def xfmr(x,fsat_phi=1.0,fl=2.0):
    # one-pole leaky integrator corner fl Hz, normalised so phi=x/(j w) scaled by w_ref=2pi*20Hz
    wref=2*np.pi*20; c=np.exp(-2*np.pi*fl/SR)
    phi=np.zeros_like(x); p=0.0
    for i,v in enumerate(x):
        p=c*p+v*wref/SR; phi[i]=p
    s=np.tanh(phi/fsat_phi)*fsat_phi
    r=s-phi
    dr=np.diff(r,prepend=r[0])*SR/wref
    return x+dr
for f0 in [20,40,80,160]:
    for A in [0.1,0.2]:
        tt=np.arange(int(SR*1.5))/SR; x=A*np.sin(2*np.pi*f0*tt)
        y=xfmr(x)[SR//2:]
        h=harmonics(y,f0)
        print(f"f={f0} Hz A={A}: H2 {h[1]:.1f} dB  H3 {h[2]:.1f} dB  H5 {h[4]:.1f} dB")
