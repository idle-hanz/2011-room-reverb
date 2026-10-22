"""Screenshot the static mockups served by the box app copy. Usage: shoot.py BASEURL OUTDIR name[:height] ..."""
import sys
from playwright.sync_api import sync_playwright
URL, OUT = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/") + "/"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    for arg in sys.argv[3:]:
        name, _, h = arg.partition(":")
        pg = b.new_page(viewport={"width": 1600, "height": int(h or 1000)}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        page, _, state = name.partition("#")
        pg.goto(URL + "/static/mockups/" + page + ".html" + ("#" + state if state else "")); pg.wait_for_timeout(700)
        pg.screenshot(path=OUT + "mock_" + name.replace("#", "_") + ".png", full_page=True)
        print(name, "errors:", errs); pg.close()
    b.close()
