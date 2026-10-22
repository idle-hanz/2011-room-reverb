import sys, json, numpy as np
sw=sys.argv[1]; sys.path[:0]=[sw, sw+'/engine']
import air_iso as A, early_field as ef
sr=48000; f=np.geomspace(100,16000,400); z=np.exp(-2j*np.pi*f/sr)
def pair_db(pair):
    r=np.zeros_like(f)
    for c in pair:
        if c is None: continue
        b0,b1,b2,a0,a1,a2 = c if len(c)==6 else (c[0],c[1],c[2],1.0,c[3],c[4])
        r+=20*np.log10(np.abs((b0+b1*z+b2*z*z)/(a0+a1*z+a2*z*z)))
    return r
def true_alpha(ff,T,rh,p=101.325):  # independent ISO 9613-1 (h in percent)
    tk=T+273.15; C=-6.8346*(273.16/tk)**1.261+4.6151; h=rh*10**C*101.325/p
    frO=(p/101.325)*(24+4.04e4*h*(0.02+h)/(0.391+h)); frN=(p/101.325)*(tk/293.15)**-0.5*(9+280*h*np.exp(-4.170*((tk/293.15)**(-1/3)-1)))
    return 8.686*ff**2*(1.84e-11*(101.325/p)*(tk/293.15)**0.5+(tk/293.15)**-2.5*(0.01275*np.exp(-2239.1/tk)/(frO+ff**2/frO)+0.1068*np.exp(-3352/tk)/(frN+ff**2/frN)))
out={}
T1={1000.0:{10:21.6,50:4.26,90:3.54},3981.07:{10:57.3,50:46.7,90:25.7},7943.28:{10:69.4,50:155.0,90:92.4}}
out['iso_table1_10C']=[(fq,rh,round(1000*float(A._iso_alpha_db_per_m(np.array([fq]),10,rh,101.325)[0]),2),w) for fq,r in T1.items() for rh,w in r.items()]
out['iso_table1_max_rel_err_pct']=round(max(abs(g-w)/w*100 for _,_,g,w in out['iso_table1_10C']),2)
out['engine_vs_independent_alpha_maxrel']=float(max(np.max(np.abs(A._iso_alpha_db_per_m(f,T,rh,101.325)/true_alpha(f,T,rh)-1)) for T in (20,22) for rh in (20,50,90)))
# peak RH
fb=f[f>=8000]
pk={}
for T in (20.0,22.0):
    rhs=np.arange(5,60,0.1); m=[float(np.mean(-true_alpha(fb,T,r)*30)) for r in rhs]; pk[T]=round(float(rhs[int(np.argmin(m))]),1)
out['peak_rh_independent']=pk; out['peak_rh_engine']={T:A.peak_rh_pct(T) for T in (20.0,22.0)}
# fit + monotonic per climate
clim=['studio_20C_50RH','dry_20C_20RH','humid_20C_80RH','warm_22C_40RH']
fit={}; mono={}
band=f>=8000
for c in clim:
    T=A.climate_record(c)['conditions']['temperature_c']
    worst=(0,None)
    for h in (0.02,0.1,0.2,0.35,0.5,0.7,0.85,1.0):
        rh=A.rh_pct_from_slider(h,c)
        for d in (1.0,5.0,10.0,30.0):
            e=pair_db(ef.iso_shelf_pair(d,sr,1.0,c,h))-(-true_alpha(f,T,rh)*d)
            mx=float(np.max(np.abs(e))); rm=float(np.sqrt(np.mean(e**2)))
            key=f'{d:g}m'; fit.setdefault(c,{}).setdefault(key,[0,0])
            fit[c][key]=[round(max(fit[c][key][0],mx),3),round(max(fit[c][key][1],rm),3)]
    hs=np.linspace(0.01,1,100); rhs=[A.rh_pct_from_slider(h,c) for h in hs]
    v=[float(pair_db(ef.iso_shelf_pair(30.0,sr,1.0,c,h))[band].mean()) for h in hs]
    vi=[float(np.mean(-true_alpha(fb,T,r)*30)) for r in rhs]
    per={}
    for fq in (4000,8000,12500,16000):
        i=int(np.argmin(abs(f-fq))); vv=[float(pair_db(ef.iso_shelf_pair(30.0,sr,1.0,c,h))[i]) for h in hs]
        per[fq]=round(float(max(np.diff(vv).max(),0)),3)
    mono[c]={'rh_0.01':round(rhs[0],1),'rh_0.35':round(A.rh_pct_from_slider(0.35,c),1),'rh_1.0':round(rhs[-1],1),
             'loss_8_16k_30m_h0.01':round(v[0],2),'h0.35':round(float(pair_db(ef.iso_shelf_pair(30.0,sr,1.0,c,0.35))[band].mean()),2),'h1.0':round(v[-1],2),
             'max_step_up_db_mean':round(float(max(np.diff(v).max(),0)),4),'max_step_up_trueiso_mean':round(float(max(np.diff(vi).max(),0)),4),
             'max_step_up_db_single_freq':per,'rh_monotonic_decreasing':bool(np.all(np.diff(rhs)<=1e-9))}
out['fit_vs_true_iso_max_rmse_db']=fit; out['monotonic']=mono
# multiplier check: shelf depth equals physical (air_shelf=1)
out['shelf_specs_studio_10m_h035']=A.shelf_specs(10.0,1.0,'studio_20C_50RH',48000.0,A.rh_pct_from_slider(0.35))
json.dump(out,open(sys.argv[2],'w'),indent=1,default=str); print(json.dumps(out,indent=1,default=str))
