import json, subprocess, os, copy, numpy as np, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from bisect_lib import metrics
from hall import hall, dif
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+'/w'
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
SWS={'1140':B+'/snapshot_2026-10-02_1140/software','keepdif':'/tmp/rb_keepdif/software'}
def hallbody():
    b=copy.deepcopy(base); b.update(hall); b['mcx']=28.5
    for L,v in dif.items(): b['surfaces'][L].update(diffusion=v,jitter_D=v,structure_dif=v)
    return b
ROOMS={'def':copy.deepcopy(base),'hall':hallbody()}
SM={'none':{},'solo_A':{'surfaces_solo':'A'},'solo_E':{'surfaces_solo':'E'},'mute_A':{'surfaces_mute':['A']},'mute_all':{'surfaces_mute':list('ABCDEF')}}
res={}
for rn,rb in ROOMS.items():
  for sm,ov in SM.items():
    for swn,sw in SWS.items():
      if swn=='keepdif' and sm=='none': continue
      b=dict(copy.deepcopy(rb),**ov); tag=f'{rn}_{sm}_{swn}'; pj=f'{W}/ps_{tag}.json'; f=f'{W}/irs_{tag}.f32'
      subprocess.run([P,LIB+'/dump_params.py',sw,json.dumps(b),pj,'48000'],check=True,capture_output=True)
      r=subprocess.run(['node',LIB+'/wasm_run.js',sw,pj,json.dumps({"direct_wet":0,"early_wet":0}),'ir','4',f],capture_output=True,text=True); assert r.returncode==0,r.stderr
      x=np.fromfile(f,np.float32).reshape(-1,2).astype(float); p=json.load(open(pj))
      d=np.array(p['buses']['c']['dffs']); inj=np.array(p['buses']['c']['inject'])
      m=metrics(x); m.update(dffs_zero_lines=int(np.sum(np.abs(d)<1e-12)), dffs_mean_abs=round(float(np.mean(np.abs(d))),4), inject_zero_lines=int(np.sum(np.abs(inj)<1e-12)), rms_db=round(20*np.log10(np.sqrt(np.mean(x[int(.05*48000):]**2))+1e-30),2))
      res[tag]=m; print(tag,{k:m[k] for k in ('ac_peak','ac_lag_ms','spec_dev_p99','spec_dev_max','T30_s','dffs_zero_lines','dffs_mean_abs','inject_zero_lines','rms_db')},m['ned'],flush=True)
json.dump(res,open(HERE+'/solo_fdn.json','w'),indent=1)
