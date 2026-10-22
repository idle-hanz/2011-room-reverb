"""Paired per-block t19 bench, per-variant software tree + wasm + params. argv: rounds names [shared_tail 0|1]
Each variant: (sw tree, wasm, params json). t19 scene, shared tail as argv[3] (default off). 12 alternating rounds (ABBA order)."""
import sys, os, json, types, subprocess, numpy as np, time
B='/workspace/build_support_2'; HERE=os.path.dirname(os.path.abspath(__file__))
HAR=B+'/snapshot_2026-10-03_1600/3_phase_acceptance_tests/harness'; sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
SW0=B+'/snapshot_2026-10-03_1010/software'; SW1=B+'/snapshot_2026-10-03_1600/software'
def t19params(sw,tag):
    os.makedirs(HERE+'/work_bench_'+tag,exist_ok=True)
    c=RA.Ctx(types.SimpleNamespace(sw=sw,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=HERE+'/work_bench_'+tag))
    key=RA.find_key(c, r'source_(?:pattern|radiation|directivity)[a-z_]*')
    return str(c.params('std_lock18',{key:'talking_head','source_radiation_b':'trumpet_byu','source_yaw':35.0,'source_yaw_b':-25.0,'two_sources':True}))
P0=t19params(SW0,'old'); P1=t19params(SW1,'new')
j=json.load(open(P1)); assert j.get('surf_cascade'), 'no surf_cascade in new params'
j.pop('surf_cascade'); P1n=HERE+'/work_bench_new/t19_nocas.json'; json.dump(j,open(P1n,'w'))
W=HERE+'/wasm/'
V={'A_ship':(SW0,SW0+'/static/wasm/live_stereo.wasm',P0),'S_ship':(SW1,SW1+'/static/wasm/live_stereo.wasm',P1),
   'S_nocas':(SW1,SW1+'/static/wasm/live_stereo.wasm',P1n),'A_reb':(SW0,W+'A_reb.wasm',P0),'S_reb':(SW1,W+'S_reb.wasm',P1),
   'S_D2':(SW1,W+'S_D2.wasm',P1),'S_K2':(SW1,W+'S_K2.wasm',P1),
   'S_nf':(SW1,W+'S_nf.wasm',P1),'S_scalar':(SW1,W+'S_scalar.wasm',P1),'S_nf_scalar':(SW1,W+'S_nf_scalar.wasm',P1),
   'S_D0':(SW1,W+'S_D0.wasm',P1),'S_K0':(SW1,W+'S_K0.wasm',P1),'S_nf_D0':(SW1,W+'S_nf_D0.wasm',P1),
   'S_U4':(SW1,W+'S_U4.wasm',P1),'S_U4_KM4':(SW1,W+'S_U4_KM4.wasm',P1),'S_KM4':(SW1,W+'S_KM4.wasm',P1),'S_SOA':(SW1,W+'S_SOA.wasm',P1)}
rounds=int(sys.argv[1]); names=sys.argv[2].split(','); shared=len(sys.argv)>3 and sys.argv[3]=='1'
OV=json.dumps({'shared_tail':shared})
def stats(j):
    pb=np.array(j['play_blocks']); sb=np.array(j['silence_blocks']); late=sb[len(sb)//2:]
    return {'mean':pb.mean(),'median':float(np.median(pb)),'p90':np.percentile(pb,90),'sil_late_median':float(np.median(late))}
R={n:[] for n in names}
for r in range(rounds):
    for n in (names if r%2==0 else names[::-1]):
        sw,w,p=V[n]
        out=subprocess.run(['timeout','120','node',HERE+'/bench_blocks_1600.js',sw,p,OV,'bench','4','10'],capture_output=True,text=True,env=dict(os.environ,WASM=w)).stdout
        R[n].append(stats(json.loads(out)))
    print(time.strftime('%H:%M:%S'),r,{n:round(R[n][-1]['median'],4) for n in names},flush=True)
summ={'shared_tail':shared,'rounds':rounds,'wasm_sha1':{n:subprocess.run(['sha1sum',V[n][1]],capture_output=True,text=True).stdout[:12] for n in names}}
for n in names:
    summ[n]={k:round(float(np.median([x[k] for x in R[n]])),4) for k in ('mean','median','p90','sil_late_median')}
    summ[n]['median_spread']=[round(min(x['median'] for x in R[n]),4),round(max(x['median'] for x in R[n]),4)]
ref=names[0]
for n in names[1:]:
    d=[100*(R[n][i]['median']/R[ref][i]['median']-1) for i in range(rounds)]
    summ[n][f'paired_pct_vs_{ref}']={'median':round(float(np.median(d)),2),'all':[round(x,1) for x in d]}
print(json.dumps(summ,indent=1))
tag=time.strftime('%H%M'); json.dump({'summary':summ,'runs':R},open(HERE+f'/bench_ab_{tag}_{"on" if shared else "off"}.json','w'),indent=1,default=float)
