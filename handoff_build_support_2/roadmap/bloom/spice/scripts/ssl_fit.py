import numpy as np, json
from spicerun import ROOT
t1,t2=91e3*0.47e-6,750e3*6.8e-6
out={}
for dur in [0.05,0.3,1.0,3.0,8.0]:
    d=np.loadtxt(f'{ROOT}/raw/ssl_auto_release_{dur}.csv',delimiter=',')
    t,g=d[:,0],d[:,1]; A=np.c_[np.exp(-t/t1),np.exp(-t/t2)]
    a,res,_,_=np.linalg.lstsq(A,g,rcond=None); err=np.max(np.abs(A@a-g))
    out[dur]=dict(a_fast_db=float(a[0]),a_slow_db=float(a[1]),w_slow=float(a[1]/(a[0]+a[1])),w_slow_formula=float(min(dur/(dur+t1*6.8/0.47*0+91e3*6.8e-6),750/841)),max_fit_err_db=float(err))
    print(dur,out[dur])
json.dump(dict(tau_fast_s=t1,tau_slow_s=t2,fits=out),open(f'{ROOT}/raw/ssl_auto_fit.json','w'),indent=1)
