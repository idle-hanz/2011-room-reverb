import sys, argparse, tempfile, json, numpy as np, os, subprocess
T='/workspace/build_support_2/3_phase_acceptance_tests'
sys.path[:0]=[T+'/harness',T+'/harness/lib',T+'/tests']
import run_all as RA, test_s4b_tail_solo_runaway as TT
ns=argparse.Namespace(sw='/workspace/build_support_2/snapshot_2026-10-02_1140/software',python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=T+'/harness/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=tempfile.mkdtemp())
c=RA.Ctx(ns); FW='/workspace/build_support_2/roadmap/robotic_1240/fixwasm/'
W={k:FW+k+'.wasm' for k in ('ship','osign','csign')}
body=json.load(open('/workspace/build_support_2/roadmap/s4_verify_1140/measure/client_body_1140.json'))
FDN=dict(direct_wet=0,early_wet=0,fdn_wet=1,dry_gain=0); sr=48000
def oct(h):
    m=h.mean(1); F=np.abs(np.fft.rfft(m,1<<18))**2; fr=np.fft.rfftfreq(1<<18,1/sr)
    return np.array([10*np.log10(F[(fr>=fc/1.414)&(fr<fc*1.414)].sum()+1e-30) for fc in (63,125,250,500,1000,2000,4000,8000)])
def met(h):
    m=h.mean(1); sch=np.cumsum((m**2)[::-1])[::-1]; sch=10*np.log10(sch/sch[0]+1e-30)
    i=np.argmax(sch<=-5); j=np.argmax(sch<=-25)
    return dict(ac19=[round(v,3) for v in TT._acmax(h,sr,at_ms=19.36)],acmax=[round(v,3) for v in TT._acmax(h,sr)],T20=round((j-i)/sr*3,3),rms_db=round(float(10*np.log10(np.mean(h**2))),2),lr=round(float(np.corrcoef(h[:,0],h[:,1])[0,1]),3))
SC={'default_fdn':dict(body,**FDN),'bigroom_fdn':dict(body,W=57.0,H=34.241,L=97.0,sx=24.925,sz=72.083,mcx=28.5,mcz=24.25,**FDN),
    'binaural_default_fdn':dict(body,mic_setup='binaural',**FDN),'default_all_on':dict(body,direct_wet=1,early_wet=1,fdn_wet=1)}
res={}
for sn,b in SC.items():
    hs={k:c.play_ir(b,{},3.0 if 'big' in sn else 1.5,wasm=v) for k,v in W.items()}
    o0=oct(hs['ship'])
    for k,h in hs.items():
        r=met(h); r['octave_vs_ship_db_63..8k']=[round(float(v),1) for v in oct(h)-o0]; res[f'{sn}|{k}']=r; print(sn,k,r,flush=True)
X=c.play_ir(dict(body,sx=3.0,mcx=3.0,**FDN),{},1.0,wasm=W['csign']); res['csign_sym_maxLR']=float(np.max(np.abs(X[:,0]-X[:,1])))
two=dict(body,two_sources=True,mirror_b=True,sx_b=3.4,**FDN)
a=c.play_ir(dict(two,source_balance=-1),{},1.0,wasm=W['csign']); bb=c.play_ir(dict(two,source_balance=1),{},1.0,wasm=W['csign'])
res['csign_mirror_maxdiff']=float(np.max(np.abs(a[:,0]-bb[:,1])))
print('sym',res['csign_sym_maxLR'],'mirror',res['csign_mirror_maxdiff'])
json.dump(res,open('play_csign.json','w'),indent=1)
