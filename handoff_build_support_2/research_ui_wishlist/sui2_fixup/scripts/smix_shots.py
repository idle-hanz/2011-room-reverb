"""S-MIX screenshots, pixel check, and tab tour. Windows Chrome. Does not edit tour.py."""
from __future__ import annotations

import json
import os
import sys

from playwright.sync_api import sync_playwright

ROOT_EARLY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT_EARLY, "software", "tests")]
import test_smix_desk as T  # noqa: E402

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:7860/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SHOT = os.path.join(ROOT, "handoff_build_support_2", "research_ui_wishlist", "sui2_fixup", "shots")
DATA = os.path.join(ROOT, "handoff_build_support_2", "research_ui_wishlist", "data")
os.makedirs(SHOT, exist_ok=True)
os.makedirs(DATA, exist_ok=True)

CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CH):
    alt = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    CH = alt if os.path.exists(alt) else ""


def set_range(pg, sel, value):
    pg.eval_on_selector(
        sel,
        """(el, v) => { el.value = String(v); el.dispatchEvent(new Event('input', {bubbles:true})); }""",
        value,
    )


def wait_polar(pg):
    pg.wait_for_function(
        """() => {
          const d = window.micDesk;
          if (!d || !d.drawnGrid) return false;
          const g = d.drawnGrid('L');
          const pts = d.drawnPoints('L') || [];
          return !!(g && g.length && pts.length);
        }""",
        timeout=20000,
    )


def choose(pg, sel, value):
    cur = pg.eval_on_selector(sel, "el => el.value")
    if cur == value:
        return False
    with pg.expect_response(lambda r: "/api/polar" in r.url and r.status == 200, timeout=20000):
        pg.select_option(sel, value)
    return True


def main():
    log = {"pixel": [], "tour": {}, "console": [], "dialogs": [], "data_db": []}
    fail = []
    allow_replace = {"on": False}
    with sync_playwright() as p:
        kw = dict(headless=True, args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        if CH:
            kw["executable_path"] = CH
        b = p.chromium.launch(**kw)
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        def on_dialog(d):
            msg = d.message
            if allow_replace["on"] and "Replace the desk" in msg:
                log["dialogs"].append(["accept", msg])
                d.accept()
                return
            log["dialogs"].append(["unexpected", msg])
            fail.append("dialog: " + msg)
            d.dismiss()

        polar_cap = {}

        def on_resp(resp):
            if "/api/polar" not in resp.url or resp.status != 200:
                return
            try:
                polar_cap["body"] = json.loads(resp.request.post_data or "{}")
                polar_cap["data"] = resp.json()
            except Exception as exc:
                polar_cap["err"] = str(exc)

        pg.on("dialog", on_dialog)
        pg.on("response", on_resp)
        pg.on("console", lambda m: log["console"].append((m.type, m.text[:240])) if m.type == "error" else None)
        pg.on("pageerror", lambda e: log["console"].append(("pageerror", str(e)[:300])))
        pg.goto(URL)
        pg.wait_for_timeout(3500)
        # Mic desk is inside the app closure. Expose drawn grids by reading canvases after the fetch.
        pg.evaluate(
            """() => {
              const tag = document.querySelector('script[src*="mic_desk"]');
              window.__shot = { tag: tag ? tag.getAttribute('src') : null };
            }"""
        )

        def shot(name):
            pg.screenshot(path=os.path.join(SHOT, name), full_page=False)

        def shot_each(name):
            panel = pg.locator("#micEach")
            panel.scroll_into_view_if_needed()
            panel.screenshot(path=os.path.join(SHOT, name))

        def open_mic():
            pg.click(".view-tab[data-view=mic]")
            pg.wait_for_timeout(600)

        def colour(mode):
            choose(pg, "#colour_mode", mode)
            if mode != "ASSUMED_TOYS":
                wait_polar(pg)
            else:
                pg.wait_for_timeout(400)

        def setup(sid):
            open_mic()
            choose(pg, "#mic_setup", sid)
            pg.wait_for_timeout(400)

        # Item 11 cases. Colour is set after the setup, so a User-defined switch can be undone.
        cases = [
            ("ab_omni", "ab_omni", None),
            ("ortf", "ortf", None),
            ("ms", "ms", None),
            ("split", "ortf", "split"),
        ]
        for name, sid, extra in cases:
            setup(sid)
            if extra == "split":
                colour("MEASURED_SHELF")
                pg.click("#side_split")
                pg.wait_for_function(
                    """() => [...document.querySelectorAll('#mic_preset_r option')].some(o => o.value === 'AKGC414Omni')""",
                    timeout=15000,
                )
                with pg.expect_response(lambda r: "/api/polar" in r.url and r.status == 200, timeout=20000):
                    pg.select_option("#mic_preset_r", "AKGC414Omni")
                pg.click(".view-tab[data-view=mix]")
                pg.wait_for_timeout(300)
                pg.click('[data-place="r"][data-name="room"]')
                set_range(pg, "#room_x", 4)
                set_range(pg, "#room_yaw", 20)
                allow_replace["on"] = True
                open_mic()
                pg.wait_for_timeout(300)
            for mode, leaf in (
                ("MEASURED_SHELF", "measured"),
                ("BYPASS", "bypass"),
                ("ASSUMED_TOYS", "user"),
            ):
                colour(mode)
                pg.wait_for_timeout(700)
                shot_each(f"mic_each_{name}_{leaf}_smix.png")
                api_each = (polar_cap.get("data") or {}).get("each_db") or {}
                grids = pg.evaluate(
                    """(api) => {
                      const desk = window.micDesk;
                      if (!desk || !desk.drawnGrid) return { missing: true };
                      const out = {};
                      ['L','C','R'].forEach(cap => {
                        const canvas = document.getElementById('micPolar' + cap);
                        const grid = desk.drawnGrid(cap);
                        const pts = desk.drawnPoints(cap) || [];
                        if (!canvas || !grid || !grid.length) { out[cap] = { maxPx: null, n: 0, dataMax: null }; return; }
                        const w = canvas.width, h = canvas.height;
                        const cx = w * 0.5, cy = h * 0.52, R = Math.min(w, h) * 0.38;
                        const yaw = (Number(canvas.dataset.drawnYaw) || 0) * Math.PI / 180;
                        const nAz = grid[0].length;
                        let max = 0;
                        pts.forEach(p => {
                          let db = Number(p.db);
                          if (!(db > -30)) db = -30;
                          if (db > 0) db = 0;
                          const g = (db + 30) / 30;
                          const theta = (p.az / nAz) * Math.PI * 2;
                          const screen = theta + yaw;
                          const sx = cx + R * g * Math.sin(screen);
                          const sy = cy - R * g * Math.cos(screen);
                          const d = Math.hypot(sx - p.x, sy - p.y);
                          if (d > max) max = d;
                        });
                        let dataMax = null;
                        const ref = api && api[cap];
                        if (ref && ref.length) {
                          dataMax = 0;
                          for (let bi = 0; bi < grid.length; bi++) {
                            for (let ai = 0; ai < nAz; ai++) {
                              const rv = Number(ref[bi][ai]);
                              if (!(rv > -30)) continue;
                              const dv = Math.abs(Number(grid[bi][ai]) - rv);
                              if (dv > dataMax) dataMax = dv;
                            }
                          }
                        }
                        out[cap] = { maxPx: max, n: pts.length, dataMax: dataMax };
                      });
                      const sw = [...document.querySelectorAll('#micRingLegend .mic-ring-swatch')].map(e => e.style.background || getComputedStyle(e).backgroundColor);
                      out.legend = sw;
                      return out;
                    }""",
                    api_each,
                )
                entry = {"case": name, "mode": mode, "canvas": grids}
                if mode != "ASSUMED_TOYS":
                    api = (polar_cap.get("data") or {}).get("each_db") or {}
                    body = polar_cap.get("body") or {}
                    deltas = {}
                    if polar_cap.get("err"):
                        fail.append(f"{name} {mode} polar capture {polar_cap['err']}")
                    else:
                        try:
                            p = T.A.params_from_body(body)
                            for key, slot in (("L", "l"), ("C", "c"), ("R", "r")):
                                d = T._max_db_delta(
                                    api[key], mode,
                                    p["mic_preset_" + slot], p["family_" + slot],
                                    p["polar_" + slot], p["pattern_" + slot],
                                )
                                deltas[key] = d
                                if d > 0.01:
                                    fail.append(f"{name} {mode} {key} data {d}")
                        except Exception as exc:
                            fail.append(f"{name} {mode} data {type(exc).__name__}: {exc}")
                    entry["engine_db"] = deltas
                    drawn_bad = grids.get("missing") if isinstance(grids, dict) else True
                    if drawn_bad:
                        fail.append(f"{name} {mode} drawn grid missing")
                    elif isinstance(grids, dict):
                        for cap in ("L", "C", "R"):
                            cell = grids.get(cap) or {}
                            px = cell.get("maxPx")
                            n = cell.get("n") or 0
                            if px is None or n < 8 or px > 1:
                                fail.append(f"{name} {mode} {cap} pixel {px} n {n}")
                            if cell.get("dataMax") is None or cell.get("dataMax") > 0.01:
                                fail.append(f"{name} {mode} {cap} drawn {cell.get('dataMax')}")
                log["pixel"].append(entry)
                log["data_db"].append({"case": name, "mode": mode, "engine_db": entry.get("engine_db")})
                print(name, leaf, entry.get("engine_db"), {k: (grids.get(k) or {}).get("maxPx") if isinstance(grids, dict) else None for k in ("L", "C", "R")})
                if name == "ortf" and leaf == "measured":
                    # Measured, so the pending note is not skipped by the User-defined drawer.
                    pg.evaluate("() => window.micDesk && window.micDesk.setPolarStatus('pending')")
                    pg.wait_for_timeout(200)
                    shot_each("mic_each_ortf_pending_smix.png")
                    colour("MEASURED_SHELF")

        # Badges in three colour modes, ORTF, plus the stack and the legend.
        setup("ortf")
        for mode, leaf in (
            ("MEASURED_SHELF", "measured"),
            ("BYPASS", "bypass"),
            ("ASSUMED_TOYS", "user"),
        ):
            colour(mode)
            badge = pg.locator("#micHonestyBadge")
            badge.screenshot(path=os.path.join(SHOT, f"badge_{leaf}_smix.png"))
        pg.locator("#mic3dCanvas").screenshot(path=os.path.join(SHOT, "stack_top_smix.png"))
        legend = pg.locator("#micRingLegend")
        if legend.count():
            legend.screenshot(path=os.path.join(SHOT, "mic_legend_smix.png"))

        # MS classic figure-8 strip.
        setup("ms_classic")
        colour("ASSUMED_TOYS")
        pg.locator("#micPolarL").screenshot(path=os.path.join(SHOT, "ms_fig8_L_smix.png"))

        # Idle's mix: MS classic, R room, pan +0.3 at -6 dB, L width +2.
        setup("ms_classic")
        pg.click(".view-tab[data-view=mix]")
        pg.wait_for_timeout(400)
        pg.click('[data-place="r"][data-name="room"]')
        set_range(pg, "#room_x", 4)
        set_range(pg, "#room_z", 2)
        set_range(pg, "#room_y", 1.5)
        set_range(pg, "#room_yaw", 0)
        mute = pg.locator("#mute_r")
        if mute.get_attribute("aria-pressed") == "true":
            mute.click()
        set_range(pg, "#pan_r", 0.3)
        set_range(pg, "#fader_r", 0.42)
        set_range(pg, "#width_l", 2)
        pg.wait_for_timeout(400)
        shot("mix_scenario_smix.png")
        log["matrix"] = pg.locator("#deskMatrix").inner_text()

        # At speakers page.
        pg.click(".view-tab[data-view=polar]")
        pg.wait_for_timeout(400)
        pg.click('[data-polar-page="speakers"]')
        pg.wait_for_timeout(1200)
        shot("polar_speakers_smix.png")

        # Tab tour on the current seven tabs.
        tabs = pg.evaluate("""() => [...document.querySelectorAll('.view-tab')].map(e => e.dataset.view)""")
        pg.click(".view-tab[data-view=mic]")
        pg.select_option("#mic_setup", "ortf")
        pg.wait_for_timeout(500)
        for t in tabs:
            pg.click(f".view-tab[data-view={t}]")
            pg.wait_for_timeout(700)
            panels = pg.evaluate(
                """() => [...document.querySelectorAll('.sidebar > .panel, .sidebar > details')]
                  .filter(e => e.offsetParent !== null)
                  .map(e => e.id)"""
            )
            log["tour"][t] = panels
            pg.screenshot(path=os.path.join(SHOT, f"tour_ortf_{t}_smix.png"))
        b.close()
    out = os.path.join(DATA, "smix_shots.json")
    json.dump(log, open(out, "w"), indent=1)
    print("matrix", log.get("matrix"))
    print("tour", log["tour"])
    print("console", len(log["console"]))
    print("fail", fail)
    print("wrote", out)
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
