import json, subprocess, os, sys, glob, math
import numpy as np
H=os.path.dirname(os.path.abspath(__file__)); PRO=H+'/../proto'
exec(open(H+'/measure.py').read().split('ONLY=')[0])
V.clear()
V.update({'m0':PRO+'/shared_m0.wasm','m1':PRO+'/shared_m1.wasm','j150_s0':PRO+'/sweep/j150_s0.wasm','j300_s0':PRO+'/sweep/j300_s0.wasm','j300_s1':PRO+'/sweep/j300_s1.wasm',
          'fx300_s0':PRO+'/sweep/fx300_s0.wasm','fx300_s1':PRO+'/sweep/fx300_s1.wasm','fx300_s2':PRO+'/sweep/fx300_s2.wasm'})
S.update({'small':({**base,'W':6.0,'H':3.0,'L':8.0,'sx':3.4,'sz':5.6,'mcx':2.8,'mcz':2.4,'decay_s':0.8},2),
          'mid_off':({**base,'W':15.0,'H':8.0,'L':22.0,'sx':6.0,'sz':15.0,'mcx':8.5,'mcz':6.0,'decay_s':2.2},4),
          'ortf_wide':({**base,'toe_half_deg':45,'space':0.30},3)})
SC={'def_omni':(0.08,1.0),'big_omni':(0.25,2.5),'bin_def_omni':(0.08,1.0),'small':(0.04,0.5),'mid_off':(0.1,1.2),'ortf_wide':(0.08,1.0),'def_hall_lock40':(0.15,2.0)}
def irv(v,k):
    out=f'{H}/val_{v}_{k}.f32'
    if not os.path.exists(out):
        r=subprocess.run(['node',LIB+'/wasm_run.js',SW,params(k),json.dumps(TAIL),'ir',str(S[k][1]),out],capture_output=True,text=True,env=dict(os.environ,WASM=V[v]))
        if r.returncode: raise SystemExit(r.stderr[-400:])
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
res={}
for k,win in SC.items():
    a,b=int(win[0]*SR),int(win[1]*SR); r={}
    for v in V:
        y=irv(v,k); c=coh(y[:,0],y[:,1],*win)
        r[v]={'coh':c,'t30_L_1k':t30(band(y[:,0],1000)),'t30_R_1k':t30(band(y[:,1],1000)),
              'lvl_L':10*math.log10(np.mean(y[a:b,0]**2)+1e-30),'lvl_R':10*math.log10(np.mean(y[a:b,1]**2)+1e-30),
              'third_L':third(y[:,0],a,b),'third_R':third(y[:,1],a,b)}
    for v in V:
        e=[r[v]['coh'][f]-r['m0']['coh'][f] for f in OCT]
        r[v]['coh_dev']=[round(x,3) for x in e]; r[v]['coh_rms']=round(float(np.sqrt(np.mean(np.square(e)))),3); r[v]['coh_max']=round(float(np.max(np.abs(e))),3)
        r[v]['dlvl_L']=round(r[v]['lvl_L']-r['m0']['lvl_L'],2); r[v]['dlvl_R']=round(r[v]['lvl_R']-r['m0']['lvl_R'],2)
        sd=[(r[v]['third_L'][f]-r['m0']['third_L'][f]) for f in r['m0']['third_L']]; r[v]['spec_dev_L_db']=[round(x,2) for x in sd]
        r[v]['spec_shape_maxdev_db']=round(float(np.max(np.abs(np.array(sd)-np.mean(sd)))),2)
    res[k]=r
    print(k,{v:(r[v]['coh_rms'],r[v]['coh_max'],r[v]['dlvl_L'],r[v]['dlvl_R'],r[v]['t30_L_1k'],r[v]['spec_shape_maxdev_db']) for v in V},flush=True)
# mirror for fixed-decor variants
for v in V:
    A=None
    def mir(bal):
        out=f'{H}/val_{v}_mir{bal}.f32'
        if not os.path.exists(out):
            subprocess.run(['node',LIB+'/wasm_run.js',SW,params(f'mir_omni_{bal}'),json.dumps(TAIL),'ir','3',out],check=True,capture_output=True,env=dict(os.environ,WASM=V[v]))
        return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
    A=mir('-1'); Bm=mir('+1')
    null=20*math.log10(np.max(np.abs(Bm[:48000,0]-A[:48000,1]))/np.max(np.abs(A[:48000]))+1e-30)
    res.setdefault('mirror',{})[v]=round(null,1)
print('mirror',res['mirror'])
json.dump(res,open(H+'/validate_results.json','w'),indent=1,default=str)
