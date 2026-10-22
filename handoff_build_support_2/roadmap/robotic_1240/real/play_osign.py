import sys, argparse, tempfile, json, numpy as np
T='/workspace/build_support_2/3_phase_acceptance_tests'
sys.path[:0]=[T+'/harness',T+'/harness/lib',T+'/tests']
import run_all as RA
ns=argparse.Namespace(sw='/workspace/build_support_2/snapshot_2026-10-02_1140/software',python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=T+'/harness/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=tempfile.mkdtemp())
c=RA.Ctx(ns); FW='/workspace/build_support_2/roadmap/robotic_1240/fixwasm/'
W={'ship':FW+'ship.wasm','ship_fs':FW+'ship_fs.wasm','fix_fs':FW+'fix_fs.wasm','osign':FW+'osign.wasm'}
body=json.load(open('/workspace/build_support_2/roadmap/s4_verify_1140/measure/client_body_1140.json'))
FDN=dict(direct_wet=0,early_wet=0,fdn_wet=1,dry_gain=0)
sr=48000
def met(h):
    o={}
    acs=[]
    for ch in range(2):
        F=np.fft.rfft(h[:,ch],1<<18); ac=np.fft.irfft(np.abs(F)**2)[:int(0.06*sr)]; ac/=ac[0]
        l0=int(0.002*sr); acs.append(round(float(np.max(np.abs(ac[l0:]))),3))
        o[f'ac_peak_lag_ms_{ch}']=round((int(np.argmax(np.abs(ac[l0:])))+l0)/sr*1000,2)
    o['ac_max']=acs
    m=h.mean(1); sch=np.cumsum((m**2)[::-1])[::-1]; sch=10*np.log10(sch/sch[0]+1e-30)
    i=np.argmax(sch<=-5); j=np.argmax(sch<=-25); o['T20']=round((j-i)/sr*3,3)
    o['rms_db']=round(float(10*np.log10(np.mean(h[int(.05*sr):]**2))),2)
    o['lr_corr']=round(float(np.corrcoef(h[int(.05*sr):,0],h[int(.05*sr):,1])[0,1]),3)
    return o
scenes={'default_fdn_only':dict(body,**FDN),'default_all_on':dict(body,direct_wet=1,early_wet=1,fdn_wet=1),
        'default_fdn_binaural':dict(body,mic_setup='binaural',**FDN),
        'default_fdn_nocolour':dict(body,colour_mode='OFF',**FDN)}
res={}
for sn,b in scenes.items():
    hs={k:c.play_ir(b,{},1.5,wasm=v) for k,v in W.items()}
    res[sn]={k:met(v) for k,v in hs.items()}
    res[sn]['ship_fs_vs_ship_maxdiff']=float(np.max(np.abs(hs['ship_fs']-hs['ship'])))
    res[sn]['fix_fs_vs_ship_maxdiff']=float(np.max(np.abs(hs['fix_fs']-hs['ship'])))
    print(sn,json.dumps(res[sn]),flush=True)
json.dump(res,open('play_osign.json','w'),indent=1)
# mirror / symmetric-scene checks
sym=dict(body,sx=3.0,mcx=3.0,**FDN)
two=dict(body,two_sources=True,mirror_b=True,sx_b=3.4,**FDN)
out={}
for k in ('ship','osign'):
    h=c.play_ir(sym,{},1.0,wasm=W[k]); out[k+'_sym_maxLR']=float(np.max(np.abs(h[:,0]-h[:,1])))
    a=c.play_ir(dict(two,source_balance=-1),{},1.0,wasm=W[k]); b=c.play_ir(dict(two,source_balance=1),{},1.0,wasm=W[k])
    out[k+'_mirror_null_db']=round(float(20*np.log10(np.std(a[:,0]-b[:,1])/np.std(a[:,0]))),1)
    hh=c.play_ir(dict(body,W=57.0,H=34.2,L=97.0,sx=24.0,sz=60.0,mcx=28.5,mcz=30.0,decay_s=8.0,decay_lock=True,**FDN),{},20,wasm=W[k]) if k=='osign' else None
    if hh is not None: out['osign_hall_decay8_18_20s_db']=round(float(10*np.log10(np.mean(hh[18*sr:20*sr]**2)+1e-300)),1)
print(out); res['symmetry']=out; json.dump(res,open('play_osign.json','w'),indent=1)
