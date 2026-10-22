# 6386 remote-cutoff triode black-box model, Raffensperger DAFx-12 Eq.1 / Table 1
import numpy as np
p=dict(p1=3.981e-8,p2=2.383,p3=0.5,p4=0.1,p5=1.8,p6=0.5,p7=-0.03922,p8=0.2)
def Ia(vgk,vak):
    return p['p1']*vak**p['p2']/((p['p3']-p['p4']*vgk)**p['p5']*(p['p6']+np.exp(p['p7']*vak-p['p8']*vgk)))
def gm(vgk,vak=250.0,h=1e-3): return (Ia(vgk+h,vak)-Ia(vgk-h,vak))/(2*h)
VBIAS=-7.2
def gr_db(vsc,vak=250.0):
    """gain reduction (positive dB) for sidechain voltage magnitude vsc (grid driven more negative)"""
    return -20*np.log10(gm(VBIAS-np.asarray(vsc),vak)/gm(VBIAS,vak))
if __name__=='__main__':
    for v in [0,1,2,4,6,8,10,15,20,30,40]:
        print(v, round(float(gr_db(v)),2), round(float(gr_db(v,150)),2), round(float(gr_db(v,300)),2), 'Ia mA',round(float(Ia(VBIAS-v,250))*1e3,2))
