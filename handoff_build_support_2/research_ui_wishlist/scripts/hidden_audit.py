"""List elements that carry hidden=true but still render (CSS display overrides [hidden]).
v2 (3 Oct 2026): tabs are discovered from .view-tab (works with 8 or 7 tabs), every Colour mode is visited,
output goes to ../data/hidden_audit.json next to this script, Chrome path optional. Exit code 1 if any leak.
Usage: python hidden_audit.py http://127.0.0.1:7860/"""
import json, os, sys
from playwright.sync_api import sync_playwright
URL=sys.argv[1]; D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data'); os.makedirs(D,exist_ok=True)
JS='''()=>[...document.querySelectorAll("[hidden]")].filter(e=>{const s=getComputedStyle(e);return s.display!=="none"}).map(e=>({id:e.id||null,cls:e.className&&String(e.className).slice(0,60),tag:e.tagName,display:getComputedStyle(e).display,onscreen:e.getClientRects().length>0&&!!e.offsetParent,text:(e.textContent||"").trim().slice(0,50)}))'''
CH='/usr/bin/google-chrome'
if not os.path.exists(CH):
    for _c in (r'C:\Program Files\Google\Chrome\Application\chrome.exe', r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'):
        if os.path.exists(_c):
            CH = _c
            break
out={}
with sync_playwright() as p:
    kw=dict(headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    if os.path.exists(CH): kw['executable_path']=CH
    b=p.chromium.launch(**kw)
    pg=b.new_page(viewport={'width':1600,'height':1000})
    dialogs=[]
    def _dlg(d):
        dialogs.append(d.message)
        d.dismiss()
    pg.on('dialog', _dlg)
    pg.goto(URL); pg.wait_for_timeout(4000)
    tabs=pg.evaluate('()=>[...document.querySelectorAll(".view-tab")].map(e=>e.dataset.view)')
    for setup in ('ortf','ms_classic','binaural','mono_c'):
        for mode in ('MEASURED_SHELF','ASSUMED_TOYS','BYPASS'):
            pg.click('.view-tab[data-view=mic]'); pg.wait_for_timeout(400)
            pg.select_option('#mic_setup',setup); pg.wait_for_timeout(900)
            pg.select_option('#colour_mode',mode); pg.wait_for_timeout(900)
            for t in tabs:
                pg.click(f'.view-tab[data-view={t}]'); pg.wait_for_timeout(600)
                out[f'{setup}|{mode}|{t}']=[x for x in pg.evaluate(JS) if x['onscreen']]
    b.close()
json.dump(out,open(os.path.join(D,'hidden_audit.json'),'w'),indent=1)
seen={}
for k,v in out.items():
    for x in v: seen.setdefault((x['id'],x['tag'],x['display'],x['text'][:30]),[]).append(k)
for k,v in seen.items(): print(k, len(v), v[:4])
n=sum(len(v) for v in out.values()); print('tabs',tabs,'states',len(out),'visible [hidden] elements',n)
if dialogs:
    print('DIALOGS', len(dialogs), dialogs[:4])
sys.exit(1 if n or dialogs else 0)
