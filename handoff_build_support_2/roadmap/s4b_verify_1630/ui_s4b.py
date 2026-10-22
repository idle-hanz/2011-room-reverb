"""S4b D12 (Solo -> Mix plays Early only, exact restore) + D17 hint, headless Chrome on the box against the 16:30 snapshot."""
import json, sys, time
from playwright.sync_api import sync_playwright
URL=sys.argv[1]; D='/workspace/build_support_2/roadmap/s4b_verify_1630/'; SH=D+'shots/'
WAV='/workspace/build_support_2/roadmap/robotic_1240/test_guitar_dualmono.wav'
K=('direct_wet','fdn_wet','early_wet','dry_gain','fader_direct','fader_fdn','fader_early','fader_dry','mute_early','mute_fdn','surfaces_solo','surfaces_mute')
log={'console':[],'steps':{},'shots':[]}; posts=[]
def snap(page,n): page.screenshot(path=SH+f'ui1630_{n}.png'); log['shots'].append(f'ui1630_{n}.png')
def last(prefix='live_params'):
    b=[x['body'] for x in posts if x['url'].startswith(prefix) and x['body']]; return b[-1] if b else None
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'])
    page=b.new_page(viewport={'width':1600,'height':1000})
    page.on('console',lambda m: log['console'].append((m.type,m.text[:300])) if m.type in('error','warning') else None)
    page.on('pageerror',lambda e: log['console'].append(('pageerror',str(e)[:300])))
    def onreq(r):
        if r.method=='POST' and '/api/' in r.url:
            try: body=r.post_data_json
            except Exception: body=None
            posts.append({'url':r.url.split('/api/')[1],'body':body})
    page.on('request',onreq)
    page.goto(URL); page.wait_for_timeout(4000)
    page.set_input_files('#wavInput',WAV); page.wait_for_timeout(1500)
    page.click('#liveBtn'); page.wait_for_timeout(6000)
    log['steps']['live_running']=page.evaluate('()=>!!(window.LiveFDN&&LiveFDN.isRunning())')
    log['steps']['worklet_ver_seen']=page.evaluate('()=>[...performance.getEntriesByType("resource")].map(e=>e.name).filter(n=>n.includes("worklet")||n.includes("live_fdn")||n.includes(".wasm"))')
    # give the Mix a non-default setting: Direct up, Early at a non-unity travel, Dry up
    def setf(id,v):
        page.click('.view-tab[data-view=mix]'); page.wait_for_timeout(300)
        page.evaluate(f"()=>{{const e=document.getElementById('{id}'); e.value='{v}'; e.dispatchEvent(new Event('input',{{bubbles:true}})); e.dispatchEvent(new Event('change',{{bubbles:true}}))}}"); page.wait_for_timeout(700)
    setf('fader_direct','0.62'); setf('fader_early','0.41'); setf('fader_dry','0.30'); setf('fader_fdn','0.55')
    def body(): page.wait_for_timeout(900); bd=last() or {}; return {k:bd.get(k,'<missing>') for k in K}
    def faders(): return page.evaluate("()=>['fader_direct','fader_fdn','fader_early','fader_dry'].map(i=>document.getElementById(i).value)")
    def hint(): return page.evaluate("()=>{const e=document.getElementById('surfaceSoloHint'); return e?{text:e.textContent, visible:e.offsetParent!==null}:null}")
    n0=len(posts); base=body(); log['steps']['0_mix_set']={'body':base,'faders':faders(),'posts':len(posts)-n0}
    page.click('.view-tab[data-view=surfaces]'); page.wait_for_timeout(1200)
    log['steps']['0_hint_no_solo']=hint()
    page.click('.surface-card[data-letter=A] [data-solo]'); s1=body()
    log['steps']['1_solo_A']={'body':s1,'faders':faders(),'hint':hint()}; snap(page,'01_solo_A_hint')
    page.click('.surface-card[data-letter=D] [data-solo]'); s2=body()
    log['steps']['2_solo_D']={'body':s2,'hint':hint()}; snap(page,'02_solo_D_hint')
    page.click('.view-tab[data-view=mix]'); page.wait_for_timeout(600); snap(page,'03_mix_while_solo')
    log['steps']['3_mix_faders_while_solo']=faders()
    page.click('.view-tab[data-view=surfaces]'); page.wait_for_timeout(600)
    page.click('#surfacesSoloOff'); r1=body()
    log['steps']['4_solo_off']={'body':r1,'faders':faders(),'hint':hint()}
    page.click('.surface-card[data-letter=A] [data-mute]'); m1=body()
    log['steps']['5_mute_A_only']={'body':m1,'hint':hint()}
    page.click('.surface-card[data-letter=A] [data-mute]'); page.wait_for_timeout(300)
    # early fader at zero then solo: auditions at unity
    setf('fader_early','0'); page.click('.view-tab[data-view=surfaces]'); page.wait_for_timeout(500)
    z0=body(); page.click('.surface-card[data-letter=B] [data-solo]'); z1=body(); page.click('#surfacesSoloOff'); z2=body()
    log['steps']['6_early0_solo']={'before':z0,'solo':z1,'off':z2}
    keys=('direct_wet','fdn_wet','early_wet','dry_gain','fader_direct','fader_fdn','fader_early','fader_dry')
    v={}
    v['solo_zeroes_direct_fdn_dry']=all(s1[k]==0 for k in ('direct_wet','fdn_wet','dry_gain')) and all(s2[k]==0 for k in ('direct_wet','fdn_wet','dry_gain'))
    v['solo_early_equals_fader_early']=s1['early_wet']==base['early_wet'] and base['early_wet']>0
    v['solo_faders_unchanged_in_body']=all(s1[k]==base[k] for k in keys[4:])
    v['solo_off_exact_restore']=all(r1[k]==base[k] for k in keys)
    v['mute_alone_no_mix_change']=all(m1[k]==base[k] for k in keys)
    v['early0_solo_unity']=(z1['early_wet']==1) and z1['fdn_wet']==0 and all(z2[k]==z0[k] for k in keys)
    v['hint_A']=log['steps']['1_solo_A']['hint']; v['hint_D']=log['steps']['2_solo_D']['hint']; v['hint_off']=log['steps']['4_solo_off']['hint']
    v['ui_faders_never_moved']=log['steps']['3_mix_faders_while_solo']==log['steps']['0_mix_set']['faders']==log['steps']['4_solo_off']['faders']
    log['verdict']=v
    json.dump(log,open(D+'ui_s4b.json','w'),indent=1,default=str); b.close()
print(json.dumps(log['verdict'],indent=1,default=str)); print('live',log['steps']['live_running'],'console',log['console'][:8])
