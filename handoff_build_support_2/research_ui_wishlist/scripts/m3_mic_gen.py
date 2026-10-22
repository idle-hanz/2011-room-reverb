"""Generate mock/src/m3_mic.html (v3.1, 3 Oct 2026 09:15 BST, S-UI2 fix-up; v3.1 = Split L/R kept in Measured, D-UI25 = no).
Layout: the Mic tools column leaves the Source plane panel and becomes a 'Mics' panel in the right sidebar
under Listen. Top and Combined stretch to the sidebar height. Source plane spans the full main width.
Two states: Colour = Measured (preset + high-pass only) and Colour = User defined (Family/Polar/Split + graphs,
no preset). Tabs show 7 (Colour merged into Surfaces, item 7, pending Idle).
Canvas pictures are real element screenshots of the running S-UI2 build (box port 7881, ORTF, 1600x1000)
stretched/contained into the proposed boxes, so their drawn content is today's, not re-fitted.
v2 is in mock/src/old/m3_mic_v2.html and mock/old/m3_mic_v2.png."""
OUT='/workspace/build_support_2/research_ui_wishlist/mock/src/m3_mic.html'
I='img_sui2/'
def row(l,w,v): return f'<div class="row"><span class="lbl">{l}</span><div class="slider"><i style="width:{w}%"></i><b style="left:{w-2}%"></b></div><span class="val">{v}</span></div>'
def sel(t,cls=''): return f'<div class="sel {cls}">{t}<span>▾</span></div>'
def tick(t,on=False): return f'<div class="row tk"><span class="box{" on" if on else ""}"></span><span>{t}</span></div>'
css='''.lay{display:grid;grid-template-columns:minmax(0,1.72fr) minmax(268px,.72fr);grid-template-areas:"stage side" "wide wide";gap:12px;align-items:stretch}
.stage{grid-area:stage;display:grid;grid-template-columns:1fr 1fr;gap:11px}.side{grid-area:side;display:flex;flex-direction:column;gap:11px}.wide{grid-area:wide}
.stage .panel{display:flex;flex-direction:column}.cv{flex:1;min-height:560px;background:#08090c center/contain no-repeat;border:1px solid var(--border);border-radius:10px;position:relative}
.dim{position:absolute;right:8px;bottom:6px;font:11px monospace;color:var(--source);background:#0b0c10cc;padding:1px 6px;border-radius:4px}
.sel{display:flex;justify-content:space-between;background:#0f1218;border:1px solid var(--border);border-radius:8px;padding:6px 10px;color:var(--text);font-size:12px;margin:4px 0}
.sel span{color:var(--muted)}.tk{font-size:12px}.box{width:14px;height:14px;border:1.5px solid var(--muted);border-radius:3px;display:inline-block}
.box.on{background:var(--accent);border-color:var(--accent)}.sec{border-top:1px solid var(--border);padding-top:8px;margin-top:8px}
.sec h3{margin:0 0 4px;font-size:12px}.sub2{margin:4px 0 0}.opts{font-size:11px;color:var(--muted);background:#0f1218;border:1px solid var(--border);border-radius:8px;padding:4px 10px;margin:0 0 4px}
.opts b{color:var(--accent)}.hero{height:600px;background:#08090c center/contain no-repeat;border:1px solid var(--border);border-radius:10px;position:relative}
.trio{display:grid;grid-template-columns:repeat(3,1fr);gap:11px;margin-top:11px}.trio div{height:360px;background:#08090c center/contain no-repeat;border:1px solid var(--border);border-radius:10px;position:relative}
.frame{border:1px solid var(--border);border-radius:14px;padding:12px;margin:0 0 26px;background:#0d0e13}
.frame>h2{color:var(--text);font-size:13px}.gone{text-decoration:line-through;color:var(--faint)}.pill{font-size:10px;color:var(--muted);border:1px solid var(--border);border-radius:999px;padding:1px 6px;margin-left:4px}'''
def mics_panel(mode):
    s='<div class="panel new"><h2>Mics <span class="newtag">moved from the Source plane tools column</span></h2>'
    s+='<div class="row"><span class="lbl">Colour</span><div style="flex:1">'+sel({'M':'Measured','U':'User defined'}[mode])+'</div></div>'
    s+='<div class="opts">order: <b>Measured</b> · <b>User defined</b> · <b>Bypass</b></div>'
    s+='<div class="sec">'+tick('Horizontally aligned',True)+tick('Link angles',True)+tick('Link heights',True)+'</div>'
    if mode=='M':
        s+='<div class="sec"><h3 style="color:var(--left)">Side mics <span class="pill">Split L/R ticked</span></h3><div class="sub2" style="color:var(--left);font-size:11px">Left</div>'+sel('Shure SM57 — dynamic cardioid')+'<div class="sub2" style="color:var(--right);font-size:11px">Right</div>'+sel('Shure SM57 — dynamic cardioid')+tick('Side high-pass (preset curve)')+tick('Split L/R <span class="hint">own measured mic per side</span>',True)+'<div class="hint">e.g. L = side mic, R = room mic, C = M/S mid (positions and routing: S-MIX, link Independent)</div></div>'
        s+='<div class="sec"><h3 style="color:var(--source)">Centre mic</h3>'+sel('Shure SM57 — dynamic cardioid')+tick('High-pass (preset curve)')+'</div>'
        s+='<div class="hint" style="margin-top:8px">Pattern comes from the preset (SM57 = fixed cardioid). Family, Polar and the capsule graphs are <b>hidden</b>, not greyed. Switch Colour to User defined to shape the pattern.<br><b>Split L/R stays</b> (D-UI25 = no, Idle 09:09): ticked, each side gets its own measured preset.</div>'
    else:
        s+='<div class="sec"><h3 style="color:var(--left)">Side mics</h3>'+sel('Family: Cardioid')+row('Polar',50,'Cardioid')+tick('Split L/R <span class="hint">own pattern per side</span>')+'</div>'
        s+='<div class="sec"><h3 style="color:var(--source)">Centre mic</h3>'+sel('Family: Cardioid')+row('Polar',50,'Cardioid')+'</div>'
        s+='<details class="sec" open><summary style="font-size:12px;font-weight:700">User defined capsule <span class="pill">moved from Listen · only in User defined</span></summary>'
        s+=row('Response Hz',0,'10000')+row('Capsule mm',38,'17.0')+'<div class="hint">Panel high-pass and Proximity dropped: Render never reads them (VERIFIED grep).</div></details>'
        s+='<div class="hint" style="margin-top:8px">No preset dropdown and no high-pass: measured colour is off in User defined. The graphs below and these rows write the same family/polar values.</div>'
    return s+'</div>'
def frame(mode):
    t={'M':'State 1 · Colour = Measured','U':'State 2 · Colour = User defined'}[mode]
    s=f'<div class="frame"><h2>{t} · viewport 1600×1000 · main 1564 px</h2>'
    s+='<div class="tabs"><span class="tab">Room</span><span class="tab">Source</span><span class="tab on">Mic</span><span class="tab">Mix</span><span class="tab">Space</span><span class="tab">Surfaces</span><span class="tab">Polar</span><span class="tab gone">Colour</span><span class="hint" style="align-self:center">7 tabs if Colour merges into Surfaces (item 7, D-UI23)</span></div>'
    s+='<div class="lay"><div class="stage">'
    s+=f'<div class="panel"><h2>Top <span class="pill">today 553×409 panel</span></h2><div class="cv" style="background-image:url({I}top.png)"><span class="dim">canvas fills the row · ≥541×560</span></div></div>'
    s+=f'<div class="panel"><h2>Combined <span class="pill">today 553×409 panel</span></h2><div class="cv" style="background-image:url({I}combined.png)"><span class="dim">canvas fills the row · ≥541×560</span></div></div>'
    s+='</div><div class="side">'
    s+=f'<div class="panel" style="padding:0;overflow:hidden"><img src="{I}listen_crop.png" style="display:block;width:100%"></div>'
    s+=mics_panel(mode)+'<div class="panel" style="padding:10px 14px"><h2 style="margin:0">▸ Advanced</h2></div></div>'
    s+='<div class="wide"><div class="panel moved"><h2>Source plane <span class="movetag">full width</span> <span class="pill">today 1117 wide, hero 847×522, tools 228</span></h2>'
    s+=f'<div class="hero" style="background-image:url({I}{"hero" if mode=="M" else "hero_ud"}.png)"><span class="dim">hero ≈1536×600 · plane re-fits to the wider box</span></div>'
    if mode=='U':
        s+='<div style="margin-top:10px;font-weight:700">Each capsule <span class="hint">one mic, not the combined pattern · User defined only</span></div><div class="trio">'
        s+=''.join(f'<div style="background-image:url({I}each_{c}.png)"></div>' for c in 'LCR')+'</div>'
    else:
        s+='<div class="hint" style="margin-top:8px">Each capsule graphs: hidden in Measured (the preset owns the pattern). Bypass: see D-UI22.</div>'
    return s+'</div></div></div></div>'
html=('<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="base.css"><style>'+css+'</style></head><body>'
  '<h1>Mic tab · v3.1 (S-UI2 fix-up, 3 Oct 2026 · decisions locked 09:06/09:09)</h1>'
  '<div class="sub">The tools column (Colour, alignment ticks, Side mics, Centre mic) leaves the Source plane and becomes a <b>Mics</b> panel in the sidebar under Listen. '
  'Top and Combined grow to the sidebar height. The Source plane spans the full width below. Colour order is Measured · User defined · Bypass. '
  'Each state shows only what acts in it. Canvas pictures are today\'s S-UI2 drawings dropped into the proposed boxes.</div>'
  +frame('M')+frame('U')+'</body></html>')
open(OUT,'w').write(html); print(OUT)
