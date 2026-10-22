# Static curve of a feedback compressor with linear (full-wave, peak-held) detector and exponential (dB-linear) VCA,
# i.e. the SSL G topology: GR = KDB*(Kr*a_out - Vth). Local ratio = 1 + 0.1151*(GR + KDB*Vth) = R0 + 0.1151*GR.
# Cross-check: SPICE closed-loop points from ssl_gbus.py attack runs (gr_final vs input amplitude).
import numpy as np, json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from spicerun import ROOT
s=json.load(open(f'{ROOT}/raw/ssl_summary.json'))
fig,ax=plt.subplots(1,2,figsize=(12,4.5)); out={}
for R0 in [2,4,10]:
    gr=np.linspace(0,20,201); ratio=R0+0.1151*gr
    # integrate to an in/out curve: d(in)=ratio*d(out), d(GR)=(ratio-1)*d(out)
    dout=np.diff(gr)/(ratio[:-1]-1); out_db=np.r_[0,np.cumsum(dout)]; in_db=out_db+gr
    ax[0].plot(in_db,out_db,label=f'{R0}:1 switch'); ax[1].plot(gr,ratio,label=f'{R0}:1 switch')
    pts=[(v['gr_final']) for k,v in s['attack'].items() if k.startswith(f'r{R0}_') and k.endswith('att0.3')]
    out[R0]=dict(gr=gr[::20].tolist(),ratio=ratio[::20].tolist(),spice_gr_at_amp_2_4_8=pts)
ax[0].set_xlabel('input above threshold dB'); ax[0].set_ylabel('output above threshold dB'); ax[0].legend(); ax[0].set_title('SSL-type static curve (circuit-derived law)')
ax[1].set_xlabel('gain reduction dB'); ax[1].set_ylabel('local ratio'); ax[1].legend(); ax[1].set_title('ratio rises ~0.115 per dB of GR')
plt.tight_layout(); plt.savefig(f'{ROOT}/plots/ssl_static.png',dpi=110)
json.dump(out,open(f'{ROOT}/raw/ssl_static.json','w'),indent=1); print(out)
