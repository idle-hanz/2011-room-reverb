# SPICE: SSL 4000 G bus compressor sidechain, behavioural closed loop with the real 82E27 timing parts.
# Topology (82E26/82E27 drawings, gyraf.dk): output-mirroring sidechain VCA -> full-wave rectifier ->
# diode -> attack resistor (820R/2K7/8K2/27K/82K/270K) -> release cap network -> buffer -> VCA control (exp law).
# Unknown scale: KDB = dB of gain reduction per volt on the timing cap (ASSUMED 20 dB/V); VOFF sets onset ratio.
import numpy as np, json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from spicerun import run, ROOT
KDB=20.0
ATT={0.1:820,0.3:2.7e3,1:8.2e3,3:27e3,10:82e3,30:270e3}
REL={0.1:180e3,0.3:270e3,0.6:560e3,1.2:1.2e6}
def net(ratio_onset,att_ms,rel,amp,t_on,t_end,f=500):
    vth=(ratio_onset-1)/(0.1151*KDB)        # effective threshold volts that gives the onset ratio
    voff=vth-0.55
    b=f"""Vin in 0 SIN(0 {amp} {f} 0 0 0)
Vgate g1 0 PWL(0 1 {t_on} 1 {t_on+1e-4} 0)
Bout out 0 V=v(in)*v(g1)*exp(-{KDB}*0.11513*v(n1))
Brect r 0 V=abs(v(out))-{voff}
D1 r d DSIG
Ra d n1 {ATT[att_ms]}
"""
    if rel=='auto':
        b+="C1 n1 n2 0.47u\nR7 n1 n2 91k\nC2 n2 0 6.8u\nR8 n2 0 750k\n"
    else:
        b+=f"C1 n1 0 0.47u\nR9 n1 0 {REL[rel]}\n"
    return b
def sim(name,ratio,att,rel,amp,t_on,t_end):
    step=min(2e-5,t_end/2e5)
    d=run(name,net(ratio,att,rel,amp,t_on,t_end),['v(n1)','v(out)'],tran=f'{step} {t_end} 0 {step}')
    return d['time'],KDB*d['vn1']
if __name__=='__main__':
    out={}
    # 1) release shapes vs burst length, auto release, 4:1, 10 ms attack, ~10 dB GR
    fig,ax=plt.subplots(1,2,figsize=(13,5))
    out['auto_release']={}
    for dur in [0.05,0.3,1.0,3.0,8.0]:
        t,gr=sim(f'ssl_auto_burst{dur}',4,10,'auto',4.0,dur,dur+12)
        i0=np.searchsorted(t,dur); g0=gr[i0-1]; tr=t[i0:]-dur; g=gr[i0:]
        def tc(x):
            j=np.where(g<=x)[0]; return float(tr[j[0]]) if len(j) else None
        out['auto_release'][dur]=dict(gr_end=round(float(g0),2),t50=tc(g0/2),t37=tc(g0*0.368),t_1dB=tc(1.0),t_0p5dB=tc(0.5))
        np.savetxt(f'{ROOT}/raw/ssl_auto_release_{dur}.csv',np.c_[tr[::10],g[::10]],delimiter=',',header='t_s,gr_db')
        ax[0].plot(tr,g,label=f'{dur}s burst'); print('auto',dur,out['auto_release'][dur]); sys.stdout.flush()
    ax[0].set_xscale('symlog',linthresh=0.05); ax[0].set_title('SSL Auto release after bursts (4:1, 10 ms)'); ax[0].set_xlabel('s'); ax[0].set_ylabel('GR dB'); ax[0].legend()
    # 2) fixed releases from ~10 dB
    out['fixed_release']={}
    for rel in REL:
        t,gr=sim(f'ssl_fixed_{rel}',4,1,rel,4.0,0.5,0.5+6*REL[rel]*0.47e-6+0.5)
        i0=np.searchsorted(t,0.5); g0=gr[i0-1]; tr=t[i0:]-0.5; g=gr[i0:]
        def tc(x):
            j=np.where(g<=x)[0]; return float(tr[j[0]]) if len(j) else None
        out['fixed_release'][rel]=dict(gr_end=round(float(g0),2),tau_RC=REL[rel]*0.47e-6,t37=tc(g0*0.368),t_1dB=tc(1.0),t_0p5dB=tc(0.5))
        print('fixed',rel,out['fixed_release'][rel]); sys.stdout.flush()
    # 3) attack: time to 63% of final GR vs ratio and level
    out['attack']={}
    for ratio in [2,4,10]:
        for amp in [2.0,4.0,8.0]:
            for att in [0.3,10]:
                T=0.4 if att==10 else 0.05
                t,gr=sim(f'ssl_att_r{ratio}_a{amp}_t{att}',ratio,att,'auto' if False else 1.2,amp,T,T)
                gf=gr[-1]; j=np.where(gr>=0.632*gf)[0]; t63=float(t[j[0]]) if len(j) else None
                out['attack'][f'r{ratio}_amp{amp}_att{att}']=dict(gr_final=round(float(gf),2),t63_ms=round(t63*1e3,3) if t63 else None,tauRC_ms=ATT[att]*0.47e-3)
                print('att',ratio,amp,att,out['attack'][f'r{ratio}_amp{amp}_att{att}']); sys.stdout.flush()
    plt.tight_layout(); plt.savefig(f'{ROOT}/plots/ssl_release.png',dpi=110)
    json.dump(out,open(f'{ROOT}/raw/ssl_summary.json','w'),indent=1)
