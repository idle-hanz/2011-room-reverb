"""Space: is the user's orbit kept (a) with no action for 6 s, (b) after a sidebar state change (refetch -> setData -> fitCamera)?"""
import json, sys, hashlib
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:7881/'; OUT='/workspace/build_support_2/research_ui_wishlist/sui2_fixup/'
H="()=>document.getElementById('imageCanvas').toDataURL('image/png')"
CHG="(v)=>{const e=document.getElementById('sy');e.value=String(v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}"
res={}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1600,'height':1000}); pg.goto(URL); pg.wait_for_timeout(4000)
    pg.click('.view-tab[data-view=space]'); pg.wait_for_timeout(3000)
    box=pg.locator('#imageCanvas').bounding_box(); cx,cy=box['x']+box['width']/2, box['y']+box['height']/2
    h=lambda: hashlib.md5(pg.evaluate(H).encode()).hexdigest()[:10]
    def rdrag():
        pg.mouse.move(cx,cy); pg.mouse.down(button='right')
        for k in range(1,11): pg.mouse.move(cx+16*k, cy+6*k)
        pg.mouse.up(button='right'); pg.wait_for_timeout(400)
    for chip in ('lattice','paths'):
        pg.click(f'.space-mode-chip[data-space-mode={chip}]'); pg.wait_for_timeout(2500)
        r={}
        pg.evaluate(CHG,1.30); pg.wait_for_timeout(2500); fitA=h()          # fitted view at sy=1.30
        rdrag(); d=h(); r['orbit_changed']=d!=fitA
        pg.wait_for_timeout(6000); r['orbit_kept_6s_idle']=h()==d
        pg.evaluate(CHG,1.20); pg.wait_for_timeout(2500); fitB_after_orbit=h()
        pg.evaluate(CHG,1.30); pg.wait_for_timeout(2500); r['state_change_resets_camera_to_fit']=h()==fitA
        res[chip]=r
    b.close()
json.dump(res,open(OUT+'data/space_reset_probe.json','w'),indent=1); print(res)
