import sys, json, time, numpy as np
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
band=(f>=8000)&(f<=16000)
rows=[]; t0=time.time()
for h in [0.01,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.5,0.6,0.7,0.8,0.9,1.0]:
    rh=air_iso.rh_pct_from_slider(h,'studio_20C_50RH')
    row={'slider':h,'rh_pct':round(rh,1)}
    for d in (10.0,30.0):
        got=pair_db(ef.iso_shelf_pair(d,sr,1.0,'studio_20C_50RH',h))
        iso=air_iso.iso_path_loss_db(f,d,'studio_20C_50RH',rh)
        row[f'{d:g}m_real_8_16k_mean_db']=round(float(got[band].mean()),3)
        row[f'{d:g}m_iso_8_16k_mean_db']=round(float(iso[band].mean()),3)
        row[f'{d:g}m_real_at']={str(k):round(float(np.interp(k,f,got)),2) for k in (2000,4000,8000,16000)}
        row[f'{d:g}m_maxerr_db']=round(float(np.max(np.abs(got-iso))),3)
    rows.append(row)
el=time.time()-t0
def mono(key, sub=None):
    v=[r[key] if sub is None else r[key][sub] for r in rows]; d=np.diff(v)
    return {'non_increasing_loss_steps':int(np.sum(d>1e-6)),'values':v}
res={'rows':rows,'monotonic_30m_8_16k_mean':mono('30m_real_8_16k_mean_db'),'monotonic_30m_iso':mono('30m_iso_8_16k_mean_db'),
     'monotonic_30m_at_4k':mono('30m_real_at','4000'),'monotonic_30m_at_8k':mono('30m_real_at','8000'),'monotonic_30m_at_16k':mono('30m_real_at','16000'),'sweep_secs':round(el,2)}
json.dump(res,open('slider_sweep.json','w'),indent=1)
for r in rows: print(r['slider'],r['rh_pct'],r['30m_real_8_16k_mean_db'],r['30m_iso_8_16k_mean_db'],r['30m_real_at'],r['30m_maxerr_db'],r['10m_maxerr_db'])
for k in ('monotonic_30m_8_16k_mean','monotonic_30m_at_4k','monotonic_30m_at_8k','monotonic_30m_at_16k','monotonic_30m_iso'): print(k,res[k]['non_increasing_loss_steps'])
print('secs',el)
