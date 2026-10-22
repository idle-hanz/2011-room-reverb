"""S4 box measurements: boot/old-save bit-exactness vs 08:30, diffusion split independence,
and Solo/Mute Play vs Render (early-only, FDN-only, direct). Box only; snapshots are read-only."""
import json, subprocess, sys, os, math, copy
import numpy as np
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'
LIB=B+'/3_phase_acceptance_tests/harness/lib'; HERE=os.path.dirname(os.path.abspath(__file__))
NEW=B+'/snapshot_2026-10-02_1140/software'; OLD=B+'/snapshot_2026-10-02_0830/software'
SR=48000; W=HERE+'/w'; os.makedirs(W,exist_ok=True)
body0=json.load(open(HERE+'/client_body_1140.json')); body0.pop('mics',None)
def play(sw, body, key, secs=0.5):
    pj=f'{W}/p_{key}.json'; out=f'{W}/play_{key}.f32'
    r=subprocess.run([P,LIB+'/dump_params.py',sw,json.dumps(body),pj,str(SR)],capture_output=True,text=True)
    if r.returncode: raise SystemExit(r.stderr[-2000:])
    subprocess.run(['node',LIB+'/wasm_run.js',sw,pj,'{}','ir',str(secs),out],check=True,capture_output=True)
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float), json.load(open(pj))
def render(sw, body, key, ms=500):
    out=f'{W}/rend_{key}.f32'
    r=subprocess.run([P,HERE+'/render_ir3.py',sw,json.dumps(body),out,str(ms),str(SR)],capture_output=True,text=True)
    if r.returncode: raise SystemExit(r.stderr[-2000:])
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
def mx(a,b):
    n=min(len(a),len(b)); return float(np.max(np.abs(a[:n]-b[:n])))
def db(e): return round(10*math.log10(e+1e-30),2)
def old_style(body):
    b=copy.deepcopy(body)
    for L,c in (b.get('surfaces') or {}).items():
        c.pop('jitter_D',None); c.pop('structure_dif',None)
    b.pop('surfaces_solo',None); b.pop('surfaces_mute',None)
    b['source_radiation_b']='omni'; b['source_pitch_b']=0
    return b
R={}
# A. boot defaults: new client body on 11:40 vs 08:30-style body on 08:30
for name,(bn,bo) in {'boot':(body0,old_style(body0))}.items():
    pn,_=play(NEW,bn,'bootN',1.5); po,_=play(OLD,bo,'bootO',1.5)
    rn=render(NEW,bn,'bootN',1500); ro=render(OLD,bo,'bootO',1500)
    R['A_boot_vs_0830']={'play_max_abs_diff':mx(pn,po),'render_max_abs_diff':mx(rn,ro)}
print('A',R['A_boot_vs_0830'],flush=True)
# B. old save holding only "diffusion"
ob=old_style(body0); ob['surfaces']['A']['diffusion']=0.4; ob['surfaces']['F']['diffusion']=0.65; ob['surfaces']['D']['diffusion']=0.0
pn,ln=play(NEW,ob,'oldN',1.5); po,lo=play(OLD,ob,'oldO',1.5)
rn=render(NEW,ob,'oldN',1500); ro=render(OLD,ob,'oldO',1500)
R['B_old_save_vs_0830']={'play_max_abs_diff':mx(pn,po),'render_max_abs_diff':mx(rn,ro),
   'vs_boot_render_max_abs_diff':None}
print('B',R['B_old_save_vs_0830'],flush=True)
# C. split independence (11:40)
base=copy.deepcopy(body0); base['fdn_wet']=0
pb,lb=play(NEW,base,'splitbase'); rb=render(NEW,base,'splitbase')
bf=copy.deepcopy(body0); pbf,lbf=play(NEW,bf,'splitbaseF',1.5); rbf=render(NEW,bf,'splitbaseF',1500)
out={}
for key,val in (('jitter_D',0.9),('structure_dif',0.9)):
    b=copy.deepcopy(base)
    for L in 'ABCDEF': b['surfaces'][L][key]=val
    pe,le=play(NEW,b,'split_'+key); re_=render(NEW,b,'split_'+key)
    bF=copy.deepcopy(bf)
    for L in 'ABCDEF': bF['surfaces'][L][key]=val
    pF,lF=play(NEW,bF,'splitF_'+key,1.5); rF=render(NEW,bF,'splitF_'+key,1500)
    dffs_same=all(le['buses'][k]['dffs']==lb['buses'][k]['dffs'] for k in ('l','c','r'))
    delay_same=all(le['buses'][k]['delay_ms']==lb['buses'][k]['delay_ms'] for k in ('l','c','r'))
    out[key]={'play_early_only_max_diff':mx(pe,pb),'render_early_only_max_diff':mx(re_,rb),
              'play_full_max_diff':mx(pF,pbf),'render_full_max_diff':mx(rF,rbf),
              'play_dffs_unchanged':dffs_same,'play_delays_unchanged':delay_same}
R['C_split_all_faces_0.9']=out
print('C',json.dumps(out),flush=True)
# D. Solo / Mute
scen={'none':{},'mute_A':{'surfaces_mute':['A']},'mute_E':{'surfaces_mute':['E']},
      'mute_all':{'surfaces_mute':list('ABCDEF')},'solo_E':{'surfaces_solo':'E'},'solo_A':{'surfaces_solo':'A'}}
paths={'early':dict(fdn_wet=0,direct_wet=1,early_wet=1),'fdn':dict(fdn_wet=1,direct_wet=0,early_wet=0)}
irs={}
for s,ov in scen.items():
    for pth,pv in paths.items():
        b=dict(copy.deepcopy(body0),**pv,**ov)
        secs=0.5 if pth=='early' else 1.5
        pp,lp=play(NEW,b,f'sm_{s}_{pth}',secs); rr=render(NEW,b,f'sm_{s}_{pth}',int(secs*1000))
        irs[s,pth]=(pp,rr,lp)
# direct arrival from 'none' early
pp0,rr0,_=irs['none','early']
n0p=int(np.argmax(np.abs(pp0).sum(1))); n0r=int(np.argmax(np.abs(rr0).sum(1)))
def win_e(x,n0,a_ms,b_ms):
    a=n0+int(a_ms*SR/1000); b=n0+int(b_ms*SR/1000); return float(np.sum(x[max(a,0):b]**2))
D={'direct_peak_sample':{'play':n0p,'render':n0r}}
for s in scen:
    pe,re_,lp=irs[s,'early']; pf,rf,_=irs[s,'fdn']
    pe0,re0,_=irs['none','early']; pf0,rf0,_=irs['none','fdn']
    row={}
    for eng,x,x0,n0 in (('play',pe,pe0,n0p),('render',re_,re0,n0r)):
        row[eng+'_direct_db_vs_none']=round(db(win_e(x,n0,-1,1))-db(win_e(x0,n0,-1,1)),2)
        row[eng+'_early_db_vs_none']=round(db(win_e(x,n0,1.5,80))-db(win_e(x0,n0,1.5,80)),2)
    for eng,x,x0 in (('play',pf,pf0),('render',rf,rf0)):
        row[eng+'_fdn_db_vs_none']=round(db(float(np.sum(x[int(0.05*SR):]**2)))-db(float(np.sum(x0[int(0.05*SR):]**2))),2)
    row['play_solo_mute_gates']=lp.get('solo_mute')
    inj=np.array(lp['buses']['l']['inject']); row['play_inject_lines_zero']=int(np.sum(np.abs(inj)<1e-12))
    D[s]=row
    print('D',s,json.dumps(row),flush=True)
# Play vs Render early level difference (same scene): early energy Render - Play in dB, per scene
for s in scen:
    pe,re_,_=irs[s,'early']
    D[s]['render_minus_play_early_db']=round(db(win_e(re_,n0r,1.5,80))-db(win_e(pe,n0p,1.5,80)),2)
R['D_solo_mute']=D
json.dump(R,open(HERE+'/s4_measure.json','w'),indent=1)
print('saved')
