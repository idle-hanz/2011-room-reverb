"""Render once in the headless app, then grab the Colour analyser + face strip (for the m9 mock)."""
from playwright.sync_api import sync_playwright
O='/workspace/build_support_2/research_ui_wishlist/mock/src/img_sui2/'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'])
    pg=b.new_page(viewport={'width':1600,'height':1000}); pg.goto('http://127.0.0.1:7881/'); pg.wait_for_timeout(3500)
    pg.click('.view-tab[data-view=surfaces]'); pg.wait_for_timeout(800)
    pg.click('#renderBtn')
    pg.wait_for_function('()=>!/Render to see/.test(document.getElementById("colourMeta").textContent)',timeout=240000)
    pg.wait_for_timeout(1500)
    print('view after render:', pg.evaluate('()=>[...document.querySelectorAll(".view-tab.active")].map(e=>e.dataset.view)'))
    pg.click('.view-tab[data-view=colour]'); pg.wait_for_timeout(1500)
    print(pg.evaluate('()=>document.getElementById("colourMeta").textContent'))
    pg.locator('#colourCanvas').screenshot(path=O+'analyser.png'); pg.locator('#colourSparkBlock').screenshot(path=O+'spark.png')
    b.close()
