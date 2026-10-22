"""Generate mock/src/m3_mic.html (v2, 2 Oct ~19:30 BST): pattern controls live only in the Side mics and
Centre mic sections; one shared side control with a 'Split L/R' tick; L/R link chip = geometry only;
Colour 'User defined' shows the Each-mic graphs (editable), Measured hides them."""
import math
OUT='/workspace/build_support_2/research_ui_wishlist/mock/src/m3_mic.html'
def lobe(p, yaw_deg, col, fill=True, fig8=False, size=200):
    c=size/2; R=size*0.41; pts=[]; neg=[]
    for k in range(0,361,3):
        th=math.radians(k); g=math.cos(th) if fig8 else (1-p)+p*math.cos(th)
        a=math.radians(yaw_deg)+th
        r=R*abs(g); pt=(c+r*math.sin(a), c-r*math.cos(a))   # +sin: same sign as the front dot (bug 2a fixed)
        (neg if g<0 else pts).append(pt)
    d=lambda P:'M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in P)
    fy=math.radians(yaw_deg); fx,fyy=c+R*math.sin(fy), c-R*math.cos(fy)
    s=f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}"><g stroke="rgba(255,255,255,.08)" fill="none">'
    s+=''.join(f'<circle cx="{c}" cy="{c}" r="{R*q:.0f}"/>' for q in (1/3,2/3,1))+f'<path d="M{c-R} {c} H{c+R} M{c} {c-R} V{c+R}"/></g>'
    s+=f'<path d="{d(pts)} Z" fill="{col}33" stroke="{col}" stroke-width="2"/>' if fill else f'<path d="{d(pts)}" fill="none" stroke="{col}" stroke-width="2"/>'
    if neg: s+=f'<path d="{d(neg)}" fill="none" stroke="#f472b6" stroke-width="2" stroke-dasharray="5 3"/>'
    s+=f'<circle cx="{fx:.1f}" cy="{fyy:.1f}" r="7" fill="#f59e0b"/></svg>'
    return s
def row(l,w,v,dis=False): return f'<div class="row" style="{"opacity:.45" if dis else ""}"><span class="lbl">{l}</span><div class="slider"><i style="width:{w}%"></i><b style="left:{w-2}%"></b></div><span class="val">{v}</span></div>'
def sel(t,dis=False): return f'<div class="sel" style="{"opacity:.45" if dis else ""}">{t} ▾</div>'
def tick(t,on): return f'<div class="row"><span class="box{" on" if on else ""}"></span><span>{t}</span></div>'
css='''.cols{display:grid;grid-template-columns:1fr 400px;gap:12px}.caps{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.cap{background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:10px;text-align:center}
.sel{background:#0f1218;border:1px solid var(--border);border-radius:8px;padding:6px 10px;color:var(--text);font-size:12px;margin:4px 0}
.sec{background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:10px;margin:10px 0}
.sec h3{margin:0 0 6px;font-size:12px}.box{width:14px;height:14px;border:1.5px solid var(--muted);border-radius:3px;display:inline-block}
.box.on{background:var(--accent);border-color:var(--accent)}.sub2{color:var(--muted);font-size:11px;margin:6px 0 2px}
.lock{color:var(--warn);font-size:11px;margin-top:4px}.state{display:grid;grid-template-columns:1fr 1fr;gap:12px}'''
def side_section(split, locked):
    s=f'<div class="sec new"><h3 style="color:var(--left)">Side mics <span class="newtag">pattern lives here</span></h3>'
    s+=sel('Preset: Shure SM57 — dynamic cardioid')+tick('Side high-pass',False)
    if not split:
        s+='<div class="sub2">Pattern · L and R together</div>'+sel('Family: Cardioid',locked)+row('Polar',50,'Cardioid',locked)
    else:
        s+='<div class="sub2" style="color:var(--left)">Left</div>'+sel('Family: Cardioid',locked)+row('Polar',50,'Cardioid',locked)
        s+='<div class="sub2" style="color:var(--right)">Right</div>'+sel('Family: Cardioid',locked)+row('Polar',72,'Supercardioid',locked)
    s+=tick('Split L/R <span class="hint">(own preset and pattern per side)</span>',split)
    if locked: s+='<div class="lock">🔒 Shure SM57 is a fixed cardioid. Set Colour to User defined to shape the pattern.</div>'
    return s+'</div>'
def centre_section(locked):
    s='<div class="sec new"><h3 style="color:var(--source)">Centre mic</h3>'+sel('Preset: Shure SM57 — dynamic cardioid')+tick('Centre high-pass',False)
    s+='<div class="sub2">Pattern</div>'+sel('Family: Cardioid',locked)+row('Polar',30,'Wide cardioid',locked)
    if locked: s+='<div class="lock">🔒 Fixed by the measured preset.</div>'
    return s+'</div>'
listen=('<div class="panel"><h2>Mic tab sidebar</h2>'+sel('Mic setup: ORTF')+
  '<div class="row"><span class="lbl">Colour</span>'+sel('User defined')+'</div>'
  '<div class="hint">Colour: Measured · Bypass · <b>User defined</b> (was “Assumed toys”; saved value stays ASSUMED_TOYS).</div>'
  '<div class="new" style="margin:10px 0;padding:6px"><div class="lbl">L / R link <span class="hint">(where and how they aim)</span></div>'
  '<span class="chip on">Mirror</span><span class="chip">Linked</span><span class="chip">Independent</span>'
  '<div class="hint">Geometry only: position, height and yaw. Mirror = opposite yaw, same height (today’s Link angles). Linked = move and turn together. Independent = own X/Z/height/yaw. <b>Pattern is not part of the link</b>; it sits in Side mics below.</div></div>'
  +side_section(True,False)+centre_section(False)+
  '<div class="new" style="margin:10px 0;padding:6px"><div class="lbl">3rd mic</div><span class="chip">Off</span><span class="chip on">Centre (array)</span><span class="chip">Room (own place)</span></div>'
  +row('Capsule space',20,'0.17 m')+row('Stand X',50,'3.00 m')+row('Stand Z',20,'1.50 m')+row('Mic height',30,'1.50 m')+'</div>')
each=('<div class="panel new"><h2>Each mic <span class="newtag">shown in User defined (and Bypass)</span></h2><div class="caps">'
  f'<div class="cap"><div style="font-weight:700;color:var(--left)">Left</div>{lobe(0.5,-55,"#a78bfa")}<div class="hint">drag amber = aim · drag rim = pattern</div></div>'
  f'<div class="cap"><div style="font-weight:700;color:var(--source)">Centre</div>{lobe(0.3,0,"#fbbf24")}<div class="hint">same controls as the Centre mic section</div></div>'
  f'<div class="cap"><div style="font-weight:700;color:var(--right)">Right</div>{lobe(0.72,55,"#34d399")}<div class="hint">Right ≠ Left only with Split L/R ticked</div></div>'
  '</div><div class="hint" style="margin-top:8px">No family/polar widgets under the graphs: the graphs and the section controls write the same <code>family_*</code>/<code>polar_*</code> values. Lobes drawn with +sin (bug 2a fixed), so each lobe points at its amber front dot.</div></div>')
measured=('<div class="panel"><h2>Same tab, Colour = Measured</h2><div class="state"><div>'+side_section(False,True)+centre_section(True)+'</div>'
  '<div><div class="canvas" style="height:150px;flex-direction:column;padding:10px"><b>Each mic</b><span class="hint">hidden: the measured preset owns the pattern.<br>Aim stays on the Top view (drag the amber front there).</span></div>'
  '<div class="hint" style="margin-top:8px">Unsplit default: one control drives family_l = family_r and polar_l = polar_r. Every current setup (AB, XY, ORTF, NOS, DIN, MS, MS classic, Mono, Binaural) already has L = R, so the default UI loads them unchanged. Mono centre hides Side mics; Binaural hides both pattern blocks (the head decides).</div></div></div></div>')
html=('<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="base.css"><style>'+css+'</style></head><body>'
  '<h1>Mic tab: after (items 2, 3, 7, 19, 20) · v2</h1><div class="sub">Pattern controls only inside Side mics and Centre mic. One shared side pattern; “Split L/R” gives L and R their own. Link chip = geometry, Split tick = capsule, so nothing is set twice. Colour “User defined” shows the Each-mic graphs, live.</div>'
  '<div class="tabs"><span class="tab">Room</span><span class="tab">Source</span><span class="tab on">Mic</span><span class="tab">Mix</span><span class="tab">Space</span><span class="tab">Surfaces</span><span class="tab">Colour</span><span class="tab">Polar</span></div>'
  '<div class="cols"><div class="grid"><div class="panel"><h2>Top · Combined pattern · Source plane (unchanged)</h2><div class="canvas" style="height:200px">existing views</div></div>'
  +each+measured+'</div><div class="grid">'+listen.replace(side_section(True,False),side_section(True,False))+'</div></div></body></html>')
open(OUT,'w').write(html); print(OUT)
