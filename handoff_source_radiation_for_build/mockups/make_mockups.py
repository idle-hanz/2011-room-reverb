"""Generate UI MOCKUPS (HTML+inline SVG -> PNG via headless Chrome). Polar/balloon shapes use real fitted presets."""
import json, math, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "source_fitter"))
from source_fitter import model as M

P = lambda pid: json.load(open(os.path.join(ROOT, "source_fitter", "presets", pid + ".json")))
CSS = """
body{margin:0;background:#0d1016;font-family:Inter,Segoe UI,system-ui,sans-serif;color:#dfe6f0}
.top{height:56px;display:flex;align-items:center;padding:0 22px;border-bottom:1px solid #1f2632;background:#10141c}
.brand{font-weight:700;font-size:16px;margin-right:28px}.brand small{display:block;font-weight:400;color:#7d8aa0;font-size:11px}
.tab{padding:7px 13px;margin-right:4px;border-radius:8px;font-size:13px;color:#9fb0c8}
.tab.on{background:#1d2735;color:#fff;box-shadow:inset 0 -2px 0 #ffb347}
.tab.new{outline:1px dashed #ffb347}
.btn{margin-left:auto;padding:7px 14px;border-radius:8px;background:#1b2330;font-size:13px}.btn.p{margin-left:8px;background:#3b82f6;color:#fff}
.wrap{display:grid;gap:14px;padding:14px}
.card{background:#131924;border:1px solid #202a39;border-radius:14px;padding:12px 14px;position:relative}
.card h3{margin:0 0 8px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#8ea0bb;font-weight:600}
.chip{display:inline-block;padding:4px 10px;border-radius:999px;background:#1b2433;font-size:12px;margin:0 4px 6px 0;color:#b7c4d8}
.chip.on{background:#ffb347;color:#1a1206;font-weight:600}
.row{display:flex;align-items:center;gap:10px;margin:8px 0;font-size:13px}
.lbl{width:78px;color:#8ea0bb;font-size:12px}
.slider{flex:1;height:4px;background:#263041;border-radius:3px;position:relative}
.slider i{position:absolute;top:-6px;width:16px;height:16px;border-radius:50%;background:#ffb347;box-shadow:0 0 0 4px #ffb34733}
.val{width:64px;text-align:right;font-variant-numeric:tabular-nums;color:#fff}
.sel{flex:1;padding:8px 10px;border-radius:9px;background:#0f141d;border:1px solid #2a3547;font-size:13px}
.note{font-size:11px;color:#7d8aa0;line-height:1.45}
.adv{border-top:1px solid #222c3b;margin-top:10px;padding-top:8px;font-size:12px;color:#8ea0bb}
.mock{position:fixed;right:18px;bottom:12px;font-size:12px;color:#ff6b6b;border:1px solid #ff6b6b;padding:4px 10px;border-radius:8px;background:#1a0f12}
.callout{position:absolute;font-size:11px;color:#1a1206;background:#7ee0c3;border-radius:7px;padding:3px 7px;white-space:nowrap}
"""
TABS = ["Floor · Side · 3D", "Source", "Mic", "Mix", "Lattice", "Paths", "Colour", "Surfaces", "Polar 3D"]


def topbar(active):
    t = "".join(f'<span class="tab{" on" if x == active else ""}{" new" if x == "Source" else ""}">{x}</span>' for x in TABS)
    return f'<div class="top"><div class="brand">2011 Room Reverb<small>Place on Floor · orbit in 3D · sculpt the early field</small></div>{t}<span class="btn">Play live</span><span class="btn p">Render</span></div>'


def polar_path(preset, f, cx, cy, R, plane="h", yaw=0.0, rng=30.0, mode="polar"):
    ang = np.radians(np.arange(0, 361, 3))
    if plane == "h":
        d = np.stack([np.cos(ang), np.sin(ang), 0 * ang], -1)
    else:
        d = np.stack([np.cos(ang), 0 * ang, np.sin(ang)], -1)
    r = M.relative_db(preset["params"], d, np.array([float(f)]))[:, 0]
    rr = R * np.clip(1 + r / rng, 0.03, 1.0)
    pts = []
    for a, q in zip(ang, rr):
        if plane == "h" and yaw is not None and mode == "floor":
            # floor plan: +x right, +z down; yaw 0 = +z, + toward +x; local +angle = source-left = +x side
            th = math.radians(yaw) + a
            pts.append(f"{cx + q * math.sin(th):.1f},{cy + q * math.cos(th):.1f}")
        elif mode == "side":
            th = math.radians(yaw) + a   # yaw arg = pitch here; +z right, up = -screen y
            pts.append(f"{cx + q * math.cos(th):.1f},{cy - q * math.sin(th):.1f}")
        else:  # plain polar plot, front = up, source-left = screen left
            pts.append(f"{cx - q * math.sin(a):.1f},{cy - q * math.cos(a):.1f}")
    return "M" + " L".join(pts) + " Z"


def balloon_svg(preset, f, cx, cy, R):
    # simple orthographic balloon: wireframe of meridians/parallels scaled by gain
    out = []
    az_view, el_view = math.radians(35), math.radians(20)
    def proj(v):
        x, y, z = v
        x1 = x * math.cos(az_view) - y * math.sin(az_view); y1 = x * math.sin(az_view) + y * math.cos(az_view)
        z2 = z * math.cos(el_view) - x1 * math.sin(el_view)
        return cx + y1 * R, cy - z2 * R
    def rad(d):
        r = M.relative_db(preset["params"], d, np.array([float(f)]))[:, 0]
        return np.clip(1 + r / 30.0, 0.03, 1)
    for el in np.radians(np.arange(-75, 76, 15)):
        az = np.radians(np.arange(0, 361, 6)); d = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el) + 0 * az], -1)
        rr = rad(d); p = [proj(v * q) for v, q in zip(d, rr)]
        out.append('<path d="M' + " L".join(f"{a:.1f},{b:.1f}" for a, b in p) + '" fill="none" stroke="#ffb34755" stroke-width="1"/>')
    for az in np.radians(np.arange(0, 360, 20)):
        el = np.radians(np.arange(-90, 91, 6)); d = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1)
        rr = rad(d); p = [proj(v * q) for v, q in zip(d, rr)]
        out.append('<path d="M' + " L".join(f"{a:.1f},{b:.1f}" for a, b in p) + '" fill="none" stroke="#7ec8ff55" stroke-width="1"/>')
    ax = proj((1.15, 0, 0))
    out.append(f'<line x1="{cx}" y1="{cy}" x2="{ax[0]:.1f}" y2="{ax[1]:.1f}" stroke="#ffb347" stroke-width="2.5" marker-end="url(#ar)"/>')
    return "".join(out)


DEFS = '<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="5" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#ffb347"/></marker><marker id="arg" markerWidth="8" markerHeight="8" refX="5" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#7ee0c3"/></marker></defs>'


def source_desk():
    tp = P("trumpet"); yaw = 20.0  # 20 deg off the mic line (mic straight down at +z)
    # floor plan 6 x 8 m -> 300 x 400 px
    sx, sy, s = 60, 40, 50.0
    src = (sx + 3.0 * s, sy + 2.5 * s); mic = (sx + 3.0 * s, sy + 5.5 * s)
    fp = f'''<svg width="420" height="470">{DEFS}
<rect x="{sx}" y="{sy}" width="{6*s}" height="{8*s}" rx="6" fill="#0f141d" stroke="#2f3b50"/>
<text x="{sx}" y="{sy-12}" fill="#8ea0bb" font-size="11">TOP · 6 × 8 m · drag dot = move · drag ring handle = yaw</text>
<path d="{polar_path(tp, 4000, *src, 120, 'h', yaw, mode='floor')}" fill="#ffb34722" stroke="#ffb347" stroke-width="1.5"/>
<path d="{polar_path(tp, 500, *src, 120, 'h', yaw, mode='floor')}" fill="none" stroke="#7ec8ff" stroke-width="1" stroke-dasharray="4 3"/>
<circle cx="{src[0]}" cy="{src[1]}" r="{0.06*s*4:.1f}" fill="none" stroke="#ffffff55" stroke-dasharray="2 2"/>
<circle cx="{src[0]}" cy="{src[1]}" r="46" fill="none" stroke="#ffb34755" stroke-width="1.5" stroke-dasharray="3 3"/>
<circle cx="{src[0]}" cy="{src[1]}" r="9" fill="#ffb347"/>
<line x1="{src[0]}" y1="{src[1]}" x2="{src[0]+46*math.sin(math.radians(yaw)):.1f}" y2="{src[1]+46*math.cos(math.radians(yaw)):.1f}" stroke="#ffb347" stroke-width="3" marker-end="url(#ar)"/>
<circle cx="{src[0]+46*math.sin(math.radians(yaw)):.1f}" cy="{src[1]+46*math.cos(math.radians(yaw)):.1f}" r="8" fill="#10141c" stroke="#ffb347" stroke-width="2.5"/>
<g fill="#7ee0c3"><circle cx="{mic[0]-7}" cy="{mic[1]}" r="5"/><circle cx="{mic[0]}" cy="{mic[1]+6}" r="5"/><circle cx="{mic[0]+7}" cy="{mic[1]}" r="5"/></g>
<line x1="{src[0]}" y1="{src[1]}" x2="{mic[0]}" y2="{mic[1]}" stroke="#7ee0c355" stroke-dasharray="3 4"/>
<text x="{mic[0]+14}" y="{mic[1]+4}" fill="#7ee0c3" font-size="11">L C R</text>
<text x="{src[0]+56}" y="{src[1]-40}" fill="#ffb347" font-size="12">yaw {yaw:.0f}° off mic</text>
<text x="{sx+4}" y="{sy+8*s+20}" fill="#8ea0bb" font-size="11">— 4 kHz  - - 500 Hz   (radiation cut in room, to scale of level)</text>
</svg>'''
    # pitch side view
    sv = f'''<svg width="420" height="200">{DEFS}
<rect x="30" y="30" width="{8*42}" height="{3*42}" rx="6" fill="#0f141d" stroke="#2f3b50"/>
<text x="30" y="20" fill="#8ea0bb" font-size="11">SIDE · length × height · drag ring handle = pitch</text>
<path d="{polar_path(tp, 4000, 30+2.5*42, 30+1.5*42, 70, 'v', -8, mode='side')}" fill="#ffb34722" stroke="#ffb347" stroke-width="1.3"/>
<circle cx="{30+2.5*42}" cy="{30+1.5*42}" r="8" fill="#ffb347"/>
<line x1="{30+2.5*42}" y1="{30+1.5*42}" x2="{30+2.5*42+40*math.cos(math.radians(-8)):.1f}" y2="{30+1.5*42-40*math.sin(math.radians(-8)):.1f}" stroke="#ffb347" stroke-width="3" marker-end="url(#ar)"/>
<circle cx="{30+5.5*42}" cy="{30+1.5*42}" r="5" fill="#7ee0c3"/>
<text x="{30+2.5*42+48}" y="{30+1.5*42+22}" fill="#ffb347" font-size="12">pitch −8°</text>
</svg>'''
    pol = f'''<svg width="330" height="300">
<g transform="translate(165,150)">{''.join(f'<circle r="{120*(1-k/30):.0f}" fill="none" stroke="#263041"/>' for k in (0,10,20))}
<line x1="-125" y1="0" x2="125" y2="0" stroke="#263041"/><line x1="0" y1="-125" x2="0" y2="125" stroke="#263041"/></g>
{''.join(f'<path d="{polar_path(tp, f, 165, 150, 120, "h")}" fill="none" stroke="{c}" stroke-width="1.6"/>' for f, c in ((250,'#4c6ef5'),(1000,'#7ec8ff'),(4000,'#ffb347'),(8000,'#ff6b6b')))}
<text x="10" y="290" fill="#8ea0bb" font-size="11">0/−10/−20 dB · front = up · 250 1k 4k 8k</text></svg>'''
    di = tp["di_db"]; fk = sorted(di["model"].items(), key=lambda kv: float(kv[0])) if isinstance(di, dict) and "model" in di else []
    bal = f'<svg width="330" height="300">{DEFS}{balloon_svg(tp, 4000, 150, 150, 140)}<text x="10" y="290" fill="#8ea0bb" font-size="11">3D balloon · orbit only · 4 kHz</text></svg>'
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{topbar("Source")}
<div class="wrap" style="grid-template-columns:300px 440px 1fr">
 <div class="card"><h3>Sources in this room</h3>
  <span class="chip on">● Trumpet — this track</span><span class="chip">● Vox (linked)</span><span class="chip">● Gtr cab (linked)</span><span class="chip">+ Link track</span>
  <div class="row"><span class="lbl">Radiation</span><span class="sel">Trumpet — TU Berlin ▾</span></div>
  <div class="note">Measured fit · hold-out RMSE shown in tooltip · <b style="color:#7ee0c3">VERIFIED data</b></div>
  <div class="row"><span class="lbl">Yaw</span><div class="slider"><i style="left:55%"></i></div><span class="val">20°</span></div>
  <div class="row"><span class="lbl">Pitch</span><div class="slider"><i style="left:45%"></i></div><span class="val">−8°</span></div>
  <div class="row"><span class="lbl">Size</span><div class="slider"><i style="left:30%"></i></div><span class="val">6 cm</span></div>
  <div class="note">Size moves the beaming onset (≈ c / 2πa = 900 Hz). Circle on the dot shows radius.</div>
  <div class="row"><span class="chip">⟲ Face mic</span><span class="chip">↺ Face away</span><span class="chip">○ Omni (bypass)</span></div>
  <div class="adv">▸ Advanced (Structure)<div class="note" style="margin-top:6px">Aim offset az/el · Tail follow α (0) · Size jitter (off) · Emission points M (1) · Up/down asym.</div></div>
 </div>
 <div class="card"><h3>Place &amp; face</h3>{fp}{sv}</div>
 <div style="display:grid;grid-template-rows:auto auto;gap:14px">
  <div class="card"><h3>Radiation</h3>
   <span class="chip">250</span><span class="chip">500</span><span class="chip">1k</span><span class="chip">2k</span><span class="chip on">4k</span><span class="chip">8k</span><span class="chip">Horizontal ▾</span>
   <div style="display:flex">{pol}{bal}</div></div>
  <div class="card"><h3>What the room hears</h3>
   <div class="note">Direct to mic C: <b style="color:#fff">−3.1 dB @ 4 kHz</b> vs on-axis · Tail (diffuse power): <b style="color:#fff">{tp["diffuse_inject"]["shelf_gain_db"]:.0f} dB shelf above {tp["diffuse_inject"]["shelf_f0"]/1000:.1f} kHz</b> — does not change with yaw.</div>
   <div class="note">Hover an image in Paths to see its emission angle and radiation colour.</div></div>
 </div>
</div><div class="mock">MOCKUP — not implemented · shapes from fitted trumpet preset</div></body></html>'''
    return html


def floor_tab():
    tp = P("talking_head"); cab = P("cab_1x12_closed")
    sx, sy, s = 70, 70, 70.0
    def src(x, z, pr, yaw, col, name, a_cm):
        cx, cy = sx + x * s, sy + z * s
        hx, hy = cx + 30 * math.sin(math.radians(yaw)), cy + 30 * math.cos(math.radians(yaw))
        return f'''<path d="{polar_path(pr, 2000, cx, cy, 85, 'h', yaw, mode='floor')}" fill="{col}18" stroke="{col}88"/>
<circle cx="{cx}" cy="{cy}" r="{max(a_cm/100*s,4):.1f}" fill="none" stroke="#ffffff44" stroke-dasharray="2 2"/>
<circle cx="{cx}" cy="{cy}" r="9" fill="{col}"/><line x1="{cx}" y1="{cy}" x2="{hx:.1f}" y2="{hy:.1f}" stroke="{col}" stroke-width="3" marker-end="url(#ar)"/>
<circle cx="{hx:.1f}" cy="{hy:.1f}" r="7" fill="#10141c" stroke="{col}" stroke-width="2"/><text x="{cx+14}" y="{cy+22}" fill="{col}" font-size="12">{name}</text>'''
    svg = f'''<svg width="960" height="690">{DEFS}
<rect x="{sx}" y="{sy}" width="{6*s}" height="{8*s}" rx="8" fill="#0f141d" stroke="#2f3b50"/>
<text x="{sx}" y="{sy-20}" fill="#8ea0bb" font-size="12">FLOOR · existing tab · new: facing handle on each source dot, faint 2 kHz radiation cut</text>
{src(2.0, 2.2, tp, 25, "#ffb347", "Vox (this track)", 9)}
{src(4.4, 1.6, cab, -30, "#c792ea", "Gtr cab (linked)", 13)}
<g fill="#7ee0c3"><circle cx="{sx+2.85*s}" cy="{sy+5.5*s}" r="6"/><circle cx="{sx+3*s}" cy="{sy+5.6*s}" r="6"/><circle cx="{sx+3.15*s}" cy="{sy+5.5*s}" r="6"/></g>
<text x="{sx+3.3*s}" y="{sy+5.55*s}" fill="#7ee0c3" font-size="12">mic L C R</text>
<g transform="translate(560,90)">
<rect width="360" height="270" rx="12" fill="#131924" stroke="#202a39"/>
<text x="16" y="28" fill="#8ea0bb" font-size="12" letter-spacing="1">INTERACTION</text>
<text x="16" y="56" fill="#dfe6f0" font-size="13">• drag dot → move (x, z) as today</text>
<text x="16" y="82" fill="#dfe6f0" font-size="13">• drag hollow ring handle → yaw (snap 15° w/ Shift)</text>
<text x="16" y="108" fill="#dfe6f0" font-size="13">• double-click handle → face mic</text>
<text x="16" y="134" fill="#dfe6f0" font-size="13">• Alt-drag → size radius (dashed circle)</text>
<text x="16" y="160" fill="#dfe6f0" font-size="13">• hover → tooltip: preset, yaw, DI@2k</text>
<text x="16" y="186" fill="#dfe6f0" font-size="13">• omni preset → no handle, no lobe</text>
<text x="16" y="212" fill="#dfe6f0" font-size="13">• linked sources: other tracks' colour,</text>
<text x="30" y="232" fill="#dfe6f0" font-size="13">editable only from their own instance</text>
<text x="16" y="256" fill="#8ea0bb" font-size="11">(or unlock in Advanced)</text></g>
<g transform="translate(560,390)"><rect width="360" height="160" rx="12" fill="#131924" stroke="#202a39"/>
<text x="16" y="28" fill="#8ea0bb" font-size="12" letter-spacing="1">SIDE VIEW (same tab)</text>
<rect x="16" y="44" width="328" height="90" rx="6" fill="#0f141d" stroke="#2f3b50"/>
<circle cx="110" cy="100" r="8" fill="#ffb347"/><line x1="110" y1="100" x2="146" y2="92" stroke="#ffb347" stroke-width="3" marker-end="url(#ar)"/>
<circle cx="148" cy="92" r="6" fill="#10141c" stroke="#ffb347" stroke-width="2"/>
<text x="160" y="84" fill="#ffb347" font-size="12">drag handle = pitch</text>
<circle cx="250" cy="98" r="5" fill="#7ee0c3"/></g>
</svg>'''
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{topbar("Floor · Side · 3D")}<div style="padding:10px 16px">{svg}</div><div class="mock">MOCKUP — not implemented</div></body></html>'


def shot(html, name, w, h):
    p = os.path.join(HERE, name + ".html"); open(p, "w").write(html)
    png = os.path.join(HERE, name + ".png")
    subprocess.run(["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={w},{h}", f"--screenshot={png}", "file://" + p], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    print(png, os.path.exists(png))


if __name__ == "__main__":
    shot(source_desk(), "mockup_source_desk", 1480, 900)
    shot(floor_tab(), "mockup_floor_facing", 1000, 760)
