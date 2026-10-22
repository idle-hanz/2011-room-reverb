# Build's Fix2 range: cap so hall median |dffs| in [0.35,0.70]. Measure T30/density/level per cap, ship vs column signs.
import json, numpy as np, hall_b as HB
from bisect_lib import metrics
from dens import ned_curve
res={}
for sc,caps in (('hall_preset_parity',(None,130,90,65)),('bigroom_default_surfaces',(None,18,12))):
    for cap in caps:
        for wn in ('ship','csign'):
            x,p=HB.run(sc,HB.SC[sc],cap,HB.FW+wn+'.wasm')
            m=metrics(x); d=np.abs(np.array(p['buses']['c']['dffs'])); n=ned_curve(x.mean(1))
            r=dict(dffs_med=round(float(np.median(d)),3),T30_s=m['T30_s'],ac_peak=m['ac_peak'],ned_0p2_0p4=round(float(n[15:35].mean()),2),
                   rms_db=round(float(10*np.log10(np.mean(x[int(.05*48000):]**2))),2))
            res[f'{sc}|cap{cap}|{wn}']=r; print(sc,cap,wn,r,flush=True)
json.dump(res,open('cap_build.json','w'),indent=1)
