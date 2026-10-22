"""Playwright proof for the SL1/SL5/SL6 panel in the box app copy.
usage: prove_sl_ui.py http://127.0.0.1:7873/ OUTDIR   (server: prebuild_app/software, uvicorn)"""
import json, sys
from playwright.sync_api import sync_playwright
URL, OUT = sys.argv[1], sys.argv[2].rstrip("/") + "/"
res = {}
def rr(pg):
    return pg.evaluate("window.SLRoomResult && window.SLRoomResult.view.last ? {n: window.SLRoomResult.view.last.n_within_10pct, T: window.SLRoomResult.view.last.T_faces_air, f: window.SLRoomResult.view.last.f, abs: window.SLRoomResult.view.last.T_absolute_mid} : null")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                          args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    for vw in (1600, 1280):
        pg = b.new_page(viewport={"width": vw, "height": 1000}); pg.on("dialog", lambda d: d.accept())
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        bad = []; pg.on("response", lambda r: bad.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        pg.goto(URL, wait_until="domcontentloaded", timeout=120000); pg.wait_for_timeout(4000)
        pg.click(".view-tab[data-view=surfaces]"); pg.wait_for_timeout(1200)
        tag = f"_{vw}"
        res["panel" + tag] = pg.locator("#slRoomResult").is_visible()
        r0 = rr(pg); res["untreated" + tag] = dict(n=r0["n"], T_abs_mid=r0["abs"]) if r0 else None
        pg.locator("#slRoomResult").screenshot(path=OUT + f"sl1_room_result{tag}.png")
        # paint plaster on all walls+ceiling is the D-SL8 'real default'; here we keep today's cards (Flat cards)
        pg.click("#slMode_surfaces"); pg.wait_for_timeout(300)
        res["mode" + tag] = pg.evaluate("window.RRState.decay_mode")
        # Auto-treat to the dial (field defaults to state.decay_s)
        res["autotreat_field_default" + tag] = pg.input_value("#slAutoTmid")
        pg.click("#slAutoBtn"); pg.wait_for_timeout(2500)
        res["suggested_rows" + tag] = pg.locator("#slSuggest .sl-row").count()
        res["treatment_before_accept" + tag] = pg.evaluate("window.RRState.surf_treatment.length")
        pg.locator("#slRoomResult").screenshot(path=OUT + f"sl6_suggestions{tag}.png")
        pg.click("#slAcceptAll"); pg.wait_for_timeout(1200)
        res["treatment_after_accept" + tag] = pg.evaluate("window.RRState.surf_treatment.length")
        r1 = rr(pg); res["treated" + tag] = dict(n=r1["n"], T_abs_mid=r1["abs"])
        pg.locator("#slRoomResult").screenshot(path=OUT + f"sl6_after_accept{tag}.png")
        # select rear wall D and screenshot its treatment rows
        sel = pg.locator("#roomNet [data-letter=D], #roomNet [data-face=D], #roomNet button:has-text('D')").first
        if sel.count():
            sel.click(); pg.wait_for_timeout(500)
        res["rows_on_selected_face" + tag] = pg.locator("#slTreatment .sl-row").count()
        res["selected" + tag] = pg.evaluate("window.RRColourSurfaces.selected")
        pg.locator("#slTreatment").screenshot(path=OUT + f"sl5_rows_face{tag}.png")
        # toggle the first tuned panel row off: the curve must move near its f0
        info = pg.evaluate("""(() => { const L = window.RRState.surf_treatment.filter(r => r.face === window.RRColourSurfaces.selected && (r.type==='membrane'||r.type==='helmholtz')); return L.length ? {id: L[0].id, f0: L[0].f0} : null; })()""")
        res["toggled_row" + tag] = info
        if info:
            before = rr(pg)
            pg.locator(f"#slTreatment .sl-row[data-id='{info['id']}'] input.sl-on").uncheck(); pg.wait_for_timeout(1200)
            after = rr(pg)
            import math
            i = min(range(len(after["f"])), key=lambda k: abs(math.log(after["f"][k] / info["f0"])))
            res["T_at_f0_on_off" + tag] = [round(before["T"][i], 3), round(after["T"][i], 3)]
            far = min(range(len(after["f"])), key=lambda k: abs(math.log(after["f"][k] / 4000)))
            res["T_at_4k_on_off" + tag] = [round(before["T"][far], 3), round(after["T"][far], 3)]
            pg.locator("#slTreatment").screenshot(path=OUT + f"sl5_row_off{tag}.png")
        # coverage clamp: type 95 % into a porous row on this face
        cov = pg.locator("#slTreatment .sl-row input.sl-cov:not([disabled])").first
        if cov.count():
            cov.fill("95"); cov.press("Enter"); pg.wait_for_timeout(600)
            res["face_cover_after_95_typed" + tag] = pg.evaluate("window.RRState.surf_treatment.filter(r => r.face === window.RRColourSurfaces.selected && r.on !== false).reduce((a, r) => a + r.coverage, 0)")
        # EBU preset
        pg.click("#slTogEbu"); pg.click("#slAutoEbu"); pg.wait_for_timeout(2500)
        res["ebu_t_mid" + tag] = pg.evaluate("Number(document.getElementById('slAutoTmid').value)")
        res["ebu_plan_model_within" + tag] = pg.evaluate("window.SLRoomResult.view.plan.n_within_10pct + '/' + window.SLRoomResult.view.plan.n_bands")
        res["ebu_pass" + tag] = pg.evaluate("JSON.stringify(window.SLRoomResult.view.plan.ebu_pass)")[:200]
        pg.locator("#slAcceptAll").click(); pg.wait_for_timeout(1500)
        res["lock_note" + tag] = pg.locator("#slLockNote").inner_text() if pg.locator("#slLockNote").is_visible() else ""
        pg.locator("#slRoomResult").screenshot(path=OUT + f"sl6_ebu{tag}.png")
        # overflow at this width
        res["panel_overflow_px" + tag] = pg.evaluate("(() => { const e = document.getElementById('slRoomResult'); return Math.max(0, e.scrollWidth - e.clientWidth); })()")
        res["treat_overflow_px" + tag] = pg.evaluate("(() => { const e = document.getElementById('slTreatment'); return Math.max(0, e.scrollWidth - e.clientWidth); })()")
        pg.screenshot(path=OUT + f"sl_surfaces_tab{tag}.png", full_page=False)
        res["page_errors" + tag] = errs; res["http_errors" + tag] = bad
        pg.close()
    b.close()
json.dump(res, open(OUT + "sl_ui_results.json", "w"), indent=1)
print(json.dumps(res, indent=1))

# Stage gating (SL1 build): window.RR_SL_STAGE = 1 before load
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                          args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 1280, "height": 1000}); pg.add_init_script("window.RR_SL_STAGE = 1;")
    pg.goto(URL, wait_until="domcontentloaded", timeout=120000); pg.wait_for_timeout(4000); pg.click(".view-tab[data-view=surfaces]"); pg.wait_for_timeout(1200)
    res["stage1"] = pg.evaluate("({surfaces_disabled: document.getElementById('slMode_surfaces').disabled, autotreat_hidden: document.getElementById('slAutoTreat').hidden, treatment_hidden: document.getElementById('slTreatment').hidden, panel_drawn: !!(window.SLRoomResult && window.SLRoomResult.view.last)})")
    pg.locator("#slRoomResult").screenshot(path=OUT + "sl1_stage1_1280.png")
    b.close()
json.dump(res, open(OUT + "sl_ui_results.json", "w"), indent=1)
print("stage1", res["stage1"])
