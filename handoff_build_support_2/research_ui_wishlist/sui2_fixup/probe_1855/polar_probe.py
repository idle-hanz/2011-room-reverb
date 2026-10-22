"""Read-only probe (1600 software = PC app_server.py/polar_field.py byte-identical): what /api/polar returns per mode/preset."""
import sys, os, json, asyncio, numpy as np
SW='/workspace/build_support_2/snapshot_2026-10-03_1600/software'; sys.path[:0]=[SW,SW+'/engine']; os.chdir(SW)
import app_server as A
from mic_colour.preset_store import get_store
st=get_store(); ids=sorted(st.ids() if hasattr(st,'ids') else getattr(st,'_presets',{}).keys())
print('presets',len(ids),ids[:40])
def run(**kw):
    b=dict(A.DEFAULTS); b.update(kw); b['n_az']=72
    return asyncio.run(A.api_polar(b))
out={}
def summ(tag,d):
    r={}
    for k in ('L','C','R'):
        g=np.array(d[k]); r[k]={'bands':g.shape[0],'ring_spread_max':round(float((g.max(0)-g.min(0)).max()),4),
            'front_spread':round(float(g[:,0].max()-g[:,0].min()),4),'back_min':round(float(g[:,36].min()),4),'back_max':round(float(g[:,36].max()),4)}
    out[tag]={'presets':{k:v.get('id') if isinstance(v,dict) else v for k,v in (d.get('presets') or {}).items()},'grids':r,
              'grid_hash':{k:hex(abs(hash(np.round(np.array(d[k]),5).tobytes())))[:10] for k in ('L','C','R')}}
    print(tag,json.dumps(out[tag]))
for mode in ('MEASURED_SHELF','BYPASS','ASSUMED_TOYS'):
    summ(f'ortf_sm57_{mode}', run(colour_mode=mode))
for pid in ids[:12]:
    summ(f'ortf_{pid}_MEASURED', run(colour_mode='MEASURED_SHELF',mic_preset_l=pid,mic_preset_c=pid,mic_preset_r=pid))
json.dump(out,open('polar_probe.json','w'),indent=1)
