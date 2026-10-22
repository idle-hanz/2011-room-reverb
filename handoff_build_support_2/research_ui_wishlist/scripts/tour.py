"""Tab tour of the 18:15 snapshot app: screenshot every tab (ORTF default and binaural), record visible sidebar panels + controls."""
import json, sys
from playwright.sync_api import sync_playwright
URL=sys.argv[1]; D='/workspace/build_support_2/research_ui_wishlist/'; SH=D+'shots/'
TABS=['edit','source','mic','mix','lattice','paths','colour','surfaces','polar']
VIS='''()=>{const vis=e=>!!(e&&e.offsetParent!==null&&getComputedStyle(e).visibility!=="hidden");
 const panels=[...document.querySelectorAll('.sidebar > .panel, .sidebar > details')].filter(vis).map(e=>e.id);
 const ctrls=[...document.querySelectorAll('main input, main select, main button')].filter(vis).map(e=>e.id||e.dataset.view||e.dataset.place||e.dataset.n||e.dataset.material||e.dataset.solo||e.dataset.mute||e.dataset.srcFreq||e.textContent.trim().slice(0,24)||e.type);
 return {panels, n_controls:ctrls.length, controls:ctrls}}'''
log={'console':[], 'tabs':{}}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1600,'height':1000})
    pg.on('console',lambda m: log['console'].append((m.type,m.text[:200])) if m.type=='error' else None)
    pg.on('pageerror',lambda e: log['console'].append(('pageerror',str(e)[:300])))
    pg.goto(URL); pg.wait_for_timeout(4000)
    for setup in ('ortf','binaural'):
        if setup=='binaural':
            pg.click('.view-tab[data-view=mic]'); pg.wait_for_timeout(500)
            pg.select_option('#mic_setup','binaural'); pg.wait_for_timeout(1500)
        for t in TABS:
            pg.click(f'.view-tab[data-view={t}]'); pg.wait_for_timeout(1800)
            pg.screenshot(path=SH+f'tour_{setup}_{t}.png', full_page=True)
            log['tabs'][f'{setup}|{t}']=pg.evaluate(VIS)
    json.dump(log,open(D+'data/tour.json','w'),indent=1)
    b.close()
print('ok', len(log['console']))
