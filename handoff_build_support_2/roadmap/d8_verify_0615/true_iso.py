import sys, json, numpy as np
sw='/workspace/build_support_2/snapshot_2026-10-02_0615/software'; sys.path[:0]=[sw, sw+'/engine']
import air_iso, early_field as ef
sr=48000; f=np.geomspace(100,16000,400); z=np.exp(-2j*np.pi*f/sr)
def pair_db(pair):
    r=np.zeros_like(f)
    for c in pair:
        if c is None: continue
        b0,b1,b2,a0,a1,a2 = c if len(c)==6 else (c[0],c[1],c[2],1.0,c[3],c[4])
        r+=20*np.log10(np.abs((b0+b1*z+b2*z*z)/(a0+a1*z+a2*z*z)))
    return r
out={}
for h in (0.05,0.35,1.0):
    rh=air_iso.rh_pct_from_slider(h)
    for d in (5.0,10.0,30.0):
        got=pair_db(ef.iso_shelf_pair(d,sr,1.0,'studio_20C_50RH',h))
        true=-air_iso._iso_alpha_db_per_m(f,20.0,rh*100.0,101.325)*d  # h in percent, as ISO 9613-1 note 3
        out[f'h{h}_rh{rh:.0f}_{d:g}m']={'engine_8k':round(float(np.interp(8000,f,got)),2),'trueISO_8k':round(float(np.interp(8000,f,true)),2),'engine_16k':round(float(got[-1]),2),'trueISO_16k':round(float(true[-1]),2),'max_err_db':round(float(np.max(np.abs(got-true))),2)}
tr={rh:round(float(np.mean(-air_iso._iso_alpha_db_per_m(f[(f>=8000)],20.0,rh*100.0,101.325)*30)),2) for rh in (10,15,20,25,30,40,50,60,70,80,90)}
out['trueISO_30m_8_16k_mean_loss_db_by_RH']=tr
json.dump(out,open('true_iso_compare.json','w'),indent=1); print(json.dumps(out,indent=1))
