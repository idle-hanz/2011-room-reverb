import json, sys, time
from playwright.sync_api import sync_playwright
URL=sys.argv[1]; TAG=sys.argv[2]; D='/workspace/build_support_2/roadmap/robotic_1240/'
log={'phases':{},'console':[]}; posts=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'])
    page=b.new_page(viewport={'width':1600,'height':1000})
    page.on('console', lambda m: log['console'].append((m.type, m.text[:200])) if m.type in ('error','warning') else None)
    page.on('request', lambda r: posts.append((round(time.time(),3), r.url.split('/api/')[1])) if (r.method=='POST' and '/api/' in r.url) else None)
    page.goto(URL); page.wait_for_timeout(4000)
    page.set_input_files('#wavInput', D+'test_guitar_dualmono.wav'); page.wait_for_timeout(1500)
    page.evaluate('''()=>{window.__upd=[]; const o=LiveFDN.update; LiveFDN.update=function(d){window.__upd.push(performance.now()); return o.apply(this,arguments)}}''')
    page.click('#liveBtn'); page.wait_for_timeout(3000)
    running=page.evaluate('()=>LiveFDN.isRunning()'); log['running']=running
    def phase(name, secs):
        t0=time.time(); n0=page.evaluate('()=>window.__upd.length'); page.wait_for_timeout(int(secs*1000)); t1=time.time()
        n1=page.evaluate('()=>window.__upd.length')
        lp=[x for x in posts if t0<=x[0]<=t1 and x[1].startswith('live_params')]
        allp={}
        for x in posts:
            if t0<=x[0]<=t1: allp[x[1]]=allp.get(x[1],0)+1
        log['phases'][name]={'secs':secs,'live_params_posts':len(lp),'LiveFDN_update_calls':n1-n0,'all_posts':allp}
        print(TAG,name,log['phases'][name],flush=True)
    phase('room_idle',6)
    for v in ('source','surfaces','paths','polar'):
        page.click(f'.view-tab[data-view={v}]'); page.wait_for_timeout(500); phase(f'{v}_idle',5)
    page.click('.view-tab[data-view=edit]'); page.wait_for_timeout(300)
    hall=page.query_selector('#placeRow [data-place=hall]')
    if hall: hall.click(); page.wait_for_timeout(500); phase('hall_idle',6)
    page.click('.view-tab[data-view=surfaces]'); page.wait_for_timeout(500); phase('hall_surfaces_idle',5)
    page.click('.view-tab[data-view=source]'); page.wait_for_timeout(500); phase('hall_source_idle',5)
    page.screenshot(path=D+f'ui_live_{TAG}.png')
    json.dump(log,open(D+f'ui_live_{TAG}.json','w'),indent=1)
