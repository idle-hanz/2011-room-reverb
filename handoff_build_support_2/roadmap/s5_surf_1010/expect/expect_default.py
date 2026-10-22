"""S5 / D-UI26=A expected change (3 Oct 2026, 1010 tree, box only, read-only snapshot).
R0 = shipped Render (snapshot_2026-10-03_1010). RA = Render prototype A (protoA_sw: hit-face absorb shape
relative to card mean + face EQ cascaded on each FDN inject line; early taps unchanged).
Outputs third-octave deltas (dB, L/R mean) per window."""
import sys, json, types, copy, os, numpy as np
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'; HERE=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
def ctx(sw,wd):
    os.makedirs(wd,exist_ok=True)
    return RA.Ctx(types.SimpleNamespace(sw=sw,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=wd))
C0=ctx(B+'/snapshot_2026-10-03_1010/software',HERE+'/work_r0'); CA=ctx(B+'/roadmap/s5_surf_1010/protoA_root/software',HERE+'/work_ra')
SR=48000; MS=1500
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.update({"direct_wet":1.0,"early_wet":1.0,"fdn_wet":1.0})
BUS={'mix':{},'early':{"direct_wet":0.0,"fdn_wet":0.0},'fdn':{"direct_wet":0.0,"early_wet":0.0}}
FC=[100,125,160,200,250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,8000,10000,12500,16000]
def bands(x):
    X=np.abs(np.fft.rfft(x,1<<int(np.ceil(np.log2(len(x)+1)))))**2; f=np.fft.rfftfreq(2*(len(X)-1),1/SR)
    return np.array([X[(f>=fc*2**-(1/6))&(f<fc*2**(1/6))].sum()+1e-30 for fc in FC])
W={'0-80ms':(0,int(0.08*SR)),'80ms+':(int(0.08*SR),None),'80-300ms':(int(0.08*SR),int(0.3*SR)),'300ms+':(int(0.3*SR),None)}
def delta(ir1,ir0,w):
    a,b=W[w]; d=[10*np.log10(bands(ir1[a:b,ch])/bands(ir0[a:b,ch])) for ch in (0,1)]
    return [round(float(v),2) for v in np.mean(d,axis=0)]
def body(bus,face=None):
    b=dict(copy.deepcopy(base),**BUS[bus])
    if face: face(b)
    return b
def flat_absorb(b):
    for L,s in b['surfaces'].items():
        m=sum(s['absorb'])/len(s['absorb']); s['absorb']=[m]*len(s['absorb'])
def hs6(b): b['surfaces']['A']['eq']['high_shelf_db']=6.0
def tilt(b): b['surfaces']['A']['absorb']=list(reversed(b['surfaces']['A']['absorb']))
def hs6_all(b):
    for s in b['surfaces'].values(): s['eq']['high_shelf_db']=6.0
R={'fc':FC,'notes':{}}
def rec(k,ir1,ir0,ws):
    R[k]={w:delta(ir1,ir0,w) for w in ws}; R[k]['null_db']=round(RA.null_db(ir1.ravel(),ir0.ravel()),1)
    print(k,{w:(min(R[k][w]),max(R[k][w])) for w in ws},R[k]['null_db'],flush=True)
r=lambda C,b: C.render_ir(b,MS)
# 1 default change, tail (RA vs R0)
for bus in ('fdn','mix'):
    rec(f'default_tail|{bus}|RA_vs_R0', r(CA,body(bus)), r(C0,body(bus)), ('80ms+','80-300ms','300ms+','0-80ms'))
# early bus unchanged by prototype A (sanity, expect exact)
e0=r(C0,body('early')); eA=r(CA,body('early')); R['early_RA_vs_R0_maxabs']=float(np.max(np.abs(eA-e0))); print('early RA-R0 maxabs',R['early_RA_vs_R0_maxabs'])
# 2 Play early expected change: Render early with per-band absorb vs absorb flattened to the card mean (= what Play does today)
eF=r(C0,body('early',flat_absorb)); rec('default_play_early_expected|early|R0_vs_R0flat', e0, eF, ('0-80ms',))
# proxy check: Play today vs Render-flat early, and Play today vs Render early
pe=C0.play_ir(body('early'),{},MS/1000)
n=min(len(pe),len(eF)); rec('proxy|early|Play_vs_R0flat', pe[:n], eF[:n], ('0-80ms',)); rec('proxy|early|Play_vs_R0', pe[:n], e0[:n], ('0-80ms',))
# 3 +6 dB HS on face A, and on all faces, and absorb tilt: tail moves (RA) vs not (R0)
for cname,fn in (('hs6_A',hs6),('tilt_A',tilt),('hs6_all',hs6_all)):
    rec(f'{cname}|fdn|RA', r(CA,body('fdn',fn)), r(CA,body('fdn')), ('80ms+',))
    rec(f'{cname}|fdn|R0', r(C0,body('fdn',fn)), r(C0,body('fdn')), ('80ms+',))
# 4 flat-everything: with absorb flattened and EQ flat, RA == R0 exactly on fdn
fA=r(CA,body('fdn',flat_absorb)); f0=r(C0,body('fdn',flat_absorb)); R['flat_fdn_RA_vs_R0_maxabs']=float(np.max(np.abs(fA-f0))); print('flat fdn maxabs',R['flat_fdn_RA_vs_R0_maxabs'])
json.dump(R,open(HERE+'/expect_default.json','w'),indent=1)
