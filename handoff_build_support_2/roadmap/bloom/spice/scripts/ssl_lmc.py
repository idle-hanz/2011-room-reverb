# SPICE: SSL 4000E Listen Mic Compressor (82E33 / CF82B33 drawing, gyraf.dk), read from the schematic:
# 2N5486 JFET shunt (T7), series ~22k (R25/R26, read), gate linearisation 1M/1M (R19,R21) and R20 1M from timing cap,
# timing: precision full-wave rectifier (TDA T5 + 741 T6, 4k7 network) -> R23 1k -> C14 15uF (read "15/25v"), NO isolating diode
# => mean-absolute (average) detector with symmetric ~15 ms charge/discharge. Loop gain/threshold ASSUMED (gives ~10-25 dB GR).
import numpy as np, json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from spicerun import run, ROOT
VTO=-4.0
def net(amp,t_on,t_end,K=40.0,f=1000):
    return f"""Vin in 0 SIN(0 {amp} {f})
Vgate gt 0 PWL(0 1 {t_on} 1 {t_on+1e-5} 0)
Bin in2 0 V=v(in)*v(gt)
Rs in2 fet 22k
J1 fet g 0 2N5486
Bg g 0 V=min({VTO-0.05}+v(c)*0.5,-0.05)
* (drain-to-gate linearisation R19/R21 omitted: affects distortion, not timing)
Brec r 0 V=max(abs(v(fet))*{K}-0.6,-0.6)
R23 r c 1k
C14 c 0 15u
.options method=gear reltol=1e-3
"""
res={}; fig,ax=plt.subplots(figsize=(8,4.5))
for amp in [0.05,0.2,0.8]:
    T=0.45
    d=run(f'lmc_burst_{amp}',net(amp,0.2,T),['v(fet)','v(c)'],tran=f'5e-6 {T} 0 5e-6')
    t=d['time']; v=np.abs(d['vfet']-np.median(d['vfet'][(d['time']>0.39)])); n=int(1e-3/5e-6)
    env=np.array([v[max(0,i-n):i+1].max() for i in range(0,len(v),20)]); te=t[::20]
    base=amp*np.exp(-0) ; # reference: no-GR divider output ~ amp*Rds_off/(22k+Rds_off) ~ amp
    gr=20*np.log10(np.maximum(amp,1e-12)/np.maximum(env,1e-12)); gr[te<1.5e-3]=0
    i0=np.searchsorted(te,0.2); g0=np.median(gr[i0-200:i0-1])
    ja=np.where(gr[:i0]>=0.632*g0)[0]; c=d['vc']; tc=t
    ic=np.searchsorted(tc,0.2); c0=c[ic-1]; jr=np.where(c[ic:]<=(c0-(-0.6))*0.368-0.6)[0]
    res[amp]=dict(gr_end_db=round(float(g0),2),attack63_ms=float(te[ja[0]]*1e3) if len(ja) else None,cap_release_tau_ms=float((tc[ic+jr[0]]-0.2)*1e3) if len(jr) else None)
    print(amp,res[amp]); sys.stdout.flush(); ax.plot(te*1e3,gr,label=f'amp {amp}')
ax.set_xlabel('ms'); ax.set_ylabel('GR dB (1 ms peak env)'); ax.legend(); ax.set_title('SSL Listen Mic comp (schematic-read RC, assumed gain)')
plt.tight_layout(); plt.savefig(f'{ROOT}/plots/ssl_lmc.png',dpi=110)
json.dump(res,open(f'{ROOT}/raw/lmc_summary.json','w'),indent=1)
