import numpy as np, json
from scipy.optimize import curve_fit
from scipy.linalg import eig
from tube6386 import gr_db
from spicerun import ROOT
v=np.linspace(0,30,301); g=gr_db(v)
f=lambda v,A,B: A*np.log1p(v/B)
(A,B),_=curve_fit(f,v,g,p0=[20,5]); err=np.max(np.abs(f(v,A,B)-g))
f2=lambda v,a,b,c: a*v/(1+b*v)+c*v
pp,_=curve_fit(f2,v,g,p0=[2,0.05,0.1]); err2=np.max(np.abs(f2(v,*pp)-g))
print('GR(V)=A ln(1+V/B)',A,B,'maxerr dB',err, ' alt',pp,err2)
# eigen time constants of the release networks (no drive)
def taus(CT,RT,RU=None,RV=None):
    C=[CT]; caps=[]
    # node voltages x=[Vsc, Vu, Vv]; currents
    n=1+(RU is not None)+(RV is not None)
    G=np.zeros((n,n)); Cm=np.diag([CT]+([8e-6] if RU else [])+([20e-6] if RV else []))
    G[0,0]=1/RT; i=1
    for R in [RU,RV]:
        if R:
            G[0,0]+=1/R; G[0,i]-=1/R; G[i,0]-=1/R; G[i,i]+=1/R; i+=1
    w=np.linalg.eigvals(np.linalg.solve(Cm,G)); return sorted((1/np.real(w)).tolist())
out={'tube_fit':{'form':'GR_dB = A*ln(1+V/B)','A':A,'B':B,'max_err_db_0_30V':err},
     'eigen_taus_s':{5:taus(4e-6,220e3,100e3),6:taus(2e-6,220e3,100e3,100e3),1:taus(2e-6,51.9e3),2:taus(2e-6,149.9e3),3:taus(4e-6,220e3),4:taus(8e-6,220e3)}}
print(out)
json.dump(out,open(f'{ROOT}/raw/fairchild_fit.json','w'),indent=1)
