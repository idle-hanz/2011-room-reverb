"""t19-style CPU on the box: two directional sources + colour (std_lock18 + talking_head/trumpet_byu), node bench 4/10,
alternating rounds, min of 6. PC estimate = PC t19 ship (2.048-2.052 ms) x box ratio (ASSUMED proportional)."""
from common import *
C=ctx('R_cur')
p=C.params('std_lock18',{'source_radiation':'talking_head','source_radiation_b':'trumpet_byu','source_yaw':35.0,'source_yaw_b':-25.0,'two_sources':True})
vs=['P_ship','P_old','P_apd','P_f5']; runs={v:[] for v in vs}
for rnd in range(6):
    for v in (vs if rnd%2==0 else vs[::-1]):
        r=json.loads(C.play(p,{},'bench',4,10,wasm=WASM[v])); runs[v].append(r['play_mean_ms'])
    print(rnd,{v:round(runs[v][-1],3) for v in vs},flush=True)
mn={v:min(x) for v,x in runs.items()}
res=dict(box_min_ms={v:round(x,3) for v,x in mn.items()},ratio_vs_ship={v:round(mn[v]/mn['P_ship'],3) for v in vs},
         pc_est_ms={v:round(2.052*mn[v]/mn['P_ship'],3) for v in vs},gate_ms=2.133,runs=runs)
print(res); json.dump(res,open(R+'/data/cpu.json','w'),indent=1)
