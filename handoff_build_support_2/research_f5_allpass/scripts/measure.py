import json, sys, numpy as np, time
from common import *
secs=float(sys.argv[1]) if len(sys.argv)>1 else 3.0
only=sys.argv[2].split(',') if len(sys.argv)>2 else list(SCENES)
C={t:ctx(t) for t in TREES}
res=json.load(open(R+'/data/measure.json')) if os.path.exists(R+'/data/measure.json') else {}
for sc in only:
    body=dict(SCENES[sc](),**FDN); IR={}
    for cm,over_c in (('col',{}),('byp',{"colour_mode":"BYPASS"})):
        b=dict(body,**over_c); ov=dict(OVER,**({"colour_on":False} if cm=='byp' else {}))
        for pv in ('P_ship','P_old','P_apd','P_f5'):
            t0=time.time(); IR[(pv,cm)]=C['R_cur'].play_ir(b,ov,secs,wasm=WASM[pv])
        if sc!='binaural':
            for rv in ('R_ship','R_cur','R_z1'):
                t0=time.time(); IR[(rv,cm)]=C[rv].render_ir(b,int(secs*1000)); print(sc,cm,rv,round(time.time()-t0,1),'s',flush=True)
        for (v,c),x in list(IR.items()):
            if c==cm: np.asarray(x,np.float32).tofile(f'{R}/data/ir_{sc}_{cm}_{v}.f32')
    out={}
    for (v,cm),x in IR.items(): out[f'{v}|{cm}']=metrics(x)
    nl={}
    for cm in ('col','byp'):
        nl[f'P_apd vs P_old (apd shifted 1 smp)|{cm}']=null(IR[('P_apd',cm)],IR[('P_old',cm)],lag=1)
        nl[f'P_old vs P_ship|{cm}']=null(IR[('P_old',cm)],IR[('P_ship',cm)])
        if sc!='binaural':
            for p,r in (('P_ship','R_ship'),('P_old','R_cur'),('P_old','R_z1'),('P_f5','R_cur'),('P_f5','R_z1')):
                nl[f'{p} vs {r}|{cm}']=null(IR[(p,cm)],IR[(r,cm)])
                m=PAR.full_metrics(IR[(p,cm)],IR[(r,cm)])
                nl[f'{p} vs {r}|{cm}|t13']=dict(tail_level_db=round(m['tail_level_diff_db_80ms_1s'],2),bal=m['tail_octave_balance_diff_db_(norm)'],
                    t30_ratio={k:round(m['t30_play'][k]/m['t30_render'][k],3) for k in m['t30_play'] if m['t30_render'][k]},
                    corr=[round(m['stereo_tail_80ms_1s']['corr_play'],3),round(m['stereo_tail_80ms_1s']['corr_render'],3)])
            nl[f'R_z1 vs R_cur|{cm}']=null(IR[('R_z1',cm)],IR[('R_cur',cm)])
    res[sc]=dict(metrics=out,nulls=nl); print(sc,json.dumps(nl)[:3000],flush=True)
    json.dump(res,open(R+'/data/measure.json','w'),indent=1)
