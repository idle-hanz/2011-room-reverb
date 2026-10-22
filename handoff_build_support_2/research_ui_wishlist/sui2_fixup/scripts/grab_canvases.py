"""Element screenshots of the Mic tab canvases (ORTF) for the v3 mock."""
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:7881/'; O='/workspace/build_support_2/research_ui_wishlist/sui2_fixup/mock/src/img/'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1600,'height':1000}); pg.goto(URL); pg.wait_for_timeout(4000)
    pg.click('.view-tab[data-view=mic]'); pg.wait_for_timeout(3000)
    for sel,name in (('#micFloorCanvas','top'),('#mic3dCanvas','combined'),('#micPolarHero','hero'),('#panelListen','listen')):
        pg.locator(sel).screenshot(path=O+name+'.png')
    pg.select_option('#colour_mode','ASSUMED_TOYS'); pg.wait_for_timeout(2500)
    for cap in 'LCR': pg.locator(f'#micPolar{cap}').screenshot(path=O+f'each_{cap}.png')
    pg.locator('#micPolarHero').screenshot(path=O+'hero_ud.png')
    pg.click('.view-tab[data-view=colour]'); pg.wait_for_timeout(1500)
    pg.locator('#colourCanvas').screenshot(path=O+'analyser.png')
    pg.click('.view-tab[data-view=surfaces]'); pg.wait_for_timeout(1500)
    pg.locator('.room-net-wrap').screenshot(path=O+'roomnet.png')
    pg.locator('#absorbCanvas').screenshot(path=O+'absorb.png'); pg.locator('#eqCanvas').screenshot(path=O+'eq.png')
    b.close()
print('ok')
