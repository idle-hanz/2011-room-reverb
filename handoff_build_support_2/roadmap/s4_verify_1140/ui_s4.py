import json, sys, time
from playwright.sync_api import sync_playwright
URL=sys.argv[1]; D='/workspace/build_support_2/roadmap/s4_verify_1140/'; SH=D+'shots/'
log={'console':[], 'steps':{}, 'shots':[]}
posts=[]
def snap(page,name): page.screenshot(path=SH+f'ui1140_{name}.png'); log['shots'].append(f'ui1140_{name}.png')
def last_body(prefix='live_params'):
    b=[x['body'] for x in posts if x['url'].startswith(prefix) and x['body']]
    return b[-1] if b else None
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'])
    page=b.new_page(viewport={'width':1600,'height':1000})
    page.on('console', lambda m: log['console'].append((m.type, m.text[:300])) if m.type in ('error','warning') else None)
    page.on('pageerror', lambda e: log['console'].append(('pageerror', str(e)[:300])))
    def onreq(r):
        if r.method=='POST' and '/api/' in r.url:
            try: body=r.post_data_json
            except Exception: body=None
            posts.append({'url':r.url.split('/api/')[1],'t':round(time.time(),2),'body':body})
    page.on('request', onreq)
    page.goto(URL); page.wait_for_timeout(4000)
    log['steps']['tabs']=page.eval_on_selector_all('.view-tab','els=>els.map(e=>e.textContent.trim())')
    # which tabs show surface controls?
    vis_js='''()=>{const vis=e=>!!(e && e.offsetParent!==null && getComputedStyle(e).visibility!=="hidden");
      const q=s=>[...document.querySelectorAll(s)].filter(vis).length;
      return {surface_cards:q('.surface-card'), solo_btns:q('[data-solo]'), mute_btns:q('[data-mute]'), material_chips:q('[data-material]'),
              smear:vis(document.getElementById('jitterSlider')), tail_dif:vis(document.getElementById('structureDifSlider')),
              sidebar_panels:[...document.querySelectorAll('.sidebar .panel')].filter(vis).map(e=>e.id||e.className)}}'''
    tabs={}
    for v in ('edit','source','mic','mix','lattice','paths','colour','surfaces','polar'):
        page.click(f'.view-tab[data-view={v}]'); page.wait_for_timeout(700); tabs[v]=page.evaluate(vis_js)
        if v in ('edit','surfaces'): snap(page,f'01_tab_{v}')
    log['steps']['controls_by_tab']=tabs
    page.click('.view-tab[data-view=surfaces]'); page.wait_for_timeout(1500)
    def card_state():
        return page.evaluate('''()=>{const st=[...document.querySelectorAll('.surface-card')].map(c=>({L:c.dataset.letter,
            muted:c.classList.contains('is-muted'), solo:c.classList.contains('is-solo'),
            solo_on:c.querySelector('[data-solo]').getAttribute('aria-pressed'), mute_on:c.querySelector('[data-mute]').getAttribute('aria-pressed')}));
            const off=document.getElementById('surfacesSoloOff'); return {cards:st, solo_off:off&&off.getAttribute('aria-pressed'),
            title:(document.getElementById('surfaceDetailTitle')||{}).textContent, honesty:(document.getElementById('surfaceHonesty')||{}).textContent,
            smear:document.getElementById('jitterSlider').value, tail:document.getElementById('structureDifSlider').value}}''')
    def chips():
        return page.eval_on_selector_all('[data-material]','els=>els.map(e=>({id:e.dataset.material, name:e.textContent, disabled:e.disabled, title:e.title}))')
    def sel(L):
        page.click(f'.surface-card[data-letter={L}] .sc-label'); page.wait_for_timeout(400)
    def grab():
        page.click('.view-tab[data-view=paths]'); page.wait_for_timeout(1800)
        bd=last_body('images') or {}
        page.click('.view-tab[data-view=surfaces]'); page.wait_for_timeout(700)
        return bd
    def body_keys():
        bd=grab()
        s=bd.get('surfaces') or {}
        return {'surfaces_solo':bd.get('surfaces_solo','<missing>'), 'surfaces_mute':bd.get('surfaces_mute','<missing>'),
                'A':{k:(s.get('A') or {}).get(k) for k in ('absorb','jitter_D','structure_dif','diffusion','material','honesty')},
                'E':{k:(s.get('E') or {}).get(k) for k in ('absorb','material')}, 'F':{k:(s.get('F') or {}).get(k) for k in ('absorb','material')},
                'B':{k:(s.get('B') or {}).get(k) for k in ('absorb','material')}}
    log['steps']['first_body']=body_keys()
    log['steps']['first_body_full']=last_body('images')
    log['steps']['default']=card_state()
    for L in 'AEF':
        sel(L); log['steps'][f'chips_on_{L}']=[(c['id'],c['disabled']) for c in chips()]
    log['steps']['chip_titles']=[(c['id'],c['title']) for c in chips()]
    sel('A'); snap(page,'02_surfaces_A_default')
    # paint curtain on A
    n0=len(posts); page.click('[data-material=heavy_curtain]'); page.wait_for_timeout(1500)
    log['steps']['after_curtain_A']={'state':card_state(), 'body':body_keys(), 'new_posts':[x['url'] for x in posts[n0:]]}
    snap(page,'03_curtain_on_A')
    sel('E'); log['steps']['E_curtain_disabled']=[c['disabled'] for c in chips() if c['id']=='heavy_curtain']
    page.click('[data-material=heavy_curtain]', force=True); page.wait_for_timeout(800)
    log['steps']['after_force_click_curtain_on_E']=body_keys()['E']
    snap(page,'04_floor_selected_curtain_grey')
    # shift-paint curtain (from A)
    sel('B'); page.click('[data-material=heavy_curtain]', modifiers=['Shift']); page.wait_for_timeout(1500)
    bk=body_keys(); log['steps']['after_shift_curtain']={L:((grab()).get('surfaces') or {}).get(L,{}).get('material') for L in 'ABCDEF'}
    sel('E'); page.click('[data-material=carpet_on_concrete]', modifiers=['Shift']); page.wait_for_timeout(1500)
    log['steps']['after_shift_carpet']={L:((grab()).get('surfaces') or {}).get(L,{}).get('material') for L in 'ABCDEF'}
    # porous gap on F (ceiling) and on E (should be disabled)
    sel('F'); pg=[c for c in chips() if c['id'].startswith('absorber_panel') ]; log['steps']['porous_on_F']=[(c['id'],c['disabled']) for c in pg]
    page.click('[data-material=absorber_panel_2in_gap2in]'); page.wait_for_timeout(1500)
    log['steps']['after_gap_on_F']={'state':card_state(), 'F_absorb':((grab()).get('surfaces') or {}).get('F',{}).get('absorb')}
    snap(page,'05_gap2in_on_F')
    # All legal faces toggle
    page.click('#materialPaintAll'); page.wait_for_timeout(500)
    log['steps']['paintall_on_chips_F']=[(c['id'],c['disabled']) for c in chips()]
    page.click('[data-material=plaster_smooth]'); page.wait_for_timeout(1500)
    log['steps']['after_paintall_plaster']={L:((grab()).get('surfaces') or {}).get(L,{}).get('material') for L in 'ABCDEF'}
    page.click('#materialPaintAll'); page.wait_for_timeout(300)
    # smear / tail diffusion split
    sel('A')
    page.evaluate("()=>{const e=document.getElementById('jitterSlider'); e.value='0.6'; e.dispatchEvent(new Event('input',{bubbles:true}))}"); page.wait_for_timeout(1200)
    log['steps']['after_smear_0.6']=body_keys()['A']
    page.evaluate("()=>{const e=document.getElementById('structureDifSlider'); e.value='0.4'; e.dispatchEvent(new Event('input',{bubbles:true}))}"); page.wait_for_timeout(1200)
    log['steps']['after_tail_0.4']=body_keys()['A']
    snap(page,'06_smear_tail_split')
    # Solo / Mute
    page.click('.surface-card[data-letter=E] [data-solo]'); page.wait_for_timeout(1200)
    log['steps']['solo_E']={'state':card_state(),'body':{k:body_keys()[k] for k in ('surfaces_solo','surfaces_mute')}}
    snap(page,'07_solo_E')
    page.click('.surface-card[data-letter=C] [data-solo]'); page.wait_for_timeout(1000)
    log['steps']['solo_C_after_E']={'state':card_state(),'body':{k:body_keys()[k] for k in ('surfaces_solo','surfaces_mute')}}
    page.click('#surfacesSoloOff'); page.wait_for_timeout(800)
    page.click('.surface-card[data-letter=A] [data-mute]'); page.wait_for_timeout(500)
    page.click('.surface-card[data-letter=C] [data-mute]'); page.wait_for_timeout(1200)
    log['steps']['mute_A_C']={'state':card_state(),'body':{k:body_keys()[k] for k in ('surfaces_solo','surfaces_mute')}}
    snap(page,'08_mute_A_C')
    page.click('.surface-card[data-letter=A] [data-solo]'); page.wait_for_timeout(1000)
    log['steps']['solo_on_muted_A']={'state':card_state(),'body':{k:body_keys()[k] for k in ('surfaces_solo','surfaces_mute')}}
    page.click('.surface-card[data-letter=A] [data-mute]'); page.wait_for_timeout(1000)
    log['steps']['mute_on_soloed_A']={'state':card_state(),'body':{k:body_keys()[k] for k in ('surfaces_solo','surfaces_mute')}}
    # paint while solo
    page.click('.surface-card[data-letter=E] [data-solo]'); page.wait_for_timeout(600); sel('B')
    page.click('[data-material=brick_unglazed]'); page.wait_for_timeout(1200)
    log['steps']['paint_B_while_solo_E']={'body':{k:body_keys()[k] for k in ('surfaces_solo','surfaces_mute','B')}}
    snap(page,'09_paint_while_solo')
    # card hit target sizes
    log['steps']['button_sizes']=page.evaluate("()=>[...document.querySelectorAll('.surface-card[data-letter=A] button, #surfacesSoloOff, #materialPaintAll, [data-material=heavy_curtain]')].map(e=>{const r=e.getBoundingClientRect(); return [e.textContent.trim(), Math.round(r.width), Math.round(r.height)]})")
    # Hall place button clears solo/mute
    hb=page.query_selector('[data-place=hall]')
    if hb:
        try:
            if not hb.is_visible():
                page.click('.view-tab[data-view=edit]'); page.wait_for_timeout(800)
            hb.click(); page.wait_for_timeout(2500)
        except Exception as e: log['steps']['hall_err']=str(e)[:200]
        bd=grab()
        log['steps']['after_hall']={'surfaces_solo':bd.get('surfaces_solo'),'surfaces_mute':bd.get('surfaces_mute'),
            'dif':{L:{k:(bd.get('surfaces') or {}).get(L,{}).get(k) for k in ('jitter_D','structure_dif','diffusion','material')} for L in 'ABCDEF'},
            'reaktor_parity':bd.get('reaktor_parity'),'W':bd.get('W')}
        page.click('.view-tab[data-view=surfaces]'); page.wait_for_timeout(1000)
        log['steps']['after_hall_state']=card_state(); snap(page,'10_after_hall')
    log['posts_count']={}
    for x in posts: log['posts_count'][x['url'].split('?')[0]]=log['posts_count'].get(x['url'].split('?')[0],0)+1
    json.dump(log, open(D+'ui_s4.json','w'), indent=1, default=str)
    b.close()
print('ok')
