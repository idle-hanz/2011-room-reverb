"""Playwright proof for T1 in the box app copy. Usage: prove_t1.py http://127.0.0.1:7872/ OUTDIR"""
import json, sys
from playwright.sync_api import sync_playwright
URL, OUT = sys.argv[1], sys.argv[2].rstrip("/") + "/"
res = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                          args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 1600, "height": 1000}); pg.on("dialog", lambda d: d.accept())
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.click(".view-tab[data-view=mix]"); pg.wait_for_timeout(1000)
    res["booted"] = pg.evaluate("window.__rrControlsBooted")
    def centre(sel):
        bb = pg.locator(sel).bounding_box(); return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
    def val(i): return pg.evaluate(f"Number(document.getElementById('{i}').value)")
    # 1 coarse drag: 45 px up = +6 dB (180 px = 24 dB)
    x, y = centre("#trim_l"); pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x, y - 20, steps=4); pg.mouse.move(x, y - 45, steps=6); pg.mouse.up()
    res["trim_l_after_45px_up"] = val("trim_l")
    # 2 fine drag with Shift: 45 px = 0.6 dB -> rounds to step 0.5
    pg.keyboard.down("Shift"); x, y = centre("#trim_c"); pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x, y - 45, steps=8); pg.mouse.up(); pg.keyboard.up("Shift")
    res["trim_c_after_shift_45px"] = val("trim_c")
    # 3 detent: from +6, drag down 42 px (5.6 dB) -> lands within 0.8 dB of 0 -> held at 0
    x, y = centre("#trim_l"); pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x, y + 42, steps=8); pg.mouse.up()
    res["trim_l_detent"] = val("trim_l")
    # 4 typed value on the knob readout
    pg.locator("#trimBox_r .rr-knob-read").click(); pg.keyboard.press("Control+A"); pg.keyboard.type("-4.5 dB"); pg.keyboard.press("Enter"); pg.wait_for_timeout(200)
    res["trim_r_typed"] = val("trim_r"); res["trim_r_readout"] = pg.locator("#trimBox_r .rr-knob-read").inner_text()
    # 5 typed pan on the centre strip
    pan_read = pg.locator("#pan_c").locator("xpath=../following-sibling::output[1]")
    pan_read.click(); pg.keyboard.press("Control+A"); pg.keyboard.type("L30"); pg.keyboard.press("Enter"); pg.wait_for_timeout(200)
    res["pan_c_typed"] = val("pan_c"); res["pan_c_readout"] = pan_read.inner_text()
    pg.screenshot(path=OUT + "t1_mix_after.png", clip={"x": 0, "y": 0, "width": 1600, "height": 1000})
    desk = pg.locator(".desk-strip").first.locator("xpath=..").bounding_box()
    pg.screenshot(path=OUT + "t1_desk_crop.png", clip={"x": desk["x"], "y": desk["y"], "width": min(desk["width"], 1100), "height": min(desk["height"], 520)})
    # 6 double-click resets
    x, y = centre("#trim_r"); pg.mouse.dblclick(x, y); pg.wait_for_timeout(200)
    res["trim_r_after_dblclick"] = val("trim_r")
    # 7 wheel step
    x, y = centre("#trim_r"); pg.mouse.move(x, y); pg.mouse.wheel(0, -100); pg.wait_for_timeout(200)
    res["trim_r_after_wheel_up"] = val("trim_r")
    # 8 keyboard PageUp on pan_c (10 steps of 0.01)
    pg.focus("#pan_c"); pg.keyboard.press("PageUp"); res["pan_c_after_pageup"] = val("pan_c")
    # 9 state reached app.js (the app's own input handlers ran)
    res["app_state_sync"] = pg.evaluate("document.getElementById('read_l') ? document.getElementById('read_l').textContent : null")
    # 10 Width needle (B2): route L to s, type +12 on width
    pg.click("[data-route=l][data-name=s]"); pg.wait_for_timeout(400)
    pg.locator("#widthBox_l .rr-knob-read").click(); pg.keyboard.press("Control+A"); pg.keyboard.type("12"); pg.keyboard.press("Enter"); pg.wait_for_timeout(300)
    res["width_l"] = val("width_l"); res["width_needle"] = pg.evaluate("document.getElementById('width_l').parentElement.style.getPropertyValue('--needle')")
    # 11 typing on a normal slider (Room W) via its <output>
    pg.click(".view-tab[data-view=edit]"); pg.wait_for_timeout(800)
    out = pg.locator("#W_out")
    if out.is_visible():
        out.click(); pg.keyboard.press("Control+A"); pg.keyboard.type("7.25 m"); pg.keyboard.press("Enter"); pg.wait_for_timeout(300)
        res["room_W_typed"] = val("W"); res["W_out"] = out.inner_text()
        bb = out.locator("xpath=..").bounding_box()
        pg.locator("#W_out").click(); pg.wait_for_timeout(150)
        pg.screenshot(path=OUT + "t1_room_typed.png", clip={"x": max(0, bb["x"] - 10), "y": max(0, bb["y"] - 10), "width": bb["width"] + 20, "height": 90})
        pg.keyboard.press("Escape")
    res["page_errors"] = errs
    pg.click(".view-tab[data-view=mix]"); pg.wait_for_timeout(600)
    desk = pg.locator(".desk-strip").first.locator("xpath=..").bounding_box()
    pg.screenshot(path=OUT + "t1_desk_width.png", clip={"x": desk["x"], "y": desk["y"], "width": min(desk["width"], 1100), "height": min(desk["height"], 520)})
    b.close()
json.dump(res, open(OUT + "t1_results.json", "w"), indent=1)
print(json.dumps(res, indent=1))
