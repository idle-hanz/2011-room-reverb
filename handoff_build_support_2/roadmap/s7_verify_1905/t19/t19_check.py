"""t19 cost investigation (box). Mode 'exact': Play IRs of each wasm variant vs shipped 1905 wasm
(shared off and on, t19 scene and default FDN scene). Mode 'bench': alternating t19 bench rounds."""
import sys, os, json, types, time, numpy as np
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'; HERE=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[HAR, HAR+'/lib']
import run_all as RA
PY='/workspace/scratch_er_dropout/venv/bin/python'
def ctx(sw, tag):
    a=types.SimpleNamespace(sw=sw,python=PY,node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=HERE+'/work_'+tag)
    os.makedirs(a.workdir,exist_ok=True); return RA.Ctx(a)
SW={t:B+f'/snapshot_2026-10-02_{t}/software' for t in ('1140','1630','1905')}
def t19p(c):
    key=RA.find_key(c, r'source_(?:pattern|radiation|directivity)[a-z_]*')
    return c.params('std_lock18',{key:'talking_head','source_radiation_b':'trumpet_byu','source_yaw':35.0,'source_yaw_b':-25.0,'two_sources':True})
C={t:ctx(SW[t],t) for t in SW}
VAR={'ship1905':None,'reb1905':HERE+'/rebuilt_1905.wasm','F1':HERE+'/F1.wasm','F2':HERE+'/F2.wasm'}
mode=sys.argv[1]
if mode=='exact':
    c=C['1905']; out={}
    base=json.load(open(B+'/roadmap/s4_verify_1140/measure/client_body_1140.json'))
    scenes={'t19':t19p(c),'default':c.params(base)}
    for sn,p in scenes.items():
        for sh in (False,True):
            ref=None
            for v,w in VAR.items():
                o=os.path.join(c.work,f'{sn}_{int(sh)}_{v}.f32'); c.play(p,{'shared_tail':sh},'ir',2.0,o,wasm=w); x=np.fromfile(o,np.float32).astype(np.float64)
                if ref is None: ref=x; out[f'{sn}_shared{int(sh)}_rms_db']=round(10*np.log10(np.mean(ref**2)+1e-300),2)
                else: out[f'{sn}_shared{int(sh)}_{v}_maxabs']=float(np.max(np.abs(x-ref)))
    print(json.dumps(out,indent=1)); json.dump(out,open(HERE+'/exact.json','w'),indent=1)
else:
    rounds=int(sys.argv[2]); names=sys.argv[3].split(',')
    runs={'T1140':(C['1140'],None),'T1630':(C['1630'],None),'T1905':(C['1905'],None),
          'R1630':(C['1905'],HERE+'/rebuilt_1630.wasm'),'R1905':(C['1905'],HERE+'/rebuilt_1905.wasm'),
          'F1':(C['1905'],HERE+'/F1.wasm'),'F2':(C['1905'],HERE+'/F2.wasm')}
    P={t:t19p(c) for t,c in C.items()}
    res={n:[] for n in names}
    for r in range(rounds):
        for n in (names if r%2==0 else names[::-1]):
            c,w=runs[n]; p=P['1905'] if c is C['1905'] else P[[k for k in C if C[k] is c][0]]
            j=json.loads(c.play(p,{},'bench',4,10,wasm=w)); res[n].append(round(j['play_mean_ms'],4))
        print(r, {n:res[n][-1] for n in names}, flush=True)
    summ={n:{'min':min(v),'median':float(np.median(v)),'all':v} for n,v in res.items()}
    print(json.dumps(summ,indent=1)); json.dump(summ,open(HERE+f'/bench_{int(time.time())}.json','w'),indent=1)
