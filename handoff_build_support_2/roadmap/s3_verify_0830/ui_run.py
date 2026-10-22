import json, sys, time, re
from playwright.sync_api import sync_playwright
URL=sys.argv[1]; TAG=sys.argv[2]; FULL=len(sys.argv)<4
SH='/workspace/build_support_2/roadmap/s3_verify_0830/shots/'
log={'console':[], 'posts':[], 'steps':{}}
def snap(page,name): page.screenshot(path=SH+f'{TAG}_{name}.png'); log['steps'].setdefault('shots',[]).append(SH+f'{TAG}_{name}.png')
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'])
    page=b.new_page(viewport={'width':1600,'height':1000})
    page.on('console', lambda m: log['console'].append((m.type, m.text[:300])) if m.type in ('error','warning') else None)
    page.on('pageerror', lambda e: log['console'].append(('pageerror', str(e)[:300])))
    def onreq(r):
        if r.method=='POST' and '/api/' in r.url:
            try: body=r.post_data_json
            except Exception: body=None
            log['posts'].append({'url':r.url.split('/api/')[1],'t':round(time.time(),2),'body':body})
    page.on('request', onreq)
    resp={}
    def onresp(r):
        if '/api/source_preview' in r.url:
            try: resp['preview']=r.json()
            except Exception: pass
    page.on('response', onresp)
    page.goto(URL); page.wait_for_timeout(3500)
    log['steps']['first_live_params']=next((x['body'] for x in log['posts'] if x['url'].startswith('live_params')), None)
    log['steps']['tabs']=page.eval_on_selector_all('.view-tab', 'els=>els.map(e=>e.textContent.trim())')
    snap(page,'01_floor_default')
    if not FULL:
        json.dump(log, open(f'/workspace/build_support_2/work/s3_0830/ui_{TAG}.json','w'), indent=1, default=str); b.close(); sys.exit()
    vis_js='''()=>{const vis=e=>!!(e && e.offsetParent!==null && getComputedStyle(e).visibility!=="hidden");
      const panels=[...document.querySelectorAll('.sidebar .panel')].filter(vis).map(e=>e.id||e.className);
      const had=vis(document.getElementById('hadamardBlock')); const mix=vis(document.getElementById('panelMix'));
      const adv=document.getElementById('panelAdvanced'); return {panels, hadamard_visible:had, mix_visible:mix, advanced_open: adv? (adv.querySelector('details')||{}).open:null}}'''
    side={}
    for tab in page.query_selector_all('.view-tab'):
        v=tab.get_attribute('data-view'); tab.click(); page.wait_for_timeout(900)
        side[v]=page.evaluate(vis_js); snap(page,f'02_tab_{v}')
    log['steps']['sidebar_by_tab']=side
    # Source tab
    page.click('.view-tab[data-view=source]'); page.wait_for_timeout(1200)
    def ui():
        return page.evaluate('''()=>({preset:document.getElementById('sourcePreset').value, yaw:document.getElementById('sourceYawNum').value,
          pitch:document.getElementById('sourcePitchNum').value, off:(document.getElementById('sourceOffMic')||{}).textContent,
          hear:(document.getElementById('sourceHear')||{}).textContent, aim:(document.getElementById('sourceAim')||{}).textContent,
          chipB_hidden:document.getElementById('sourceChipB').hidden})''')
    log['steps']['source_default']=ui(); snap(page,'03_source_default_omni')
    opts=page.eval_on_selector_all('#sourcePreset option','els=>els.map(e=>e.value)'); log['steps']['n_presets']=len(opts)
    page.select_option('#sourcePreset','violin_byu'); page.wait_for_timeout(1500)
    log['steps']['after_preset']=ui(); log['steps']['preview_after_preset']={k:resp.get('preview',{}).get(k) for k in ('yaw','pitch','yaw_to_face','pitch_to_face','off_mic_deg','direct_db')}
    snap(page,'04_preset_violin_autoface')
    # find ring on srcFloorCanvas by cursor scan
    c=page.query_selector('#srcFloorCanvas'); bb=c.bounding_box(); log['steps']['canvas_box']=bb
    ring=None
    for yy in range(0,int(bb['height']),5):
        for xx in range(0,int(bb['width']),5):
            page.mouse.move(bb['x']+xx, bb['y']+yy)
            if page.evaluate("document.getElementById('srcFloorCanvas').style.cursor")=='all-scroll': ring=(bb['x']+xx,bb['y']+yy); break
        if ring: break
    log['steps']['ring_found_at']=ring
    if ring:
        snap(page,'05_ring_hover')
        # drag ring 90deg around: estimate dot = ring is RING_PX away; just drag to right of start
        page.mouse.move(*ring); page.mouse.down(); page.mouse.move(ring[0]+60, ring[1]+40, steps=8); page.mouse.up(); page.wait_for_timeout(700)
        log['steps']['after_drag']=ui(); snap(page,'06_ring_dragged')
        # Shift drag
        page.mouse.move(bb['x']+5,bb['y']+5)
        ring2=None
        for yy in range(0,int(bb['height']),5):
            for xx in range(0,int(bb['width']),5):
                page.mouse.move(bb['x']+xx, bb['y']+yy)
                if page.evaluate("document.getElementById('srcFloorCanvas').style.cursor")=='all-scroll': ring2=(bb['x']+xx,bb['y']+yy); break
            if ring2: break
        if ring2:
            page.keyboard.down('Shift'); page.mouse.move(*ring2); page.mouse.down(); page.mouse.move(ring2[0]-37, ring2[1]+23, steps=6); page.mouse.up(); page.keyboard.up('Shift'); page.wait_for_timeout(600)
            log['steps']['after_shift_drag']=ui()
            page.mouse.move(*ring2); 
        # wheel on ring (find again)
        ring3=None
        for yy in range(0,int(bb['height']),5):
            for xx in range(0,int(bb['width']),5):
                page.mouse.move(bb['x']+xx, bb['y']+yy)
                if page.evaluate("document.getElementById('srcFloorCanvas').style.cursor")=='all-scroll': ring3=(bb['x']+xx,bb['y']+yy); break
            if ring3: break
        if ring3:
            page.mouse.move(*ring3); page.mouse.wheel(0,-100); page.wait_for_timeout(500); log['steps']['after_wheel_up']=ui()
            page.mouse.dblclick(*ring3); page.wait_for_timeout(700); log['steps']['after_dblclick']=ui()
    # keys
    page.focus('#srcFloorCanvas'); page.keyboard.press('ArrowRight'); page.wait_for_timeout(400); log['steps']['after_ArrowRight']=ui()
    page.keyboard.press('ArrowUp'); page.wait_for_timeout(400); log['steps']['after_ArrowUp']=ui()
    page.keyboard.press('f'); page.wait_for_timeout(600); log['steps']['after_F']=ui(); log['steps']['preview_after_F']={k:resp.get('preview',{}).get(k) for k in ('yaw','pitch','yaw_to_face','pitch_to_face','off_mic_deg')}
    snap(page,'07_after_F')
    page.keyboard.press('o'); page.wait_for_timeout(800); log['steps']['after_O']=ui(); snap(page,'08_after_O_omni')
    # directional again, then two sources + mirror
    page.select_option('#sourcePreset','violin_byu'); page.wait_for_timeout(800)
    page.set_input_files('#wavInput','/tmp/stereo_test.wav'); page.wait_for_timeout(3000)
    log['steps']['two_btn_disabled']=page.evaluate("document.getElementById('twoSourceBtn').disabled")
    if not log['steps']['two_btn_disabled']:
        page.click('#twoSourceBtn'); page.wait_for_timeout(1500)
    log['steps']['mirror_checked']=page.evaluate("document.getElementById('mirrorB').checked")
    page.click('.view-tab[data-view=source]'); page.wait_for_timeout(1200)
    lp=[x['body'] for x in log['posts'] if x['url'].startswith('live_params')]
    last=lp[-1] if lp else {}
    log['steps']['two_src_last_live_params_B']={k:last.get(k) for k in ('two_sources','mirror_b','source_radiation','source_radiation_b','source_yaw','source_yaw_b','source_pitch','source_pitch_b','source_size_m')}
    log['steps']['two_src_ui_A']=ui(); snap(page,'09_two_sources_A')
    if not page.evaluate("document.getElementById('sourceChipB').hidden"):
        page.click('#sourceChipB'); page.wait_for_timeout(1200); log['steps']['two_src_ui_B']=ui(); snap(page,'10_two_sources_B_chip')
        page.click('#sourceChipA'); page.wait_for_timeout(500)
    # 3D cone on Floor tab
    page.click('.view-tab[data-view=edit]'); page.wait_for_timeout(1500); snap(page,'11_floor_3d_cone')
    # Paths hover
    page.click('.view-tab[data-view=paths]'); page.wait_for_timeout(3500)
    ic=page.query_selector('#imageCanvas'); ib=ic.bounding_box(); tipt=None; tries=0
    for yy in range(10,int(ib['height']),12):
        for xx in range(10,int(ib['width']),12):
            page.mouse.move(ib['x']+xx, ib['y']+yy); tries+=1
            t=page.evaluate("(()=>{const t=[...document.querySelectorAll('.image-tip, .path-tip, [class*=tip]')].find(e=>!e.hidden && e.textContent.includes('kHz')); return t? t.textContent : null})()")
            if t: tipt=t; break
        if tipt: break
    log['steps']['paths_tooltip']=tipt; log['steps']['paths_tries']=tries
    snap(page,'12_paths_hover')
    imgs=[x for x in log['posts'] if x['url'].startswith('images')]
    log['steps']['n_images_posts']=len(imgs)
    json.dump(log, open(f'/workspace/build_support_2/work/s3_0830/ui_{TAG}.json','w'), indent=1, default=str)
    b.close()
