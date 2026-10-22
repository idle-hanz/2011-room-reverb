"""S4b box measurements on the 16:30 snapshot (read-only): Solo/Mute early-only (D16/D15/D11), FDN untouched,
Render parity bit-exact vs 11:40, Render default tail level vs 11:40, comb index on Idle's scene (48k/44.1k), 44.1k 20 s runaway."""
import json, subprocess, sys, os, math, copy
import numpy as np
B='/workspace/build_support_2'; P='/workspace/scratch_er_dropout/venv/bin/python'; LIB=B+'/3_phase_acceptance_tests/harness/lib'
HERE=os.path.dirname(os.path.abspath(__file__)); S16=B+'/snapshot_2026-10-02_1630/software'; S11=B+'/snapshot_2026-10-02_1140/software'
W='/tmp/s4bm'; os.makedirs(W,exist_ok=True)
body0=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); body0.pop('mics',None)
sys.path.insert(0,B+'/3_phase_acceptance_tests/tests'); 
def play(sw,body,key,secs=0.5,sr=48000,over='{}'):
    pj=f'{W}/p_{key}.json'; out=f'{W}/play_{key}.f32'
    subprocess.run([P,LIB+'/dump_params.py',sw,json.dumps(body),pj,str(sr)],check=True,capture_output=True)
    subprocess.run(['node',LIB+'/wasm_run.js',sw,pj,over,'ir',str(secs),out],check=True,capture_output=True)
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float), json.load(open(pj))
def render(sw,body,key,ms=500,sr=48000):
    out=f'{W}/rend_{key}.f32'
    r=subprocess.run([P,LIB+'/render_ir.py',sw,json.dumps(body),out,str(ms),str(sr)],capture_output=True,text=True)
    if r.returncode: raise SystemExit(r.stderr[-2000:])
    return np.fromfile(out,np.float32).reshape(-1,2).astype(float)
def mx(a,b): n=min(len(a),len(b)); return float(np.max(np.abs(a[:n]-b[:n])))
def db(e): return 10*math.log10(e+1e-30)
R={}; SR=48000
# --- D. Solo/Mute
scen={'none':{},'solo_A':{'surfaces_solo':'A'},'solo_B':{'surfaces_solo':'B'},'solo_C':{'surfaces_solo':'C'},'solo_D':{'surfaces_solo':'D'},'solo_E':{'surfaces_solo':'E'},'solo_F':{'surfaces_solo':'F'},
      'mute_A':{'surfaces_mute':['A']},'mute_B':{'surfaces_mute':['B']},'mute_all':{'surfaces_mute':list('ABCDEF')},'solo_A_mute_B':{'surfaces_solo':'A','surfaces_mute':['B']}}
paths={'early':dict(fdn_wet=0,direct_wet=1,early_wet=1),'fdn':dict(fdn_wet=1,direct_wet=0,early_wet=0),'direct':dict(fdn_wet=0,direct_wet=1,early_wet=0)}
irs={}
for s,ov in scen.items():
    for pth,pv in paths.items():
        b=dict(copy.deepcopy(body0),**pv,**ov); secs=0.5 if pth!='fdn' else 1.5
        pp,lp=play(S16,b,f'sm_{s}_{pth}',secs); rr=render(S16,b,f'sm_{s}_{pth}',int(secs*1000)); irs[s,pth]=(pp,rr,lp)
pd0,rd0,_=irs['none','direct']; n0p=int(np.argmax(np.abs(pd0).sum(1))); n0r=int(np.argmax(np.abs(rd0).sum(1)))
def we(x,n0,a,b_,ch=None):
    a=n0+int(a*SR/1000); b_=n0+int(b_*SR/1000); y=x[max(a,0):b_]; return float(np.sum(y**2)) if ch is None else float(np.sum(y[:,ch]**2))
D={}
for s in scen:
    row={}
    for eng,i,n0 in (('play',0,n0p),('render',1,n0r)):
        e=irs[s,'early'][i]; e0=irs['none','early'][i]; f=irs[s,'fdn'][i]; f0=irs['none','fdn'][i]; d=irs[s,'direct'][i]; d0=irs['none','direct'][i]
        row[eng+'_fdn_max_abs_diff_vs_none']=mx(f,f0)
        row[eng+'_direct_path_max_abs_diff_vs_none']=mx(d,d0)
        row[eng+'_early_window_direct_db_vs_none']=round(db(we(e,n0,-1,1))-db(we(e0,n0,-1,1)),2)   # D15: direct image inside early field
        row[eng+'_early_db_vs_none']=round(db(we(e,n0,1.5,80))-db(we(e0,n0,1.5,80)),2)
        row[eng+'_early_ILD_LminusR_db']=round(db(we(e,n0,1.5,80,0))-db(we(e,n0,1.5,80,1)),2)
    lp=irs[s,'early'][2]; g=lp.get('early_gate'); row['play_early_gate_ones']=None if g is None else int(sum(1 for v in g if v>0.5)); row['play_solo_mute']=lp.get('solo_mute')
    D[s]=row; print('D',s,json.dumps(row),flush=True)
R['D_solo_mute']=D
# --- Render parity bit-exact vs 11:40, default tail level 16:30 vs 11:40
par=dict(copy.deepcopy(body0),reaktor_parity=True)
a=render(S16,par,'par16',1500); b=render(S11,par,'par11',1500); R['render_parity_1630_vs_1140_max_abs_diff']=mx(a,b); print('parity',mx(a,b),flush=True)
t16=render(S16,dict(copy.deepcopy(body0),fdn_wet=1,early_wet=0,direct_wet=0),'tail16',1500); t11=render(S11,dict(copy.deepcopy(body0),fdn_wet=1,early_wet=0,direct_wet=0),'tail11',1500)
i0=int(0.05*SR); R['render_default_tail_db_1630_minus_1140']=[round(db(float(np.sum(t16[i0:,c]**2)))-db(float(np.sum(t11[i0:,c]**2))),2) for c in (0,1)]; print('tail level',R['render_default_tail_db_1630_minus_1140'],flush=True)
p16,_=play(S16,dict(copy.deepcopy(body0),fdn_wet=1,early_wet=0,direct_wet=0),'ptail16',1.5); p11,_=play(S11,dict(copy.deepcopy(body0),fdn_wet=1,early_wet=0,direct_wet=0),'ptail11',1.5)
R['play_default_tail_db_1630_minus_1140']=[round(db(float(np.sum(p16[i0:,c]**2)))-db(float(np.sum(p11[i0:,c]**2))),2) for c in (0,1)]; print('play tail level',R['play_default_tail_db_1630_minus_1140'],flush=True)
# --- comb index on Idle's scene (test DEFAULT_TAIL), Render + Play, 48k & 44.1k, 16:30 vs 11:40
import test_s4b_tail_solo_runaway as TS
comb={}
for sr in (48000,44100):
    for nm,sw in (('1630',S16),('1140',S11)):
        r=render(sw,TS.DEFAULT_TAIL,f'comb_r_{nm}_{sr}',1500,sr); x,_=play(sw,TS.DEFAULT_TAIL,f'comb_p_{nm}_{sr}',1.5,sr)
        comb[f'{nm}|{sr}']={'render_comb_db':[round(v,2) for v in TS._comb_db(r,sr)],'render_ac_max':[round(v,3) for v in TS._acmax(r,sr)],
            'play_comb_db':[round(v,2) for v in TS._comb_db(x,sr)],'play_ac_at_19.36ms':[round(v,3) for v in TS._acmax(x,sr,at_ms=19.36)],'play_ac_max':[round(v,3) for v in TS._acmax(x,sr)]}
        print('comb',nm,sr,comb[f'{nm}|{sr}'],flush=True)
R['comb_idle_scene']=comb
# --- 44.1k default room decay 20 s, 20 s Play IR, tail only: falls every 2 s
x,_=play(S16,dict(copy.deepcopy(body0),decay_lock=True,decay_s=20.0,fdn_wet=1,early_wet=0,direct_wet=0),'run441',20,44100)
lv=[round(db(float(np.mean(x[int(k*44100):int((k+1)*44100)]**2))),1) for k in range(20)]
R['runaway_441_default_decay20']={'finite':bool(np.all(np.isfinite(x))),'level_db_per_s':lv,'falls_every_2s':all(b_<a_ for a_,b_ in zip(lv[2::2],lv[4::2]))}; print('run441',R['runaway_441_default_decay20'],flush=True)
json.dump(R,open(HERE+'/s4b_measure.json','w'),indent=1); print('saved')
