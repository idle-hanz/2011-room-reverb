"""S-UI2 fix-up 2 visibility, drag, palette, and tab tour.

The earlier visibility-matrix file was not in this tree (software/tests has no
sui2 module, and sui2_fixup/scripts only had mic_probe.py). This script is the
D-UI27 check: #micEach stays up except in Binaural, sits above the Source plane,
and the lock note shows only while the preset owns the pattern.

Usage: python fixup2_mic_each.py http://127.0.0.1:7860/
"""
import json
import math
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:7860/"
HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "..", "shots")
os.makedirs(SHOTS, exist_ok=True)

SETUPS = ("ortf", "ms_classic", "ab_omni", "mono_c", "binaural")
MODES = ("MEASURED_SHELF", "ASSUMED_TOYS", "BYPASS")
MODE_LABEL = {
    "MEASURED_SHELF": "Measured",
    "ASSUMED_TOYS": "User defined",
    "BYPASS": "Bypass",
}
ROOTS = {
    "edit": "editViews",
    "source": "sourceViews",
    "mic": "micViews",
    "mix": "mixViews",
    "space": "imageViews",
    "surfaces": "surfacesViews",
    "polar": "polarViews",
}
SIDE = {
    "edit": {"panelRoom": True, "panelListen": False, "panelMics": False, "panelPreview": True, "panelHadamard": False},
    "source": {"panelRoom": True, "panelListen": False, "panelMics": False, "panelPreview": True, "panelHadamard": False},
    "mic": {"panelRoom": False, "panelListen": True, "panelMics": True, "panelPreview": False, "panelHadamard": False},
    "mix": {"panelRoom": False, "panelListen": False, "panelMics": False, "panelPreview": True, "panelHadamard": False},
    "space": {"panelRoom": True, "panelListen": False, "panelMics": False, "panelPreview": False, "panelHadamard": True},
    "surfaces": {"panelRoom": True, "panelListen": False, "panelMics": False, "panelPreview": True, "panelHadamard": False},
    "polar": {"panelRoom": False, "panelListen": True, "panelMics": False, "panelPreview": False, "panelHadamard": False},
}

FAILS = []


def check(ok, msg):
    print(("OK  " if ok else "FAIL") + "  " + msg)
    if not ok:
        FAILS.append(msg)


def chrome_path():
    for c in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if os.path.exists(c):
            return c
    return None


def laws():
    with urllib.request.urlopen(URL.rstrip("/") + "/api/mic_presets", timeout=20) as res:
        data = json.loads(res.read().decode("utf-8"))
    out = {}
    for row in data["presets"]:
        cap = row.get("capsule") or {}
        out[row["mic_id"]] = {
            "family": cap.get("family"),
            "polar": float(cap.get("polar")),
        }
    return out


def visible(page, sel):
    return page.evaluate(
        """(sel) => {
          const e = document.querySelector(sel);
          if (!e) return false;
          const s = getComputedStyle(e);
          if (s.display === 'none' || s.visibility === 'hidden') return false;
          const r = e.getBoundingClientRect();
          return r.width > 0 && r.height > 0;
        }""",
        sel,
    )


def goto_pair(page, setup, mode):
    page.click(".view-tab[data-view=mic]")
    page.select_option("#mic_setup", setup)
    page.wait_for_timeout(250)
    page.select_option("#colour_mode", mode)
    page.wait_for_timeout(400)
    page.wait_for_function(
        "() => { const c = document.getElementById('micPolarL'); return c && c.dataset.drawnFamily; }",
        timeout=8000,
    )


def drawn(page, canvas_id):
    return page.evaluate(
        """(id) => {
          const c = document.getElementById(id);
          return {
            family: c.dataset.drawnFamily,
            polar: Number(c.dataset.drawnPolar),
            yaw: Number(c.dataset.drawnYaw)
          };
        }""",
        canvas_id,
    )


def point_on(box, yaw_deg, theta_deg, radius_frac):
    cx = box["x"] + box["width"] * 0.5
    cy = box["y"] + box["height"] * 0.52
    R = min(box["width"], box["height"]) * 0.38
    th = math.radians(yaw_deg + theta_deg)
    rad = radius_frac * R
    return cx + rad * math.sin(th), cy - rad * math.cos(th), R


def drag(page, x0, y0, x1, y1):
    page.mouse.move(x0, y0)
    page.mouse.down()
    page.mouse.move(x1, y1, steps=8)
    page.mouse.up()
    page.wait_for_timeout(80)


def rim_drag(page, canvas_id, yaw_deg):
    page.locator("#" + canvas_id).scroll_into_view_if_needed()
    box = page.locator("#" + canvas_id).bounding_box()
    x0, y0, R = point_on(box, yaw_deg, 90, 0.5)
    th = math.radians(yaw_deg + 90)
    rad = 0.5 * R + 40
    cx = box["x"] + box["width"] * 0.5
    cy = box["y"] + box["height"] * 0.52
    x1 = cx + rad * math.sin(th)
    y1 = cy - rad * math.cos(th)
    drag(page, x0, y0, x1, y1)


def front_drag(page, canvas_id, yaw_deg):
    page.locator("#" + canvas_id).scroll_into_view_if_needed()
    box = page.locator("#" + canvas_id).bounding_box()
    x0, y0, _R = point_on(box, yaw_deg, 0, 1.0)
    drag(page, x0, y0, x0 + 40, y0)


def near(a, b):
    return abs(float(a) - float(b)) < 0.02


def main():
    preset = laws()
    errors = []
    ch = chrome_path()
    with sync_playwright() as p:
        kw = dict(headless=True, args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        if ch:
            kw["executable_path"] = ch
        browser = p.chromium.launch(**kw)
        try:
            return _run(browser, errors, preset)
        finally:
            browser.close()


def _run(browser, errors, preset):
    with_page = browser.new_page(viewport={"width": 1600, "height": 1000})
    page = with_page
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)

    opts = page.eval_on_selector_all("#colour_mode option", "els => els.map(e => e.textContent.trim())")
    check(opts == ["Measured", "User defined", "Bypass"], "colour options " + json.dumps(opts))

    tabs = page.evaluate("() => [...document.querySelectorAll('.view-tab')].map(e => e.dataset.view)")
    check(tabs == ["edit", "source", "mic", "mix", "space", "surfaces", "polar"], "7 tabs " + json.dumps(tabs))
    check("colour" not in tabs, "no colour tab")

    pal = page.evaluate(
        """() => {
          const P = window.FreqPalette;
          if (!P) return null;
          const lo = P.rgb(0), hi = P.rgb(1);
          const eight = [];
          for (let i = 0; i < 8; i++) eight.push(P.hexAt(i, 8));
          return { lo, hi, eight, src0: P.hexAt(0, 6), src5: P.hexAt(5, 6) };
        }"""
    )
    check(pal is not None, "FreqPalette loaded")
    if pal:
        check(pal["lo"]["r"] > 180 and pal["lo"]["r"] > pal["lo"]["b"] + 80, "lowest band is red " + json.dumps(pal["lo"]))
        check(pal["hi"]["b"] > pal["hi"]["r"] and pal["hi"]["b"] > 120, "highest band is blue/violet " + json.dumps(pal["hi"]))

    for setup in SETUPS:
        for mode in MODES:
            goto_pair(page, setup, mode)
            tag = setup + " / " + MODE_LABEL[mode]
            show = visible(page, "#micEach")
            binaural = setup == "binaural"
            check(show != binaural, tag + " micEach visible=" + str(show))
            lock = visible(page, "#micEachLock")
            owned = mode != "ASSUMED_TOYS"
            check(lock == (owned and not binaural), tag + " lock visible=" + str(lock))
            if show:
                order = page.evaluate(
                    """() => {
                      const wide = document.getElementById('stageWide');
                      const panels = [...wide.children].filter(e => e.classList.contains('panel'));
                      const each = document.getElementById('micEach');
                      const plane = document.querySelector('#stageWide .mic-polar-panel');
                      const a = each.getBoundingClientRect();
                      const b = plane.getBoundingClientRect();
                      return {
                        first: panels[0] && panels[0].id,
                        second: panels[1] && panels[1].className,
                        count: panels.length,
                        above: a.bottom <= b.top + 1,
                        gap: Math.round(b.top - a.bottom)
                      };
                    }"""
                )
                check(order["count"] == 2 and order["first"] == "micEach", tag + " order " + json.dumps(order))
                check(order["above"], tag + " each bottom above source plane " + json.dumps(order))
                cols = page.evaluate(
                    """() => {
                      const cs = getComputedStyle(document.getElementById('micPolarTrio'));
                      const ws = [...document.querySelectorAll('#micPolarTrio .mic-polar-col')].map(e => Math.round(e.getBoundingClientRect().width));
                      return { cols: cs.gridTemplateColumns, ws };
                    }"""
                )
                widths = cols["ws"]
                check(len(widths) == 3 and max(widths) - min(widths) <= 2, tag + " three equal columns " + json.dumps(widths))
            if setup == "mono_c" and show:
                mono = page.evaluate(
                    """() => ({
                      L: document.querySelector('[data-cap=L]').classList.contains('is-unused'),
                      C: document.querySelector('[data-cap=C]').classList.contains('is-unused'),
                      R: document.querySelector('[data-cap=R]').classList.contains('is-unused'),
                      noteL: getComputedStyle(document.querySelector('[data-cap=L] .mic-unused')).display !== 'none',
                      noteC: getComputedStyle(document.querySelector('[data-cap=C] .mic-unused')).display !== 'none'
                    })"""
                )
                check(mono["L"] and mono["R"] and not mono["C"] and mono["noteL"] and not mono["noteC"], tag + " mono dim " + json.dumps(mono))
            foot = page.locator("#micEachFoot").inner_text()
            if mode == "MEASURED_SHELF" and setup == "ortf":
                check("Measured: the preset owns the pattern" in foot and "cardioid" in foot.lower(), tag + " foot " + foot[:140])
            if mode == "BYPASS" and setup == "ortf":
                check(foot.startswith("Bypass: preset pattern, no measured colour"), tag + " bypass foot")
            if mode == "ASSUMED_TOYS" and setup == "ortf":
                check("Drag the rim to set the pattern." in foot and "preset pattern" not in foot, tag + " user foot")
            if setup == "ms_classic":
                check("M/S: S is a fixed figure-8" in foot, tag + " ms note")
                check("fig-8" not in page.locator("#patternLockSide").inner_text().lower() and "fig\u20118" not in page.locator("#patternLockSide").inner_text().lower(), tag + " side lock is the preset, not fig-8")
            if setup not in ("binaural", "mono_c"):
                row = page.evaluate(
                    """() => {
                      const e = document.getElementById('side_split');
                      const row = e && e.closest('label');
                      if (!row) return false;
                      return getComputedStyle(row).display !== 'none' && !row.closest('[hidden]');
                    }"""
                )
                check(row, tag + " side_split row visible")

    # Drawn law. ORTF measured matches the preset. MS classic L/R is the fixed figure-8.
    goto_pair(page, "ortf", "MEASURED_SHELF")
    side_id = page.input_value("#mic_preset_side")
    centre_id = page.input_value("#mic_preset_centre")
    law_s = preset[side_id]
    law_c = preset[centre_id]
    for cid, law in (("#micPolarL", law_s), ("#micPolarC", law_c), ("#micPolarR", law_s)):
        d = drawn(page, cid[1:])
        check(d["family"] == law["family"] and near(d["polar"], law["polar"]), "ORTF measured " + cid + " drawn " + json.dumps(d) + " law " + json.dumps(law))
    page.wait_for_function(
        "() => document.querySelectorAll('#micRingLegend .mic-ring-swatch').length >= 2",
        timeout=8000,
    )
    legend = page.evaluate(
        """() => {
          const sw = [...document.querySelectorAll('#micRingLegend .mic-ring-swatch')];
          const bg = (el) => getComputedStyle(el).backgroundColor;
          const P = window.FreqPalette;
          const n = sw.length;
          return { n, first: bg(sw[0]), last: bg(sw[n - 1]), wantFirst: P.cssAt(0, n), wantLast: P.cssAt(n - 1, n) };
        }"""
    )
    check(legend["first"].replace(" ", "") == legend["wantFirst"].replace(" ", ""), "ring legend low " + json.dumps(legend))
    check(legend["last"].replace(" ", "") == legend["wantLast"].replace(" ", ""), "ring legend high " + json.dumps(legend))

    goto_pair(page, "ms_classic", "MEASURED_SHELF")
    for cid in ("micPolarL", "micPolarR"):
        d = drawn(page, cid)
        check(d["family"] == "bi" and near(d["polar"], 0.5), "MS classic measured " + cid + " figure-8 " + json.dumps(d))
    dC = drawn(page, "micPolarC")
    check(dC["family"] == law_c["family"] and near(dC["polar"], law_c["polar"]), "MS classic measured centre is the mid " + json.dumps(dC))

    # Rim and front drags on ORTF.
    for mode in MODES:
        page.select_option("#colour_mode", mode)
        page.select_option("#mic_setup", "ortf")
        page.wait_for_timeout(400)
        page.wait_for_function("() => document.getElementById('micPolarL').dataset.drawnFamily")
        before = {cid: drawn(page, cid) for cid in ("micPolarL", "micPolarC", "micPolarR")}
        rim_drag(page, "micPolarL", before["micPolarL"]["yaw"])
        rim_drag(page, "micPolarC", before["micPolarC"]["yaw"])
        rim_drag(page, "micPolarR", before["micPolarR"]["yaw"])
        after = {cid: drawn(page, cid) for cid in ("micPolarL", "micPolarC", "micPolarR")}
        same = all(near(before[c]["polar"], after[c]["polar"]) for c in before)
        changed = any(not near(before[c]["polar"], after[c]["polar"]) for c in before)
        if mode == "ASSUMED_TOYS":
            check(changed, "user defined rim drag changes polar " + json.dumps({"before": before, "after": after}))
        else:
            check(same, MODE_LABEL[mode] + " rim drag leaves polar " + json.dumps({"before": before, "after": after}))
        yaw0 = drawn(page, "micPolarL")["yaw"]
        front_drag(page, "micPolarL", yaw0)
        yaw1 = drawn(page, "micPolarL")["yaw"]
        check(yaw1 != yaw0, MODE_LABEL[mode] + " front drag aims " + str(yaw0) + " -> " + str(yaw1))

    # Polar tab round trip.
    page.select_option("#mic_setup", "ortf")
    page.click(".view-tab[data-view=polar]")
    page.click("[data-polar-page=each]")
    page.wait_for_timeout(400)
    parent = page.evaluate("() => document.getElementById('micPolarTrio').parentElement.id")
    check(parent == "polarEachHost", "polar each hosts the trio (" + parent + ")")
    page.click(".view-tab[data-view=mic]")
    page.wait_for_timeout(400)
    back = page.evaluate(
        """() => {
          const t = document.getElementById('micPolarTrio');
          return { parent: t.parentElement.id, next: t.nextElementSibling && t.nextElementSibling.id };
        }"""
    )
    check(back["parent"] == "micEach" and back["next"] == "micEachFoot", "trio returns above the foot " + json.dumps(back))

    # Layout at 1600.
    page.click(".view-tab[data-view=mic]")
    page.select_option("#mic_setup", "ortf")
    page.select_option("#colour_mode", "MEASURED_SHELF")
    page.wait_for_timeout(500)
    lay = page.evaluate(
        """() => {
          const box = (sel) => {
            const e = document.querySelector(sel);
            if (!e) return null;
            const r = e.getBoundingClientRect();
            return { w: Math.round(r.width), h: Math.round(r.height) };
          };
          const mics = document.getElementById('panelMics');
          const tools = document.querySelector('.mic-polar-tools');
          const plane = document.querySelector('#stageWide .mic-polar-panel');
          return {
            micsInSidebar: !!(mics && mics.closest('.sidebar')),
            plane: box('#stageWide .mic-polar-panel'),
            hero: box('#micHeroWrap'),
            top: box('#micFloorCanvas'),
            combined: box('#mic3dCanvas'),
            toolsInPlane: !!(tools && plane && plane.contains(tools))
          };
        }"""
    )
    check(lay["micsInSidebar"], "panelMics in sidebar")
    check(lay["plane"] and lay["plane"]["w"] >= 1500, "source plane width " + json.dumps(lay["plane"]))
    check(lay["hero"] and lay["hero"]["w"] >= 1400 and lay["hero"]["h"] >= 560, "hero " + json.dumps(lay["hero"]))
    check(lay["top"] and lay["top"]["w"] >= 520 and lay["top"]["h"] >= 540, "top canvas " + json.dumps(lay["top"]))
    check(lay["combined"] and lay["combined"]["w"] >= 520 and lay["combined"]["h"] >= 540, "combined canvas " + json.dumps(lay["combined"]))
    check(not lay["toolsInPlane"], "mic tools outside the source plane")

    # Source frequency chips use the same palette. 250 is the low end.
    page.click(".view-tab[data-view=source]")
    page.wait_for_timeout(400)
    chips = page.evaluate(
        """() => {
          const P = window.FreqPalette;
          const btns = [...document.querySelectorAll('[data-src-freq]')];
          const norm = (s) => String(s).replace(/\\s+/g, '').toLowerCase();
          return btns.map((b, i) => {
            const want = P.cssAt(i, btns.length);
            return { f: b.getAttribute('data-src-freq'), hit: norm(getComputedStyle(b).boxShadow).indexOf(norm(want)) >= 0, want };
          });
        }"""
    )
    if chips:
        check(chips[0]["hit"] and chips[0]["f"] == "250", "source 250 uses palette low " + json.dumps(chips[0]))
        check(chips[-1]["hit"] and chips[-1]["f"] == "8000", "source 8k uses palette high " + json.dumps(chips[-1]))

    # Surfaces: room colour is on this tab. Now/Last legend stays; octave labels are frequency colours.
    page.click(".view-tab[data-view=surfaces]")
    page.wait_for_timeout(500)
    check(visible(page, "#colourCanvas"), "room colour analyser on Surfaces")
    check(visible(page, "#absorbCanvas") and visible(page, "#eqCanvas"), "absorb and EQ graphs on Surfaces")
    check(not visible(page, "#micEach"), "mic each hidden off the Mic tab")

    # Tab tour: each tab shows its stage and its sidebar panels.
    for view, root in ROOTS.items():
        page.click(".view-tab[data-view=" + view + "]")
        page.wait_for_timeout(300)
        for other, oid in ROOTS.items():
            vis = visible(page, "#" + oid)
            check(vis == (other == view), view + " shows " + oid + "=" + str(vis))
        wide = visible(page, "#stageWide")
        check(wide == (view == "mic"), view + " stageWide=" + str(wide))
        side = page.evaluate(
            """(ids) => {
              const out = {};
              Object.keys(ids).forEach(id => {
                const e = document.getElementById(id);
                out[id] = !!(e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0);
              });
              const adv = document.getElementById('panelAdvanced');
              out.panelAdvanced = !!(adv && getComputedStyle(adv).display !== 'none');
              return out;
            }""",
            SIDE[view],
        )
        for sid, want in SIDE[view].items():
            check(side.get(sid) == want, view + " sidebar " + sid + "=" + str(side.get(sid)))
        check(side.get("panelAdvanced") is True, view + " advanced stays")

    # Screenshots of the Mic stage at 1600.
    shots = {
        ("ortf", "MEASURED_SHELF"): "mic_each_measured_1600.png",
        ("ortf", "ASSUMED_TOYS"): "mic_each_user_1600.png",
        ("ortf", "BYPASS"): "mic_each_bypass_1600.png",
        ("ms_classic", "MEASURED_SHELF"): "mic_each_ms_classic_measured_1600.png",
    }
    for (setup, mode), name in shots.items():
        goto_pair(page, setup, mode)
        page.locator("#stageWide").screenshot(path=os.path.join(SHOTS, name))
        print("SHOT", os.path.join(SHOTS, name))

    # Narrow viewport: three columns become one, and the panel is still there.
    # A JS click: at 390px the scrolled sidebar covers the tab bar, so a hit-test click times out.
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("() => { window.scrollTo(0, 0); document.querySelector('.view-tab[data-view=mic]').click(); }")
    page.select_option("#mic_setup", "ortf")
    page.select_option("#colour_mode", "MEASURED_SHELF")
    page.wait_for_timeout(400)
    narrow = page.evaluate(
        """() => {
          const each = document.getElementById('micEach');
          const cs = getComputedStyle(document.getElementById('micPolarTrio'));
          const plane = document.querySelector('#stageWide .mic-polar-panel');
          const a = each.getBoundingClientRect();
          const b = plane.getBoundingClientRect();
          return {
            shown: getComputedStyle(each).display !== 'none',
            cols: cs.gridTemplateColumns,
            above: a.bottom <= b.top + 1
          };
        }"""
    )
    check(narrow["shown"] and narrow["above"], "mobile each above source plane " + json.dumps(narrow))
    check(narrow["cols"].count(" ") == 0 or "1fr" == narrow["cols"].strip(), "mobile stacks the trio " + narrow["cols"])

    # 1920: still three equal columns, full width.
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.wait_for_timeout(300)
    wide_cols = page.evaluate(
        """() => {
          const ws = [...document.querySelectorAll('#micPolarTrio .mic-polar-col')].map(e => Math.round(e.getBoundingClientRect().width));
          const plane = document.querySelector('#stageWide .mic-polar-panel').getBoundingClientRect();
          return { ws, plane: Math.round(plane.width) };
        }"""
    )
    check(max(wide_cols["ws"]) - min(wide_cols["ws"]) <= 2 and wide_cols["plane"] >= 1500, "1920 columns " + json.dumps(wide_cols))

    check(not errors, "console errors " + json.dumps(errors[:6]))

    print("FAILS", len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
