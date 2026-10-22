"""Playwright proof for T2 demo page. Usage: prove_t2.py BASEURL OUTDIR"""
import json, sys
from playwright.sync_api import sync_playwright
URL, OUT = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/") + "/"
res = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    pg = b.new_page(viewport={"width": 1240, "height": 560}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL + "/static/mockups/t2_mixer_demo.html"); pg.wait_for_timeout(500)
    rows = lambda: pg.eval_on_selector_all("#wt tr", "rs=>rs.slice(1).map(r=>[...r.cells].map(c=>c.textContent))")
    res["ortf"] = rows(); pg.screenshot(path=OUT + "t2_ortf.png")
    pg.click(".lr-btn[data-cap=c][data-side=l]"); pg.click(".lr-btn[data-cap=c][data-side=r]")   # C: off -> L+R = pan centre
    res["c_both_on"] = rows()[1]
    pg.click(".lr-btn[data-cap=l][data-side=r]"); pg.click(".lr-btn[data-cap=l][data-side=r]")   # L: R off->on->Ø = side
    res["l_side"] = rows()[0]; pg.screenshot(path=OUT + "t2_clicks.png")
    pg.click("#pMS"); res["ms"] = rows(); pg.screenshot(path=OUT + "t2_ms.png")
    pg.click("#pMS3"); res["ms3"] = rows(); pg.screenshot(path=OUT + "t2_ms3.png")
    res["errors"] = errs; b.close()
json.dump(res, open(OUT + "t2_results.json", "w"), indent=1); print(json.dumps(res))
