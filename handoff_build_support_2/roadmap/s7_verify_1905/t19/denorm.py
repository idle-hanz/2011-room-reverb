"""Does an unguarded build (LS_DC = LS_TINY = 0) show a denormal climb in late silence, and does a median see it?"""
import sys, os, json, types, subprocess, numpy as np
B='/workspace/build_support_2'; HAR=B+'/3_phase_acceptance_tests/harness'; HERE=os.path.dirname(os.path.abspath(__file__))
sys.path[:0]=[HAR, HAR+'/lib']; import run_all as RA
SW=B+'/snapshot_2026-10-02_1905/software'
a=types.SimpleNamespace(sw=SW,python='/workspace/scratch_er_dropout/venv/bin/python',node='node',golden=HAR+'/golden',regen_golden=False,quick=False,perf_scale=1.0,workdir=HERE+'/work_1905')
c=RA.Ctx(a)
out={}
for dec in [float(x) for x in sys.argv[1].split(',')]:
    for col in (False, True):
        p=c.params('std_lock18',{'decay_s':dec})
        for n,w in (('guarded',SW+'/static/wasm/live_stereo.wasm'),('noguard',HERE+'/NOGUARD.wasm')):
            j=json.loads(subprocess.run(['node',HERE+'/bench_blocks.js',SW,str(p),json.dumps({} if col else {"colour_on":False}),'bench','2','14'],capture_output=True,text=True,env=dict(os.environ,WASM=w)).stdout)
            pb=np.array(j['play_blocks']); sb=np.array(j['silence_blocks']); late=sb[len(sb)//2:]
            r={'play_mean':round(pb.mean(),3),'play_median':round(float(np.median(pb)),3),'sil_late_mean':round(late.mean(),3),'sil_late_median':round(float(np.median(late)),3),
               'ratio_mean':round(late.mean()/pb.mean(),2),'ratio_median':round(float(np.median(late)/np.median(pb)),2),
               'sil_1s_medians':[round(float(np.median(sb[k:k+375])),3) for k in range(0,len(sb),375)]}
            out[f'dec{dec}_{"col" if col else "byp"}_{n}']=r; print(f'dec{dec}', 'col' if col else 'byp', n, r, flush=True)
json.dump(out,open(HERE+'/denorm.json','w'),indent=1)
