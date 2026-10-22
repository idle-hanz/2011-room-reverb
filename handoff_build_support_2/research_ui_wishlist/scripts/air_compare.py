"""Item 12: HF loss of Air 1-pole (Structure) vs ISO 9613 shelf vs panel darkening, using the snapshot's engine code."""
import sys, os, json, math
import numpy as np
from scipy.signal import freqz
SW='/workspace/build_support_2/snapshot_2026-10-02_1815/software'
sys.path[:0]=[SW, SW+'/engine']; os.chdir(SW)
import early_field as E
sr=48000; F=[125,500,1000,2000,4000,8000,16000]
def mag_db(c,f):
    b=c[:3]; a=c[3:]
    w,h=freqz(b,a,worN=[2*np.pi*x/sr for x in f]); return 20*np.log10(np.abs(h))
def onepole_db(fc,f,mix):
    g=1-math.exp(-2*math.pi*min(fc,0.49*sr)/sr)
    w=np.array([2*np.pi*x/sr for x in f]); H=g/(1-(1-g)*np.exp(-1j*w))
    return 20*np.log10(np.abs((1-mix)+mix*H))
hum=0.35
wet=E.air_abs_wet_from_humidity(hum)
rows=[]
for d in (3.3,7,12,17,30):
    fc=E.air_abs_cutoff_hz(d,wet)
    r={'d_m':d,'onepole_fc_hz':round(fc,1),
       'onepole_mix1_db':[round(x,2) for x in onepole_db(fc,F,1.0)],
       'onepole_mix025_db':[round(x,2) for x in onepole_db(fc,F,0.25)]}
    lo,hi=E.iso_shelf_pair(d,sr,1.0,'studio_20C_50RH',hum)
    tot=np.zeros(len(F))
    for c in (lo,hi):
        if c is not None:
            cc=np.array(c,dtype=float)
            # coefficient layout check: (b0,b1,b2,a0,a1,a2)
            if len(cc)==6: tot+=mag_db([cc[0]/cc[3],cc[1]/cc[3],cc[2]/cc[3],1,cc[4]/cc[3],cc[5]/cc[3]],F)
    r['iso_shelf_db']=[round(x,2) for x in tot]
    rows.append(r)
# panels: default card absorb
hz=[125,250,500,1000,2000,4000,8000]; ab=[0.05,0.06,0.08,0.1,0.14,0.18,0.22]
def a_at(f): return float(np.interp(math.log(f),[math.log(x) for x in hz],ab))
panel={k:[round(k*10*math.log10(1-a_at(f)),2) for f in F] for k in (1,2,3)}
out={'freqs_hz':F,'humidity_slider':hum,'wet':wet,'rows':rows,'panel_default_card_db_by_order':panel,
     'iso_coeff_example':[list(map(float,c)) if c is not None else None for c in E.iso_shelf_pair(7,sr,1.0,'studio_20C_50RH',hum)]}
json.dump(out,open('/workspace/build_support_2/research_ui_wishlist/data/air_compare.json','w'),indent=1)
print(json.dumps(out,indent=0)[:4000])
