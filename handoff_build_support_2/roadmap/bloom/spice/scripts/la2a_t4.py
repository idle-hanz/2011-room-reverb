# Behavioural T4 (EL panel + CdS LDR) model, fitted to measured optical-cell data (Stroe 2018, Table 6.6, "CdS + Old Modelled")
# and run closed-loop in ngspice. THIS IS A BEHAVIOURAL MODEL: no physical SPICE model of the T4 exists.
import numpy as np, json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.optimize import fsolve, brentq
from spicerun import run, ROOT
# 1) memory law: tau_rel(d) = r0 + (r1-r0)*(1-exp(-d/tm)) through (0.3,0.090),(1,0.580),(5,1.560)
D=np.array([0.3,1.0,5.0]); R=np.array([0.090,0.580,1.560])
from scipy.optimize import least_squares
R0=0.06  # floor: short-peak release, consistent with UA '60 ms to 50%' (tau ~87 ms) and Stroe 90 ms @300 ms burst
Mf=lambda d,t: 1-(1+d/t)*np.exp(-d/t)   # 2nd-order (two cascaded lags) memory charge
sol=least_squares(lambda p: R0+(p[0]-R0)*Mf(D,p[1])-R,[1.6,0.8]); r1,tm=sol.x; r0=R0
print('memory fit r0,r1,tm',r0,r1,tm,'resid',R0+(r1-R0)*Mf(D,tm)-R)
# alternative 'delayed' memory (sigmoid-ish via second-order charge) is not needed: 3 points, 3 params.
# 2) two-stage attack: 63% at 0.128 s, ~full (95%) at 0.128+1.0 s  -> w*e^-t/a1+(1-w)e^-t/a2
def att(p):
    w,a1,a2=p
    f=lambda t: 1-(w*np.exp(-t/a1)+(1-w)*np.exp(-t/a2))
    return [f(0.128)-0.632, f(1.128)-0.95, a2/a1-12]
w,a1,a2=fsolve(att,[0.7,0.08,0.9]); print('attack fit w,a1,a2',w,a1,a2,att([w,a1,a2]))
fit=dict(memory=dict(form='tau_rel = r0 + (r1-r0)*M2; M1,M2 cascaded lags: dM1/dt=(1-M1)/tm, dM2/dt=(M1-M2)/tm while compressing (light on); both decay with tm_decay when dark',r0_s=r0,r1_s=r1,tm_s=tm),
         attack=dict(form='GR = G*(1 - w e^-t/a1 - (1-w) e^-t/a2)',w=w,a1_s=a1,a2_s=a2,note='a2/a1 ratio fixed to 12 to make 3 eqs; Stroe gives only 63% and full points'))
# 3) closed-loop SPICE: shunt LDR attenuator, feedback (sidechain from output), EL light ~ |out|^n, LDR G ~ L^gamma
GAMMA=0.6   # PDV-P8001 sensitivity (Advanced Photonix datasheet); AP range 0.6-0.85
NEL=3.0     # EL brightness exponent vs drive (ESTIMATE)
RS=1.0      # normalised series resistor; G in units of 1/RS
def net(amp,t_on,t_end,mem_decay=20.0,f=500):
    # states: vm (memory 0..1), vgf/vgs (fast/slow conductance parts), driven by target gt = K*L^gamma
    return f"""Vin in 0 SIN(0 {amp} {f})
Vgate gt0 0 PWL(0 1 {t_on} 1 {t_on+1e-4} 0)
Bout out 0 V=v(in)*v(gt0)/(1+{RS}*(v(gf)+v(gs)))
* EL light: rectified output, smoothed 1 ms (EL phosphor; ESTIMATE)
Bl lraw 0 V=pow(abs(v(out))+1e-12,{NEL})
Rl lraw l 1k
Cl l 0 1u
Bt tgt 0 V=20*pow(abs(v(l))+1e-12,{GAMMA})
* memory M: charges toward 1 while light present (tm), decays with mem_decay s
Bm1 0 m1 I=(v(l)>1e-3 ? (1-v(m1))/{tm} : -v(m1)/{mem_decay})
Cm1 m1 0 1
Rm1 m1 0 1e9
Bm 0 m I=(v(l)>1e-3 ? (v(m1)-v(m))/{tm} : -v(m)/{mem_decay})
Cm m 0 1
Rmx m 0 1e9
* conductance parts: rise with a1/a2 (weights w,1-w), fall with tau_rel(M)
Bf 0 gf I=(({w}*v(tgt))>v(gf) ? ({w}*v(tgt)-v(gf))/{a1} : ({w}*v(tgt)-v(gf))/({r0}+({r1}-{r0})*v(m)))
Cf gf 0 1
Rfx gf 0 1e9
Bs 0 gs I=(((1-{w})*v(tgt))>v(gs) ? ((1-{w})*v(tgt)-v(gs))/{a2} : ((1-{w})*v(tgt)-v(gs))/({r0}+({r1}-{r0})*v(m)))
Cs gs 0 1
Rsx gs 0 1e9
"""
res={}
fig,ax=plt.subplots(1,2,figsize=(13,4.5))
for dur in [0.3,1.0,5.0]:
    T=dur+6
    d=run(f'la2a_t4_burst{dur}',net(1.0,dur,T),['v(gf)','v(gs)','v(m)'],tran=f'5e-5 {T} 0 5e-5')
    t=d['time']; G=d['vgf']+d['vgs']; gr=20*np.log10(1+RS*G)
    i0=np.searchsorted(t,dur); g0=gr[i0-1]; tr=t[i0:]-dur; g=gr[i0:]
    Gr=G[i0:]; jG=np.where(Gr<=Gr[0]*0.368)[0]
    def tc(x):
        j=np.where(g<=x)[0]; return float(tr[j[0]]) if len(j) else None
    ja=np.where(gr[:i0]>=0.632*g0)[0]
    res[dur]=dict(gr_end=round(float(g0),2),attack63_s=float(t[ja[0]]),rel_G_tau_s=float(tr[jG[0]]) if len(jG) else None,
                 rel_t50_dB=tc(g0/2),rel_t37_dB=tc(g0*0.368),rel_to_1dB=tc(1),rel_to_0p5dB=tc(0.5),M_end=float(d['vm'][i0-1]))
    print(dur,res[dur]); sys.stdout.flush()
    ax[0].plot(t,gr,label=f'{dur}s burst'); ax[1].plot(tr,g,label=f'{dur}s burst')
ax[0].set_title('T4 behavioural: GR vs time'); ax[1].set_title('release after burst'); 
for a in ax: a.set_xlabel('s'); a.set_ylabel('GR dB'); a.legend()
plt.tight_layout(); plt.savefig(f'{ROOT}/plots/la2a_t4_bursts.png',dpi=110)
# static curve (algebraic steady state): out = in/(1+G), G=20*(out^NEL)^GAMMA
xin=np.geomspace(0.05,20,60); yo=[]
for a in xin:
    yo.append(brentq(lambda o: o*(1+20*(o**NEL)**GAMMA)-a,1e-9,a))
yo=np.array(yo); xd=20*np.log10(xin); yd=20*np.log10(yo); ratio=np.gradient(xd,yd)
fit['static']=dict(in_db=xd[::4].tolist(),out_db=yd[::4].tolist(),local_ratio=ratio[::4].tolist(),asymptotic_ratio=1+GAMMA*NEL)
json.dump(dict(fit=fit,bursts=res,params=dict(GAMMA=GAMMA,NEL=NEL)),open(f'{ROOT}/raw/la2a_summary.json','w'),indent=1)
print('static ratio samples',[(round(a,1),round(b,2)) for a,b in zip(xd[::6],ratio[::6])])
