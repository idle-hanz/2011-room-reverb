import json, subprocess, os, copy, numpy as np, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from metal import metal
from hall import hall, dif
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+'/w'
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
SWS={'1140':B+'/snapshot_2026-10-02_1140/software','0830':B+'/snapshot_2026-10-02_0830/software','keepdif':'/tmp/rb_keepdif/software'}
def hallbody():
    b=copy.deepcopy(base); b.update(hall); b['mcx']=28.5
    for L,v in dif.items(): b['surfaces'][L].update(diffusion=v,jitter_D=v,structure_dif=v)
    return b
viol=dict(source_radiation='violin_byu',source_yaw=173.0,source_pitch=5.0)
CASES=[('def_none','1140',base,{}),('def_none','0830',base,{}),('def_solo_A','1140',base,{'surfaces_solo':'A'}),('def_solo_A','keepdif',base,{'surfaces_solo':'A'}),
 ('def_solo_E','1140',base,{'surfaces_solo':'E'}),('def_mute_all','1140',base,{'surfaces_mute':list('ABCDEF')}),('def_mute_all','keepdif',base,{'surfaces_mute':list('ABCDEF')}),
 ('def_mirror_violin_follow','1140',base,dict(viol,two_sources=True,mirror_b=True)),('def_mirror_violin_Bomni','1140',base,dict(viol,two_sources=True,mirror_b=True,source_radiation_b='omni')),
 ('def_violin_1src','1140',base,viol),
 ('hall_none','1140',hallbody(),{}),('hall_solo_A','1140',hallbody(),{'surfaces_solo':'A'}),('hall_solo_A','keepdif',hallbody(),{'surfaces_solo':'A'})]
res={}
for name,swn,b0,ov in CASES:
    b=dict(copy.deepcopy(b0),**ov); tag=f'{name}_{swn}'; pj=f'{W}/pmt_{tag}.json'; f=f'{W}/irmt_{tag}.f32'
    subprocess.run([P,LIB+'/dump_params.py',SWS[swn],json.dumps(b),pj,'48000'],check=True,capture_output=True)
    r=subprocess.run(['node',LIB+'/wasm_run.js',SWS[swn],pj,json.dumps({"direct_wet":0,"early_wet":0}),'ir','3',f],capture_output=True,text=True); assert r.returncode==0,r.stderr
    x=np.fromfile(f,np.float32).reshape(-1,2).astype(float); p=json.load(open(pj))
    m=metal(x); mL=metal(x[:,0]); d=np.array(p['buses']['c']['dffs'])
    m['L_only']=mL; m['dffs_zero']=int(np.sum(np.abs(d)<1e-12)); m['lr_corr']=round(float(np.corrcoef(x[7200:,0],x[7200:,1])[0,1]),3)
    res[tag]=m; print(tag,json.dumps(m),flush=True)
json.dump(res,open(HERE+'/metal.json','w'),indent=1)
