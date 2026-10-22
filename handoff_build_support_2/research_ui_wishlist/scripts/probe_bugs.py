"""Click-test bugs 2, 5, 8 (+1 source radiation colours) on the 18:15 snapshot app."""
import json, sys
from playwright.sync_api import sync_playwright
URL=sys.argv[1]; D='/workspace/build_support_2/research_ui_wishlist/'; SH=D+'shots/'
out={}
polar_bodies=[]
def capsule_state(pg):
    return pg.evaluate('''()=>["l","c","r"].map(c=>{const f=document.getElementById("family_"+c),p=document.getElementById("polar_"+c);
      return {cap:c,family:f.value,fam_disabled:f.disabled,polar:p.value,polar_disabled:p.disabled,label:(document.getElementById("polar_"+c+"_out")||{}).textContent}})''')
def canvas_hash(pg, cid):
    return pg.evaluate(f'''()=>{{const c=document.getElementById("{cid}");if(!c)return null;const d=c.getContext("2d").getImageData(0,0,c.width,c.height).data;let h=0;for(let i=0;i<d.length;i+=7)h=(h*31+d[i])>>>0;return h}}''')
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':1600,'height':1100})
    pg.on('request',lambda r: polar_bodies.append(json.loads(r.post_data)) if r.url.endswith('/api/polar') and r.post_data else None)
    pg.goto(URL); pg.wait_for_timeout(4000)
    # ---------- Bug 2 ----------
    pg.click('.view-tab[data-view=mic]'); pg.wait_for_timeout(1500)
    pg.evaluate('()=>{const d=[...document.querySelectorAll("details")].find(x=>x.querySelector("#micPolarL"));if(d)d.open=true}')
    pg.wait_for_timeout(800)
    out['b2_default_capsules']=capsule_state(pg)
    out['b2_colour_mode']=pg.eval_on_selector('#colour_mode','e=>e.value')
    for setup in ('xy_90','ms_classic'):
        pg.select_option('#mic_setup',setup); pg.wait_for_timeout(1800)
        out[f'b2_{setup}_capsules']=capsule_state(pg)
        last=polar_bodies[-1] if polar_bodies else {}
        out[f'b2_{setup}_polar_body']={k:last.get(k) for k in ('mic_setup','yaw_l_deg','yaw_r_deg','family_l','polar_l','family_c','polar_c','pattern_l','mic_preset_l','colour_mode')}
        el=pg.query_selector('#micPolarL').evaluate_handle('e=>e.closest("details")')
        pg.query_selector('#micPolarL').scroll_into_view_if_needed()
        pg.screenshot(path=SH+f'b2_{setup}_mic.png',full_page=True)
    # Bypass mode: do controls come alive?
    pg.select_option('#mic_setup','xy_90'); pg.wait_for_timeout(1000)
    pg.select_option('#colour_mode','BYPASS'); pg.wait_for_timeout(1500)
    out['b2_bypass_capsules']=capsule_state(pg)
    h0=canvas_hash(pg,'micPolarL')
    n0=len(polar_bodies)
    pg.eval_on_selector('#polar_l','e=>{e.value=0.9;e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}))}')
    pg.wait_for_timeout(1500)
    out['b2_bypass_after_polar_l_0.9']={'capsules':capsule_state(pg),'canvas_changed':canvas_hash(pg,'micPolarL')!=h0,'new_polar_requests':len(polar_bodies)-n0,
        'last_body_polar_l':polar_bodies[-1].get('polar_l') if polar_bodies else None,'last_body_pattern_l':polar_bodies[-1].get('pattern_l') if polar_bodies else None}
    pg.query_selector('#micPolarL').scroll_into_view_if_needed()
    pg.screenshot(path=SH+'b2_xy90_bypass_polar09.png',full_page=True)
    pg.select_option('#colour_mode','MEASURED_SHELF'); pg.wait_for_timeout(800)
    pg.select_option('#mic_setup','ortf'); pg.wait_for_timeout(1500)
    # ---------- Bug 8 ----------
    for my in ('1.5','3.0','6.0'):
        pg.eval_on_selector('#my',f'e=>{{e.value={my};e.dispatchEvent(new Event("input",{{bubbles:true}}));e.dispatchEvent(new Event("change",{{bubbles:true}}))}}')
        pg.wait_for_timeout(2000)
        out[f'b8_my{my}']={'meta':pg.eval_on_selector('#micHeroMeta','e=>e.textContent'),'sy':pg.eval_on_selector('#sy','e=>e.value'),
            'link_heights':pg.evaluate('()=>{const e=document.getElementById("link_heights");return e?e.checked:null}')}
        pg.evaluate('()=>window.scrollTo(0,0)')
        pg.screenshot(path=SH+f'b8_mic_my{my}.png')
        pg.click('.view-tab[data-view=polar]'); pg.wait_for_timeout(2500)
        pg.screenshot(path=SH+f'b8_polar3d_my{my}.png')
        pg.click('.view-tab[data-view=mic]'); pg.wait_for_timeout(1500)
    pg.eval_on_selector('#my','e=>{e.value=1.5;e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}))}')
    # ---------- Bug 5 ----------
    pg.click('.view-tab[data-view=mix]'); pg.wait_for_timeout(1200)
    res=[]
    for kid in ('pan_c','trim_l','trim_direct'):
        el=pg.query_selector('#'+kid); bb=el.bounding_box()
        rng=pg.eval_on_selector('#'+kid,'e=>[e.min,e.max,e.step,e.value]')
        cx,cy=bb['x']+bb['width']/2,bb['y']+bb['height']/2
        r={'id':kid,'box':[round(bb['width']),round(bb['height'])],'range':rng}
        # vertical drag up 60 px (what a knob user expects)
        pg.mouse.move(cx,cy); pg.mouse.down(); pg.mouse.move(cx,cy-60,steps=10); pg.mouse.up(); pg.wait_for_timeout(200)
        r['after_click_centre_then_drag_up60']=pg.eval_on_selector('#'+kid,'e=>e.value')
        # click left edge (+3px)
        pg.mouse.click(bb['x']+3,cy); pg.wait_for_timeout(200)
        r['after_click_left_edge']=pg.eval_on_selector('#'+kid,'e=>e.value')
        # drag horizontally 5 px from centre
        pg.mouse.move(cx,cy); pg.mouse.down(); pg.mouse.move(cx+5,cy,steps=5); pg.mouse.up(); pg.wait_for_timeout(200)
        r['after_click_centre_drag_right5']=pg.eval_on_selector('#'+kid,'e=>e.value')
        pg.mouse.move(cx,cy); pg.mouse.down(); pg.mouse.move(cx+17,cy,steps=5); pg.mouse.up(); pg.wait_for_timeout(200)
        r['after_click_centre_drag_right17']=pg.eval_on_selector('#'+kid,'e=>e.value')
        # wheel
        pg.mouse.move(cx,cy); pg.mouse.wheel(0,-100); pg.wait_for_timeout(200)
        r['after_wheel']=pg.eval_on_selector('#'+kid,'e=>e.value')
        # dblclick reset?
        pg.mouse.dblclick(cx+10,cy); pg.wait_for_timeout(200)
        r['after_dblclick']=pg.eval_on_selector('#'+kid,'e=>e.value')
        res.append(r)
    out['b5']=res
    pg.screenshot(path=SH+'b5_mix_after.png')
    # ---------- Bug 1 source radiation ----------
    pg.click('.view-tab[data-view=source]'); pg.wait_for_timeout(1500)
    try:
        opts=pg.eval_on_selector('#sourcePreset','e=>[...e.options].map(o=>o.value)')
        out['b1_source_presets']=opts
        v=[o for o in opts if 'violin' in o] or opts[1:2]
        pg.select_option('#sourcePreset',v[0]); pg.wait_for_timeout(2500)
    except Exception as e: out['b1_err']=str(e)
    pg.screenshot(path=SH+'b1_source_violin.png',full_page=True)
    json.dump(out,open(D+'data/probe_bugs.json','w'),indent=1)
    b.close()
print(json.dumps(out,indent=1)[:6000])
