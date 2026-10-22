# SPICE: 1176-style FET shunt attenuator + feedback peak sidechain.
# Real parts: JFET vendor models (2N5457 Motorola, 2N3819 Vishay), C27=220nF, attack pot 25k (+ ~600R source, GroupDIY),
# release 270k + 0..5M pot (GroupDIY: 59 ms..1.16 s). Gate linearisation 1M/1M (half drain signal to gate).
# ASSUMED: series resistor RS chosen so max GR ~30 dB (jhaible PSpice study), rectifier gain/bias per "ratio" (shape study only).
import numpy as np, json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from spicerun import run, ROOT
FET={'2N5457':dict(vto=-1.8),'2N3819':dict(vto=-3.0)}
# --- 1) static FET: Rds vs Vgs (Vds = 10 mV)
fig,ax=plt.subplots(1,3,figsize=(16,4.5)); out={'rds':{}}
for f,pr in FET.items():
    body=f"Vd d 0 0.01\nVg g 0 0\nJ1 d g 0 {f}\n"
    d=run(f'jfet_rds_{f}',body,['i(Vd)'],dc=f'Vg 0 {pr["vto"]+0.02} -0.01')
    vg=d[d.dtype.names[0]]; rds=0.01/np.abs(d[d.dtype.names[1]])
    out['rds'][f]=dict(ron=float(rds[0]),vgs=vg[::10].tolist(),rds=rds[::10].tolist())
    rs=rds[0]*(10**(30/20)-1)
    gr=20*np.log10((rs+rds)/rds)  # attenuation relative to off
    gr=gr-gr[-1]
    out['rds'][f]['rs_for_30dB']=float(rs)
    ax[0].semilogy(vg,rds,label=f); ax[1].plot(vg-pr['vto'],gr,label=f'{f} (Rs={rs:.0f})')
ax[0].set_xlabel('Vgs V'); ax[0].set_ylabel('Rds ohm'); ax[0].legend(); ax[0].set_title('JFET channel resistance (vendor models)')
ax[1].set_xlabel('gate drive above pinch-off, V'); ax[1].set_ylabel('attenuation dB'); ax[1].legend(); ax[1].set_title('FET shunt attenuator law')
print('ron',{k:v['ron'] for k,v in out['rds'].items()}, 'rs', {k:v['rs_for_30dB'] for k,v in out['rds'].items()}); sys.stdout.flush()
RS=out['rds']['2N5457']['rs_for_30dB']; VTO=-1.8
def net(amp,K,vrb,ratt,rrel,t_on,t_end,bias_extra=0.0,f=1000):
    return f"""Vin in 0 SIN(0 {amp} {f})
Vgate gt 0 PWL(0 1 {t_on} 1 {t_on+1e-5} 0)
Bin in2 0 V=v(in)*v(gt)
Rs in2 fet {RS}
J1 fet g 0 2N5457
Bctl ctl 0 V=2*min({VTO-0.02-bias_extra}+v(c),-0.05)
Rg1 ctl g 1Meg
Rg2 fet g 1Meg
Cg g 0 10p
.options method=gear reltol=1e-3
Bout out 0 V=v(fet)*20
Brec r 0 V=abs(v(out))*{K}-{vrb}
D1 r d DSIG
Ra d c {ratt}
C27 c 0 220n
Rr c 0 {rrel}
"""
SET={'low_ratio':(0.5,0.3),'high_ratio':(3.0,1.5)}
out['static']={}
for s,(K,vrb) in SET.items():
    lv=[];gr=[]
    for amp in np.geomspace(0.003,3.0,19):
        d=run(f'u1176_static_{s}_{amp:.4f}',net(amp,K,vrb,1.6e3,1.27e6,0.6,0.6),['v(fet)','v(in)'],tran='2e-5 0.6 0 2e-5')
        t=d['time']; m=t>0.5
        vo=np.max(np.abs(d['vfet'][m])); vin=amp
        lv.append(20*np.log10(vin)); gr.append(20*np.log10(vin/vo*(1+RS/out['rds']['2N5457']['ron']*0+0)))
    gr=np.array(gr); gr=gr-gr[0]; lv=np.array(lv); outl=lv-gr
    slope=np.gradient(lv,outl)
    out['static'][s]=dict(in_db=lv.tolist(),gr_db=gr.tolist(),local_ratio=slope.tolist())
    ax[2].plot(lv,outl,'o-',label=s)
    print(s,[ (round(a,1),round(b,1),round(c,2)) for a,b,c in zip(lv,gr,slope)]); sys.stdout.flush()
ax[2].set_xlabel('in dB'); ax[2].set_ylabel('out dB'); ax[2].legend(); ax[2].set_title('1176-style static curve (gains assumed)')
plt.tight_layout(); plt.savefig(f'{ROOT}/plots/u1176_fet_static.png',dpi=110)
# --- 2) attack vs level and all-buttons onset lag
out['attack']={}
fig,ax=plt.subplots(1,2,figsize=(13,4.5))
for label,ratt,extra in [('fastest_att',600,0.0),('slowest_att',25.6e3,0.0),('fast_att_allbuttons_bias',600,0.6)]:
    for amp in [0.03,0.1,0.3,1.0]:
        d=run(f'u1176_att_{label}_{amp}',net(amp,3.0,1.5,ratt,1.27e6,0.05,0.05,extra),['v(fet)','v(c)'],tran='2e-6 0.05 0 2e-6')
        t=d['time']; r=out['rds']['2N5457']; vg_tab=np.array(r['vgs'][::-1]); rds_tab=np.array(r['rds'][::-1])
        vg=np.minimum(VTO-0.02-extra+d['vc'],0)
        rd=np.interp(vg,vg_tab,rds_tab, left=rds_tab[0], right=rds_tab[-1]) if False else np.exp(np.interp(vg,vg_tab,np.log(rds_tab)))
        roff=np.exp(np.interp(VTO-0.02,vg_tab,np.log(rds_tab)))
        g=20*np.log10((RS+rd)/rd)-20*np.log10((RS+roff)/roff); te=t
        gf=g[-1]; j=np.where(g>=0.632*gf)[0]; t63=float(te[j[0]]) if len(j) and gf>0.5 else None
        j10=np.where(g>=0.1)[0]; out_on=float(te[j10[0]]) if len(j10) else None
        jj=np.where(d['vc']>0.02)[0]
        out['attack'][f'{label}_{amp}']=dict(gr_final=round(float(gf),2),t63_ms=t63*1e3 if t63 else None,onset_0p1dB_ms=out_on*1e3 if out_on else None)
        print(label,amp,out['attack'][f'{label}_{amp}']); sys.stdout.flush()
        ax[0 if 'all' not in label else 1].plot(te*1e3,g,label=f'{label} {amp}')
for a in ax: a.set_xlabel('ms'); a.set_ylabel('GR dB (1 ms peak env)'); a.legend(fontsize=7)
plt.tight_layout(); plt.savefig(f'{ROOT}/plots/u1176_attack.png',dpi=110)
json.dump(out,open(f'{ROOT}/raw/u1176_summary.json','w'),indent=1)
