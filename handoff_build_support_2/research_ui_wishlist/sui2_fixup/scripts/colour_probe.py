"""Colour vs Surfaces tab after S-UI2: visible panels/controls and sizes."""
import json
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:7881/'; OUT='/workspace/build_support_2/research_ui_wishlist/sui2_fixup/'
Q='''()=>{const vis=e=>!!(e&&e.offsetParent!==null&&getComputedStyle(e).visibility!=="hidden");
const r=e=>{const b=e.getBoundingClientRect();return [Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)]};
return {tabs:[...document.querySelectorAll('.view-tab')].map(e=>e.textContent.trim()),
 stagePanels:[...document.querySelectorAll('.stage .panel')].filter(vis).map(e=>[e.id||e.className,...r(e)]),
 sidebarPanels:[...document.querySelectorAll('.sidebar > .panel, .sidebar > details')].filter(vis).map(e=>[e.id,...r(e)]),
 controls:[...document.querySelectorAll('.stage input, .stage select, .stage button')].filter(vis).map(e=>e.id||e.textContent.trim().slice(0,20)).slice(0,80)}}'''
res={}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1600,'height':1000}); pg.goto(URL); pg.wait_for_timeout(4000)
    for t in ('surfaces','colour'):
        pg.click(f'.view-tab[data-view={t}]'); pg.wait_for_timeout(1500)
        res[t]=pg.evaluate(Q); pg.screenshot(path=OUT+f'shots/tab_{t}.png',full_page=True)
    b.close()
json.dump(res,open(OUT+'data/colour_probe.json','w'),indent=1)
for t,v in res.items(): print(t, v['stagePanels'], v['sidebarPanels'], len(v['controls']), v['controls'][:40])
print(res['colour']['tabs'])
