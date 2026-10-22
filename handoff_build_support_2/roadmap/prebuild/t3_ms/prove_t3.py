"""Playwright proof for the T3 demo page. Usage: prove_t3.py BASEURL OUTDIR"""
import json, sys
from playwright.sync_api import sync_playwright
URL, OUT = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/") + "/"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    pg = b.new_page(viewport={"width": 1000, "height": 640}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL + "/static/mockups/t3_ms_demo.html"); pg.wait_for_timeout(400)
    t15 = pg.eval_on_selector_all(".card p:nth-of-type(1)", "e=>e.map(x=>x.textContent)")
    pg.screenshot(path=OUT + "t3_ms_m35.png")
    pg.click("#g10"); pg.wait_for_timeout(200)
    t10 = pg.eval_on_selector_all(".card p:nth-of-type(1)", "e=>e.map(x=>x.textContent)")
    pg.screenshot(path=OUT + "t3_ms_m0.png"); b.close()
res = {"m+3.5dB": t15, "m0dB": t10, "errors": errs}
json.dump(res, open(OUT + "t3_results.json", "w"), indent=1); print(json.dumps(res, indent=1))
