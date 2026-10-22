"""List elements that carry hidden=true but still render (CSS display overrides [hidden])."""
import json, sys
from playwright.sync_api import sync_playwright
URL=sys.argv[1]; D='/workspace/build_support_2/research_ui_wishlist/'
JS='''()=>[...document.querySelectorAll("[hidden]")].filter(e=>{const s=getComputedStyle(e);return s.display!=="none"}).map(e=>({id:e.id||null,cls:e.className&&String(e.className).slice(0,60),tag:e.tagName,display:getComputedStyle(e).display,onscreen:e.getClientRects().length>0&&!!e.offsetParent,text:(e.textContent||"").trim().slice(0,50)}))'''
out={}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1600,'height':1000}); pg.goto(URL); pg.wait_for_timeout(4000)
    for setup in ('ortf','binaural','mono_c'):
        pg.click('.view-tab[data-view=mic]'); pg.wait_for_timeout(400)
        pg.select_option('#mic_setup',setup); pg.wait_for_timeout(1200)
        for t in ['edit','source','mic','mix','lattice','paths','colour','surfaces','polar']:
            pg.click(f'.view-tab[data-view={t}]'); pg.wait_for_timeout(700)
            out[f'{setup}|{t}']=[x for x in pg.evaluate(JS) if x['onscreen']]
    b.close()
json.dump(out,open(D+'data/hidden_audit.json','w'),indent=1)
seen={}
for k,v in out.items():
    for x in v: seen.setdefault((x['id'],x['tag'],x['display'],x['text'][:30]),[]).append(k)
for k,v in seen.items(): print(k, len(v), v[:4])
