"""Does a per-face Surface EQ / absorption tilt reach the tail? (3 Oct 2026, 08:18 tree, read-only)
Default client body (client_body_1140). Cases vs baseline:
  hs6   : face A high shelf +6 dB (5 kHz)
  tilt  : face A absorb reversed (same mean alpha -> same broadband reflect gain), i.e. pure frequency shape
Each case in Render (render_ir) and Play (wasm play_ir), full mix and bus-isolated (early only / FDN only).
Reports third-octave deltas (dB) for window 0-80 ms and 80 ms+, plus nulls."""
import sys, json, types, copy, numpy as np
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
SW=B+'/snapshot_2026-10-03_0818/software'; OUT=B+'/research_ui_wishlist/sui2_fixup/'
a=types.SimpleNamespace(sw=SW,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir='/tmp')
c=RA.Ctx(a); SR=48000; MS=1500
base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
base.update({"direct_wet":1.0,"early_wet":1.0,"fdn_wet":1.0})
def with_face(body, fn):
    b=copy.deepcopy(body); fn(b['surfaces']['A']); return b
def hs6(card): card['eq']['high_shelf_db']=6.0
def tilt(card): card['absorb']=list(reversed(card['absorb']))
CASES={'hs6':hs6,'tilt':tilt}
BUSES={'mix':{},'early':{"direct_wet":0.0,"fdn_wet":0.0},'fdn':{"direct_wet":0.0,"early_wet":0.0}}
FC=[100,125,160,200,250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,8000,10000,12500,16000]
def bands(x):
    X=np.abs(np.fft.rfft(x,1<<int(np.ceil(np.log2(len(x)+1)))))**2; f=np.fft.rfftfreq(2*(len(X)-1),1/SR)
    return np.array([X[(f>=fc*2**-(1/6))&(f<fc*2**(1/6))].sum()+1e-30 for fc in FC])
def win(ir):
    n80=int(0.080*SR); return {'0-80ms':ir[:n80],'80ms+':ir[n80:]}
res={'fc':FC}
print('surfaces A absorb', base['surfaces']['A']['absorb'], 'eq', base['surfaces']['A']['eq'])
for bus,over in BUSES.items():
    b0=dict(copy.deepcopy(base),**over)
    for eng in ('render','play'):
        get=(lambda b: c.render_ir(b,MS)) if eng=='render' else (lambda b: c.play_ir(b,{},MS/1000))
        ir0=get(b0)
        for cname,fn in CASES.items():
            ir1=get(with_face(b0,fn)); k=f'{eng}|{bus}|{cname}'; r={}
            for w in ('0-80ms','80ms+'):
                d=[]
                for ch in (0,1):
                    x0=win(ir0[:,ch])[w]; x1=win(ir1[:,ch])[w]
                    d.append(10*np.log10(bands(x1)/bands(x0)))
                dm=np.mean(d,axis=0)
                r[w]={'delta_db':[round(float(v),2) for v in dm],'max_abs_db':round(float(np.max(np.abs(dm))),2),
                      'null_db':[round(RA.null_db(win(ir1[:,ch])[w],win(ir0[:,ch])[w]),1) for ch in (0,1)]}
            res[k]=r
            print(k, {w:(r[w]['max_abs_db'],r[w]['null_db']) for w in r}, flush=True)
json.dump(res,open(OUT+'data/face_eq_probe.json','w'),indent=1)
