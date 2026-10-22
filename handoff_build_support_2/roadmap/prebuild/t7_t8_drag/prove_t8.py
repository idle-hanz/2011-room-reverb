"""Playwright proof for the T7/T8 drag demo. Usage: prove_t8.py BASEURL OUTDIR"""
import json, sys
from playwright.sync_api import sync_playwright
URL, OUT = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/") + "/"
res = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    pg = b.new_page(viewport={"width": 1400, "height": 660}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL + "/static/mockups/t7_t8_drag_demo.html"); pg.wait_for_timeout(400)
    fb = pg.locator("#floor").bounding_box(); eb = pg.locator("#elev").bounding_box()
    L = lambda: pg.evaluate("(()=>{const s=520,pad=46,S=window.__S;const sc=Math.min((s-2*pad)/S.W,(560-2*pad)/S.L);return {ox:(520-S.W*sc)/2,oy:(560-S.L*sc)/2,sc:sc,W:S.W,L:S.L};})()")
    def fpx(x, z, l): return fb["x"] + l["ox"] + x * l["sc"], fb["y"] + l["oy"] + (l["L"] - z) * l["sc"]
    S = lambda: pg.evaluate("JSON.parse(JSON.stringify(window.__S))")
    def drag(x0, y0, x1, y1, shot=None, shift=False):
        pg.mouse.move(x0, y0); pg.mouse.down()
        if shift: pg.keyboard.down("Shift")
        pg.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=5); pg.mouse.move(x1, y1, steps=5)
        if shot: pg.screenshot(path=OUT + shot, clip={"x": 0, "y": 0, "width": 1400, "height": 660})
        if shift: pg.keyboard.up("Shift")
        pg.mouse.up()
    l = L(); x, y = fpx(6, 4, l); x2, _ = fpx(7.5, 4, l)
    drag(x + 2, y, x2 + 2, y, "t8_wall_right.png"); res["right_wall_to_7.5"] = S()["W"]
    l = L(); x, y = fpx(0, 4, l); x2, _ = fpx(1.0, 4, l)
    drag(x - 2, y, x2 - 2, y, shift=True); s = S(); res["left_wall_+1.0"] = {"W": s["W"], "sx": s["sx"], "mcx": s["mcx"]}
    l = L(); x, y = fpx(3, 8, l); _, y2 = fpx(3, 3.0, l)
    drag(x, y - 2, x, y2, "t8_wall_stop.png"); res["front_wall_into_source"] = S()["L"]
    pg.click("[data-mode=split]"); l = L(); s = S()
    mx, my = fpx(s["mcx"] + s["space"] / 2, s["mcz"], l); tx, ty = fpx(s["W"] - 0.8, s["L"] - 1.2, l)
    drag(mx, my, tx, ty, "t8_split_r.png"); s = S(); res["split_r"] = {"place_r": s.get("place_r"), "x": s.get("room_r_x"), "z": s.get("room_r_z")}
    pg.click("[data-mode=mirror]"); l = L(); s = S()
    mx, my = fpx(s["mcx"] - s["space"] / 2, s["mcz"], l); tx, _ = fpx(s["mcx"] - 0.6, s["mcz"], l)
    drag(mx, my, tx, my); res["mirror_l_space"] = S()["space"]
    el = pg.evaluate("(()=>{const S=window.__S,pad=40;const sc=Math.min((520-2*pad)/S.L,(260-2*pad)/S.H);return {ox:(520-S.L*sc)/2,oy:(260-S.H*sc)/2,sc:sc,H:S.H};})()")
    cx, cy = eb["x"] + el["ox"] + 100, eb["y"] + el["oy"]
    drag(cx, cy + 1, cx, cy + 1 - 1.2 * el["sc"], "t8_ceiling.png"); res["ceiling_up_1.2"] = S()["H"]
    pg.screenshot(path=OUT + "t8_final.png", clip={"x": 0, "y": 0, "width": 1400, "height": 660})
    res["errors"] = errs; b.close()
json.dump(res, open(OUT + "t8_results.json", "w"), indent=1); print(json.dumps(res, indent=1))
