from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1600,'height':1000}); pg.goto('http://127.0.0.1:7881/'); pg.wait_for_timeout(3500)
    pg.click('.view-tab[data-view=surfaces]'); pg.wait_for_timeout(1200)
    print(pg.evaluate('''()=>["#surfacesBanner",".room-net-wrap","#materialChips","#surfAudition","#surfaceCards","#surfaceDetail","#absorbCanvas","#eqCanvas","#eqControls","#surfacesAdvanced","#airCard"].map(s=>{const e=document.querySelector(s);const r=e.getBoundingClientRect();return s+" "+[r.x,r.y,r.width,r.height].map(Math.round).join(",")})'''))
    print(pg.evaluate('''()=>[...document.querySelectorAll('#eqControls input,#eqControls select')].map(e=>e.id+':'+(e.getAttribute('aria-label')||''))'''))
    b.close()
