# Attribution: the only Play difference left after removing the column signs is the DC restore (bin_big, Hall preset).
import json, subprocess, os, copy, numpy as np
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'bitexact.py')).read().split('res={}')[0])
WA['nocsign_nodc']=W+'/nocsign_nodc.wasm'
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
hallp=dict(W=57,H=34.241,L=97,sx=24.925,sz=72.083,sy=1.88,my=1.9,mcz=24.25,space=0.25,reaktor_parity=True,car_omni=0.764,early_wet=1.0,fdn_wet=1,direct_wet=1,dry_gain=0,fdn_g=1,decay_lock=False,hadamard_n=32,humidity=0.5,mcx=28.5)
hb=copy.deepcopy(base); hb.update(hallp); SC['hall_preset']=hb
res={}
def rec(name,a,b):
    d=a.astype(float)-b.astype(float); res[name]={'max_abs_diff':float(np.max(np.abs(d))),'peak':float(np.max(np.abs(a))),
      'diff_dB_re_peak':(float(20*np.log10(np.max(np.abs(d))/np.max(np.abs(a)))) if np.max(np.abs(d))>0 else None)}; print(name,res[name],flush=True)
for k in ('bin_big','hall_preset'):
    sec=4.0
    rec(f'nocsign_nodc_vs_1140|{k}|page',play('nocsign_nodc',S16,k,'page',sec),play('ship1140',S11,k,'page',sec))
    rec(f'ship1630_vs_1140|{k}|page',play('ship1630',S16,k,'page',sec),play('ship1140',S11,k,'page',sec))
    if k=='bin_big': rec(f'nocsign_vs_1140|{k}|page',play('nocsign',S16,k,'page',sec),play('ship1140',S11,k,'page',sec))
json.dump(res,open(H+'/bitexact_dc.json','w'),indent=1)
