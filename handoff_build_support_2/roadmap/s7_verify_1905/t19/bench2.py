"""Per-block t19 bench, alternating wasm files under one tree (1905 software, t19 scene).
Per run: mean (t19 today), median, mean after dropping blocks > 3x median, late-silence mean/median.
Paired per-round differences vs the first variant."""
import sys, os, json, types, subprocess, numpy as np, time
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'; HERE=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
SW=B+'/snapshot_2026-10-02_1905/software'
a=types.SimpleNamespace(sw=SW,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=HERE+'/work_1905')
c=RA.Ctx(a); key=RA.find_key(c, r'source_(?:pattern|radiation|directivity)[a-z_]*')
p=c.params('std_lock18',{key:'talking_head','source_radiation_b':'trumpet_byu','source_yaw':35.0,'source_yaw_b':-25.0,'two_sources':True})
V={'w08a9_1630':HERE+'/ship_1630_bbb23260.wasm','w69eb_1905':SW+'/static/wasm/live_stereo.wasm','R1905':HERE+'/rebuilt_1905.wasm','F2':HERE+'/F2.wasm'}
names=sys.argv[2].split(',') if len(sys.argv)>2 else list(V); rounds=int(sys.argv[1])
def stats(j):
    pb=np.array(j['play_blocks']); sb=np.array(j['silence_blocks']); late=sb[len(sb)//2:]; m=np.median(pb)
    return {'mean':pb.mean(),'median':m,'trim3':pb[pb<=3*m].mean(),'n_drop3':int((pb>3*m).sum()),'p90':np.percentile(pb,90),
            'sil_late_mean':late.mean(),'sil_late_median':np.median(late),'max':pb.max()}
R={n:[] for n in names}; raw={}
for r in range(rounds):
    for n in (names if r%2==0 else names[::-1]):
        env=dict(os.environ,WASM=V[n])
        out=subprocess.run(['node',HERE+'/bench_blocks.js',SW,str(p),'{}','bench','4','10'],capture_output=True,text=True,env=env).stdout
        j=json.loads(out); s=stats(j); R[n].append(s); raw.setdefault(n,[]).append({'play':j['play_blocks'],'sil':j['silence_blocks']})
    print(r,{n:(round(R[n][-1]['mean'],3),round(R[n][-1]['median'],3)) for n in names},flush=True)
summ={}
for n in names:
    summ[n]={k:{'min':round(min(x[k] for x in R[n]),4),'median':round(float(np.median([x[k] for x in R[n]])),4),
                'spread':[round(min(x[k] for x in R[n]),3),round(max(x[k] for x in R[n]),3)]} for k in ('mean','median','trim3','sil_late_mean','sil_late_median')}
ref=names[0]
for n in names[1:]:
    for k in ('mean','median'):
        d=[100*(R[n][i][k]/R[ref][i][k]-1) for i in range(rounds)]
        summ[n][f'paired_pct_vs_{ref}_{k}']={'median':round(float(np.median(d)),2),'all':[round(x,1) for x in d]}
print(json.dumps(summ,indent=1))
tag=time.strftime('%H%M'); json.dump({'summary':summ,'runs':{n:[{k:float(v) for k,v in s.items()} for s in R[n]] for n in names}},open(HERE+f'/bench2_{tag}.json','w'),indent=1)
np.savez_compressed(HERE+f'/bench2_{tag}_blocks.npz',**{f'{n}_{i}_{k}':np.array(x[k]) for n in raw for i,x in enumerate(raw[n]) for k in ('play','sil')})
