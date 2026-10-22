import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
R='/workspace/build_support_2/research_f5_allpass'; SR=48000
plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':0.3})
# ---------- fig1: structures
fig,axs=plt.subplots(3,1,figsize=(10,8.6))
def box(ax,x,y,w,h,t,fc='#eef'):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02',fc=fc,ec='k',lw=1.2)); ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=9.5)
def arr(ax,x0,y0,x1,y1,t=None,c='k'):
    ax.annotate('',(x1,y1),(x0,y0),arrowprops=dict(arrowstyle='->',lw=1.3,color=c))
    if t: ax.text((x0+x1)/2,(y0+y1)/2+0.07,t,ha='center',fontsize=8.5,color=c)
titles=['Render today: same-sample loop (solves (I + g·diag(d)·H·D)·y = r − d·xin with M every sample)',
        'Play today: z⁻¹ between the Hadamard and the allpass input  →  loop = g·H·D · z⁻¹ · A(z)',
        "Idle's restructure: allpass input node u = s[n−1] (feed-forward and feedback both from u)  →  identical to Play, 1 sample later"]
for k,ax in enumerate(axs):
    ax.set_xlim(0,10); ax.set_ylim(0,2.2); ax.axis('off'); ax.set_title(titles[k],fontsize=10,loc='left')
    box(ax,0.2,1.2,1.1,0.55,'xin (inject)','#efe')
    box(ax,2.0,1.2,0.6,0.55,'Σ','#fff')
    if k==2: box(ax,3.0,1.2,0.8,0.55,'z⁻¹\n(u = s[n−1])','#fdd')
    box(ax,4.3,1.0,3.0,0.95,'Schroeder allpass  A(z)\ny = −d·u + r,  w = u + d·y\nr = lg·z⁻ᴰ·w  (delay line + loss + peaking)','#eef')
    box(ax,8.1,1.2,1.6,0.55,'y → output tap\n(mic mix)','#efe')
    box(ax,4.3,0.12,3.0,0.5,'g·H·D (FWHT, column signs)','#ffe')
    if k==1: box(ax,2.0,0.12,0.9,0.5,'z⁻¹ (fb)','#fdd')
    arr(ax,1.3,1.47,2.0,1.47)
    if k==2: arr(ax,2.6,1.47,3.0,1.47,'s'); arr(ax,3.8,1.47,4.3,1.47,'u')
    else: arr(ax,2.6,1.47,4.3,1.47,'s = u')
    arr(ax,7.3,1.47,8.1,1.47,'y')
    arr(ax,7.8,1.47,7.8,0.37); arr(ax,7.8,0.37,7.3,0.37)
    if k==1: arr(ax,4.3,0.37,2.9,0.37); arr(ax,2.45,0.62,2.3,1.2)
    else: arr(ax,4.3,0.37,2.3,0.37); arr(ax,2.3,0.37,2.3,1.2)
    if k==0: ax.text(2.0,0.85,'no delay: algebraic loop\n(−d·s reaches y instantly)',fontsize=8,color='#a00')
fig.tight_layout(); fig.savefig(R+'/fig/fig1_structures.png',dpi=130); plt.close(fig)
# ---------- fig2: per-line magnitude
D=400; w=np.linspace(1e-4,np.pi,1200000); f=w/np.pi*SR/2; z1=np.exp(-1j*w)
def A(d,lg=1.0): zd=lg*z1**D; return (zd-d)/(1-d*zd)
fig,ax=plt.subplots(1,2,figsize=(12,4.2))
d=0.5
ax[0].plot(f[::50],20*np.log10(np.abs(z1*A(d)))[::50],lw=2.2,zorder=5,label='Play today  z⁻¹·A_D(z)  (|T| = 1)')
ax[0].plot(f[::50],20*np.log10(np.abs(A(d)))[::50],'--',lw=1.4,zorder=6,label='Render today  A_D(z)  (|T| = 1)')
ax[0].plot(f[::7],20*np.log10(np.abs((z1**D-d*z1)/(1-d*z1**D)))[::7],lw=0.3,alpha=0.6,color='C2',label='split-node strawman (not allpass, ±9.5 dB)')
ax[0].set_xlim(0,24000); ax[0].set_ylim(-12,12); ax[0].set_xlabel('Hz (full band; the strawman ripple grows with frequency)'); ax[0].set_ylabel('|T| dB'); ax[0].set_title('Per-line transfer, d = 0.5, D = 400 samples, lossless'); ax[0].legend(fontsize=8,loc='lower right')
m2=f<=240
for d,c in ((0.044,'C2'),(0.5,'C1'),(0.98,'C3')):
    ax[1].plot(f[m2],20*np.log10(np.abs(A(d,0.968)[m2])),c,lw=1,label=f'd = {d} (Play = Render)')
ax[1].axhline(20*np.log10(0.968),color='k',ls=':',label='delay-only loss lg (−0.28 dB)')
ax[1].set_xlim(0,240); ax[1].set_ylim(-14,0.5); ax[1].set_xlabel('Hz'); ax[1].set_ylabel('per-pass |A| dB')
ax[1].set_title('Loss inside the delay (lg 0.968): per-pass |A|, Play = Render'); ax[1].legend(fontsize=8,loc='lower right')
fig.tight_layout(); fig.savefig(R+'/fig/fig2_per_line_magnitude.png',dpi=130); plt.close(fig)
# ---------- fig3: default room EDC + octave + gap per scene
L=lambda v,sc='default': np.fromfile(f'{R}/data/ir_{sc}_col_{v}.f32',np.float32).reshape(-1,2).astype(float)
fig,ax=plt.subplots(1,3,figsize=(15,4.3))
names={'R_cur':'Render today (same-sample)','R_z1':'Render new (z⁻¹, like Play)','P_old':'Play today','P_f5':'Play F5 (same-sample)'}
ref=None
for v,ls in (('R_cur','-'),('R_z1','--'),('P_old',':'),('P_f5','-.')):
    x=L(v); m=(x**2).sum(1); e=np.cumsum(m[::-1])[::-1]
    if ref is None: ref=e[0]
    t=np.arange(len(e))/SR; ax[0].plot(t,10*np.log10(e/ref+1e-30),ls,lw=1.4,label=names[v])
ax[0].set_xlim(0,2.5); ax[0].set_ylim(-70,2); ax[0].set_xlabel('s'); ax[0].set_ylabel('EDC dB re Render today'); ax[0].set_title('Default room, FDN only, colour on'); ax[0].legend(fontsize=8)
M=json.load(open(R+'/data/measure.json'))
oct=[63,125,250,500,1000,2000,4000,8000]
mm=M['default']['metrics']; r0=np.array(mm['R_cur|col']['oct_db'])
for i,(v,c) in enumerate((('R_z1','C1'),('P_old','C2'),('P_f5','C3'),('P_ship','C4'))):
    ax[1].bar(np.arange(8)+(i-1.5)*0.2,np.array(mm[f'{v}|col']['oct_db'])-r0,0.2,color=c,label=({'P_ship':'Play 11:40 ship (no S4b)','P_f5':'Play F5 (= 0: identical to Render today)'}.get(v) or names[v]))
ax[1].set_xticks(range(8)); ax[1].set_xticklabels(oct); ax[1].set_xlabel('octave Hz'); ax[1].set_ylabel('dB vs Render today (level-normalised)'); ax[1].set_title('Default room tail balance 80 ms–1 s'); ax[1].legend(fontsize=8)
sc=['default','bigroom','hall_preset']; pairs=[('P_ship vs R_ship|col|t13','11:40 ship: Play vs Render'),('P_old vs R_cur|col|t13','S4b proto: Play vs Render'),('P_old vs R_z1|col|t13','z⁻¹ in both (trim −1.70 dB still on Play)')]
for i,(k,lab) in enumerate(pairs):
    ax[2].bar(np.arange(3)+(i-1)*0.27,[M[s]['nulls'][k]['tail_level_db'] for s in sc],0.27,label=lab)
vals=[M[s]['nulls']['P_old vs R_z1|col|t13']['tail_level_db']+1.70 for s in sc]
ax[2].plot(np.arange(3)+0.4,vals,'D',color='C3',ms=8,label='z⁻¹ in both + same trim both paths (null −73 dB)')
for i,v in enumerate(vals): ax[2].text(i+0.4,v+0.12,f'{v:+.2f}',ha='center',fontsize=8,color='C3')
ax[2].axhspan(-1,1,color='g',alpha=0.08); ax[2].set_xticks(range(3)); ax[2].set_xticklabels(sc); ax[2].set_ylabel('Play − Render tail 80 ms–1 s, dB'); ax[2].set_title('Play vs Render tail level (t13 band ±1 dB shaded)'); ax[2].legend(fontsize=7.5,loc='lower right')
fig.tight_layout(); fig.savefig(R+'/fig/fig3_parity.png',dpi=130); plt.close(fig)
print('ok')
