"""Space tab: does left/right/shift drag or wheel change the WebGL canvas, per chip; does it stay changed?"""
import json, sys, hashlib
from playwright.sync_api import sync_playwright
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:7881/'
OUT='/workspace/build_support_2/research_ui_wishlist/sui2_fixup/'
H="()=>{const c=document.getElementById('imageCanvas');return c.toDataURL('image/png')}"
res={}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1600,'height':1000}); errs=[]
    pg.on('pageerror',lambda e: errs.append(str(e)[:200]))
    pg.goto(URL); pg.wait_for_timeout(4000)
    pg.click('.view-tab[data-view=space]'); pg.wait_for_timeout(3000)
    box=pg.locator('#imageCanvas').bounding_box(); res['canvas_box']=box
    cx,cy=box['x']+box['width']/2, box['y']+box['height']/2
    top=pg.evaluate("()=>{const c=document.getElementById('imageCanvas');const r=c.getBoundingClientRect();const e=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return e?(e.id||e.className||e.tagName):null}")
    res['element_at_canvas_centre']=top
    h=lambda: hashlib.md5(pg.evaluate(H).encode()).hexdigest()[:10]
    def drag(button='left', mods=None, dx=160, dy=60):
        if mods: pg.keyboard.down(mods)
        pg.mouse.move(cx,cy); pg.mouse.down(button=button); 
        for k in range(1,11): pg.mouse.move(cx+dx*k/10, cy+dy*k/10)
        pg.mouse.up(button=button)
        if mods: pg.keyboard.up(mods)
        pg.wait_for_timeout(400)
    for chip in ('lattice','paths','legs'):
        pg.click(f'.space-mode-chip[data-space-mode={chip}]'); pg.wait_for_timeout(2500)
        r={}; h0=h(); pg.screenshot(path=OUT+f'shots/space_{chip}_0.png')
        drag('left'); h1=h(); r['left_drag_changes']=h1!=h0
        drag('right'); h2=h(); r['right_drag_changes']=h2!=h1
        drag('left','Shift'); h3=h(); r['shift_drag_changes']=h3!=h2
        drag('left','Alt'); h4=h(); r['alt_drag_changes']=h4!=h3
        pg.mouse.move(cx,cy); pg.mouse.wheel(0,600); pg.wait_for_timeout(400); h5=h(); r['wheel_out_changes']=h5!=h4
        for k in range(40): pg.mouse.wheel(0,400); pg.wait_for_timeout(15)
        pg.wait_for_timeout(300); h6=h(); pg.mouse.wheel(0,400); pg.wait_for_timeout(300); r['wheel_out_still_changes_after_40']=h()!=h6
        pg.screenshot(path=OUT+f'shots/space_{chip}_after.png')
        # does a state change (any slider on the sidebar) reset the camera?
        drag('right'); hA=h()
        pg.evaluate("()=>{const e=document.querySelector('#sy')||document.querySelector('input[type=range]');if(e){e.value=String(Number(e.value)+0.01);e.dispatchEvent(new Event('input',{bubbles:true}));}}")
        pg.wait_for_timeout(2000); r['after_state_change_reset_to_fit']=h()==h0 if chip!='lattice' else None; r['after_state_change_changed']=h()!=hA
        pg.dblclick(f'#imageCanvas'); pg.wait_for_timeout(400); r['dblclick_changes']=h()!=hA
        res[chip]=r
    res['hint']=pg.inner_text('#imageViewHint'); res['errors']=errs
    b.close()
json.dump(res,open(OUT+'data/space_probe.json','w'),indent=1); print(json.dumps(res,indent=1))
