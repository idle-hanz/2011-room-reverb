"""Mic tab: per colour mode x setup, which pattern/preset rows are visible/disabled, state values, and layout sizes."""
import json
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:7881/'; OUT='/workspace/build_support_2/research_ui_wishlist/sui2_fixup/'
Q='''()=>{const vis=e=>!!(e&&e.offsetParent!==null&&getComputedStyle(e).visibility!=="hidden");
const ids=['colour_mode','mic_preset_side','mic_hpf_sides','family_side','polar_side','side_split','mic_preset_l','family_l','polar_l','mic_preset_r','family_r','polar_r','mic_preset_centre','family_c','polar_c','patternLockSide','patternLockCentre','micEach','sideSplitHint'];
const o={};for(const id of ids){const e=document.getElementById(id);if(!e){o[id]=null;continue}o[id]={vis:vis(e),dis:!!e.disabled,val:(e.value!==undefined?e.value:null),txt:(e.tagName==='P'?e.textContent.trim().slice(0,90):undefined)}}
o.options=[...document.querySelectorAll('#colour_mode option')].map(x=>x.textContent);
const r=s=>{const e=document.querySelector(s);if(!e)return null;const b=e.getBoundingClientRect();return [Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)]};
o.layout={viewport:[innerWidth,innerHeight],main:r('main')||r('.main'),micViews:r('#micViews'),top:r('.mic-map-panel'),combined:r('.mic-3d-panel'),sourcePlane:r('.mic-polar-panel'),stage:r('.mic-polar-stage'),hero:r('#micHeroWrap'),tools:r('.mic-polar-tools'),each:r('#micEach'),sidebar:r('.sidebar'),sidebarPanels:[...document.querySelectorAll('.sidebar > .panel, .sidebar > details')].filter(vis).map(e=>[e.id,...(()=>{const b=e.getBoundingClientRect();return [Math.round(b.y),Math.round(b.height)]})()])};
return o}'''
res={}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    for vw in (1600,1920):
        pg=b.new_page(viewport={'width':vw,'height':1000}); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)[:200]))
        pg.goto(URL); pg.wait_for_timeout(4000); pg.click('.view-tab[data-view=mic]'); pg.wait_for_timeout(1500)
        for setup in (['ortf','ms_classic','ab_omni','ms'] if vw==1600 else ['ortf']):
            pg.select_option('#mic_setup',setup); pg.wait_for_timeout(1200)
            for mode in ('MEASURED_SHELF','ASSUMED_TOYS','BYPASS'):
                pg.select_option('#colour_mode',mode); pg.wait_for_timeout(1500)
                k=f'{vw}|{setup}|{mode}'; res[k]=pg.evaluate(Q)
                res[k]['state']=pg.evaluate("()=>{try{return null}catch(e){return null}}")
                if setup in ('ortf','ms_classic'): pg.screenshot(path=OUT+f'shots/mic_{vw}_{setup}_{mode}.png',full_page=True)
            pg.select_option('#colour_mode','MEASURED_SHELF'); pg.wait_for_timeout(800)
        res[f'{vw}|errors']=errs; pg.close()
    b.close()
json.dump(res,open(OUT+'data/mic_probe.json','w'),indent=1)
for k,v in res.items():
    if k.endswith('errors'): print(k,v); continue
    f=lambda i: (('V' if v[i]['vis'] else '-')+('d' if v[i]['dis'] else '')+':'+str(v[i]['val'])[:10]) if v.get(i) else None
    print(k, 'presetS',f('mic_preset_side'),'famS',f('family_side'),'polS',f('polar_side'),'split',f('side_split'),'famC',f('family_c'),'polC',f('polar_c'),'each',v['micEach']['vis'],'lock',v['patternLockSide']['vis'])
print(json.dumps(res['1600|ortf|MEASURED_SHELF']['layout'])); print(json.dumps(res['1920|ortf|MEASURED_SHELF']['layout'])); print(res['1600|ortf|MEASURED_SHELF']['options'])
