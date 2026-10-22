# Final candidate (v3/cand = 1 shared loop, per-mic taps, 0.3 ms mirror-safe jitter seed 1, shared inject + per-mic tap gain) vs today (v3/m0).
import json, subprocess, os, math
import numpy as np
H=os.path.dirname(os.path.abspath(__file__)); PRO=H+'/../proto'
exec(open(H+'/measure.py').read().split('ONLY=')[0])
V.clear(); V.update({'m0':PRO+'/v3/m0.wasm','cand':PRO+'/v3/cand.wasm','fx':PRO+'/v3/fx.wasm'})
S.update({'def_2src':({**base,**vio,'two_sources':True,'source_balance':0.0},3),'big_2src':({**base,**big,**vio,'two_sources':True,'source_balance':0.0},7),
          'bin_def_2src':({**base,'mic_setup':'binaural','two_sources':True,'source_balance':0.0},3)})
SC={'def_violin':(0.08,1.0),'big_violin':(0.25,2.5),'bin_def_omni':(0.08,1.0),'bin_big_omni':(0.25,2.5),'def_2src':(0.08,1.0),'big_2src':(0.25,2.5),'bin_def_2src':(0.08,1.0)}
def irv(v,k,ov,tag):
    out=f'{H}/cm_{v}_{k}_{tag}.f32'
    if not os.path.exists(out):
        r=subprocess.run(['node',LIB+'/wasm_run.js',SW,params(k),json.dumps(ov),'ir',str(S[k][1]),out],capture_output=True,text=True,env=dict(os.environ,WASM=V[v]))
        if r.returncode: raise SystemExit(r.stderr[-400:])
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
def edc_db(x):
    e=np.cumsum(x[::-1]**2)[::-1]; return 10*np.log10(e/e[0]+1e-30)
def iacc(L,R,a,b):
    l=L[a:b]; r=R[a:b]; c=np.correlate(l,r[int(0.001*SR):-int(0.001*SR)],'valid'); return float(np.max(np.abs(c))/np.sqrt(np.sum(l**2)*np.sum(r[int(0.001*SR):-int(0.001*SR)]**2)))
res={}
for k,win in SC.items():
    a,b=int(win[0]*SR),int(win[1]*SR); r={}
    for v in V:
        y=irv(v,k,TAIL,'tail'); yf=irv(v,k,{},'full')
        bands={}
        for fc in OCT:
            L=band(y[:,0],fc); R=band(y[:,1],fc)
            bands[fc]={'t30_L':t30(L),'t30_R':t30(R),'edc_L':edc_db(L)[::480][:int(len(L)/480)],'iacc':round(iacc(L,R,a,b),3)}
        r[v]={'bands':bands,'coh':coh(y[:,0],y[:,1],*win),'coh_full':coh(yf[:,0],yf[:,1],*win),
              'lvl_L':10*math.log10(np.mean(y[a:b,0]**2)+1e-30),'lvl_R':10*math.log10(np.mean(y[a:b,1]**2)+1e-30),
              'third_L':third(y[:,0],a,b),'third_R':third(y[:,1],a,b),'finite':bool(np.all(np.isfinite(yf))),'peak_full':float(np.max(np.abs(yf)))}
    out={}
    for v in ('cand','fx'):
        o={'t30_dev_pct':{},'edc_maxdev_db_to_-30':{},'iacc':{},'coh_dev':{}}
        for fc in OCT:
            m=r['m0']['bands'][fc]; c=r[v]['bands'][fc]
            o['t30_dev_pct'][fc]=[round(100*(c['t30_L']/m['t30_L']-1),1) if c['t30_L'] and m['t30_L'] else None, round(100*(c['t30_R']/m['t30_R']-1),1) if c['t30_R'] and m['t30_R'] else None]
            em=np.array(m['edc_L']); ec=np.array(c['edc_L']); n=min(len(em),len(ec)); sel=em[:n]>-30
            o['edc_maxdev_db_to_-30'][fc]=round(float(np.max(np.abs(ec[:n][sel]-em[:n][sel]))),2)
            o['iacc'][fc]=[m['iacc'],c['iacc']]
            o['coh_dev'][fc]=round(r[v]['coh'][fc]-r['m0']['coh'][fc],3)
        o['coh_m0']=r['m0']['coh']; o['coh_v']=r[v]['coh']; o['coh_full_m0']=r['m0']['coh_full']; o['coh_full_v']=r[v]['coh_full']
        o['dlvl_L_db']=round(r[v]['lvl_L']-r['m0']['lvl_L'],2); o['dlvl_R_db']=round(r[v]['lvl_R']-r['m0']['lvl_R'],2)
        o['spec_dev_L_db']={f:round(r[v]['third_L'][f]-r['m0']['third_L'][f],2) for f in r['m0']['third_L']}
        o['spec_dev_R_db']={f:round(r[v]['third_R'][f]-r['m0']['third_R'][f],2) for f in r['m0']['third_R']}
        o['finite']=r[v]['finite']; o['peak_full']=[round(r['m0']['peak_full'],4),round(r[v]['peak_full'],4)]
        out[v]=o
    res[k]=out; print(k,'cand',json.dumps({x:out['cand'][x] for x in ('t30_dev_pct','coh_dev','dlvl_L_db','dlvl_R_db')}),flush=True)
json.dump(res,open(H+'/cand_metrics.json','w'),indent=1,default=str)
