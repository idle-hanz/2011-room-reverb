import sys, os, json, asyncio, numpy as np
SW='/workspace/build_support_2/snapshot_2026-10-03_1600/software'; sys.path[:0]=[SW,SW+'/engine']; os.chdir(SW)
import app_server as A
def run(**kw):
    b=dict(A.DEFAULTS); b.update(kw); b['n_az']=72; return asyncio.run(A.api_polar(b))
res={}
d=run(colour_mode='MEASURED_SHELF',mic_preset_l='ShureSM57',mic_preset_c='ShureSM57',mic_preset_r='AKGC414Omni')
L,R=np.array(d['L']),np.array(d['R']); res['split_L_SM57_R_414omni']={'presets':{k:v['id'] for k,v in d['presets'].items()},'L_back':L[:,36].round(3).tolist(),'R_back':R[:,36].round(3).tolist(),'max|L-R|':round(float(np.abs(L-R).max()),3)}
d2=run(colour_mode='MEASURED_SHELF',yaw_l_deg=-20.0); res['yaw_change_L_grid_equal']=bool(np.allclose(np.array(d2['L']),L))
d3=run(colour_mode='MEASURED_SHELF'); res['sm57_ring_front_vs_90deg_db']=[round(float(20*np.log10(max(x,1e-9))),2) for x in np.array(d3['C'])[:,18]]
res['ring_hz']=d3.get('centres_hz')
print(json.dumps(res,indent=1)); json.dump(res,open('polar_probe2.json','w'),indent=1)
