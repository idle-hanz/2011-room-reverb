# SPICE: Fairchild 670 sidechain time-constant network (Raffensperger DAFx-12 Fig.8 / Table 3),
# driven through a diode bridge leg + 100 ohm source (assumed; gives the manual's ~0.2 ms attack with CT=2uF),
# then sidechain volts -> gain reduction via the 6386 model (tube6386.py).
import numpy as np, json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from spicerun import run, ROOT
from tube6386 import gr_db
from scipy.optimize import brentq, curve_fit
POS={1:(2e-6,51.9e3,None,None),2:(2e-6,149.9e3,None,None),3:(4e-6,220e3,None,None),4:(8e-6,220e3,None,None),
     5:(4e-6,220e3,100e3,None),6:(2e-6,220e3,100e3,100e3)}
V10=brentq(lambda v: gr_db(v)-10.0,0.1,30)   # sidechain volts for 10 dB GR
res={}
fig,axs=plt.subplots(2,3,figsize=(15,8))
for k,(CT,RT,RU,RV) in POS.items():
    res[k]={}
    for dur in [0.01,0.3,1.0,3.0,10.0,30.0]:
        Tend=dur+min(60.0,40*RT*CT+ (40 if RU else 0))
        Vd=V10*(RT+100)/RT+0.65
        body=f"""Vd drv 0 PWL(0 0 1u {Vd} {dur} {Vd} {dur+1e-6} 0)
D1 drv a DSIG
Rsrc a sc 100
CT sc 0 {CT}
RT sc 0 {RT}
"""
        if RU: body+=f"RU sc u {RU}\nCU u 0 8u\n"
        if RV: body+=f"RV sc v {RV}\nCV v 0 20u\n"
        step=max(dur,Tend)/20000
        d=run(f'fairchild_pos{k}_burst{dur}',body,['v(sc)'],tran=f'{step} {Tend} 0 {step}')
        t=d['time']; v=d['vsc']; g=gr_db(np.clip(v,0,None))
        i0=np.searchsorted(t,dur); gpk=g[i0-1]
        tr=t[i0:]-dur; gr=g[i0:]
        def tcross(x):
            j=np.where(gr<=x)[0]; return float(tr[j[0]]) if len(j) else None
        res[k][dur]=dict(gr_at_end_db=round(float(gpk),2), t_to_50pct=tcross(gpk*0.5), t_to_37pct=tcross(gpk*0.368), t_to_1dB=tcross(1.0), t_to_0p5dB=tcross(0.5))
        ax=axs.flat[k-1]; ax.plot(tr,gr,label=f'{dur}s burst'); 
    ax.set_title(f'Fairchild pos {k}: release after bursts'); ax.set_xlabel('s after burst'); ax.set_ylabel('GR dB'); ax.set_xscale('symlog',linthresh=0.1); ax.legend(fontsize=7)
plt.tight_layout(); plt.savefig(f'{ROOT}/plots/fairchild_release.png',dpi=110)
json.dump(dict(V_for_10dB=V10,results=res),open(f'{ROOT}/raw/fairchild_summary.json','w'),indent=1)
for k in res:
    for dur in res[k]: print(k,dur,res[k][dur])
