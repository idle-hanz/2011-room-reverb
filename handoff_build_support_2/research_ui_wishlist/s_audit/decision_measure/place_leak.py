import json, re
from playwright.sync_api import sync_playwright
D='/workspace/audit_1852/'; caps=[]
def on_route(route, req):
    m=re.search(rb'name="params_json"\r\n\r\n(.*?)\r\n--', req.post_data_buffer or b'', re.S)
    if m: caps.append(json.loads(m.group(1)))
    route.fulfill(status=200, content_type='application/json', body='{"ok":true,"status":"stub"}')
def run(seq):
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        pg=b.new_page(viewport={'width':1600,'height':1000}); pg.route('**/api/render', on_route)
        pg.goto('http://127.0.0.1:7860/'); pg.wait_for_timeout(4000)
        pg.set_input_files('#wavInput', D+'data/burst_mono.wav'); pg.wait_for_timeout(500)
        for s in seq: pg.click(f'#placeRow [data-place={s}]'); pg.wait_for_timeout(800)
        n=len(caps); pg.click('#renderBtn')
        for _ in range(60):
            if len(caps)>n: break
            pg.wait_for_timeout(100)
        b.close()
    return caps[-1]
a=run(["studio"]); b=run(["hall","studio"]); h=run(["hall"]); json.dump({"a":a,"b":b,"h":h},open(D+"data/place_full.json","w"),default=str)
diff={k:(a.get(k),b.get(k)) for k in sorted(set(a)|set(b)) if a.get(k)!=b.get(k) and not k.startswith('_')}
for k,v in diff.items():
    s=json.dumps(v)[:200]; print(k, s)
json.dump(diff,open(D+'data/place_leak.json','w'),indent=1,default=str)
