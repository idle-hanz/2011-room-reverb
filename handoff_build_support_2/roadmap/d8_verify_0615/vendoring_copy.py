import sys, json, os, numpy as np, subprocess
sw='/tmp/vend0615/software'; sys.path[:0]=[sw, sw+'/engine']; os.chdir(sw)
import app_server as A, air_iso
from render_pipeline import render
out={'air_roots':[str(r) for r in air_iso.preset_roots()]}
for mode in ('ortf','binaural'):
  for h in (0.0,0.35,1.0):
    b=dict(A.DEFAULTS); b.update({"humidity":h,"sample_rate":48000,"mic_setup":mode,"ir_length_ms":600})
    try:
        p=A.params_from_body(b)
        lp=A.live_params(p) if hasattr(A,'live_params') else None
        kw={k:v for k,v in p.items() if k in render.__code__.co_varnames}
        dry=np.zeros(4800); dry[0]=1; L,R,info=render(dry,48000,**kw)
        out[f'{mode}_h{h}']={'ok':True,'render_peak':float(np.max(np.abs(L))),'mic_setup':p.get('mic_setup'),'live':type(lp).__name__}
    except Exception as e:
        out[f'{mode}_h{h}']={'ok':False,'err':repr(e)[:300]}
print(json.dumps(out,indent=1))
