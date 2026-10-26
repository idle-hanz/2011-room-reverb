"""S-AUDIT UI gates. Playwright against a local server. Audio bytes are not this file's job."""
from __future__ import annotations

import base64
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
PY = SW / ".venv" / "Scripts" / "python.exe"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
if not CHROME.exists():
    alt = Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
    CHROME = alt if alt.exists() else Path()


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _tiny_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(struct.pack("<" + "h" * 480, *([0] * 480)))


def _public(body: dict) -> dict:
    return {k: v for k, v in body.items() if not str(k).startswith("_")}


def _grab_params(raw: bytes) -> dict:
    text = raw.decode("utf-8", "replace")
    m = re.search(r'name="params_json"\r?\n\r?\n(\{.*\})\r?\n--', text, re.S)
    if not m:
        raise AssertionError("params_json missing from render post")
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def audit_server(tmp_path_factory):
    if not CHROME.exists():
        pytest.fail("Chrome is not installed; the A1 Playwright gate cannot run")
    port = _free_port()
    wav = tmp_path_factory.mktemp("saudit") / "burst.wav"
    _tiny_wav(wav)
    # publish_out_copy keeps ten stamps in the out.wav folder and deletes the
    # oldest. Point this server at a temp folder so the pinned listen wav stays.
    boot = (
        "import tempfile\n"
        "from pathlib import Path\n"
        "import app_server\n"
        "d = Path(tempfile.mkdtemp(prefix='rr_audit_renders_'))\n"
        "app_server.default_out_path = lambda: d / 'out.wav'\n"
        "import uvicorn\n"
        f"uvicorn.run(app_server.app, host='127.0.0.1', port={port}, log_level='warning')\n"
    )
    proc = subprocess.Popen(
        [str(PY), "-c", boot],
        cwd=str(SW),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}/"
    deadline = time.time() + 30
    up = False
    while time.time() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
            pytest.fail("server exited: " + err[-500:])
        try:
            with socket.create_connection(("127.0.0.1", port), 0.3):
                up = True
                break
        except OSError:
            time.sleep(0.15)
    if not up:
        proc.kill()
        pytest.fail("server did not listen")
    yield {"url": url, "wav": str(wav), "proc": proc}
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _posted(url: str, wav: str, seq: list[str]) -> dict:
    from playwright.sync_api import sync_playwright

    caps: list[dict] = []

    def on_route(route, req):
        caps.append(_grab_params(req.post_data_buffer or b""))
        route.fulfill(status=200, content_type="application/json", body='{"ok":true,"status":"stub"}')

    with sync_playwright() as p:
        b = p.chromium.launch(
            executable_path=str(CHROME),
            headless=True,
            args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        pg.route("**/api/render", on_route)
        with pg.expect_response(lambda r: r.url.endswith("/api/defaults") and r.status == 200, timeout=20000):
            pg.goto(url)
        pg.wait_for_timeout(600)
        pg.set_input_files("#wavInput", wav)
        pg.wait_for_timeout(300)
        pg.on("dialog", lambda d: d.accept())
        for name in seq:
            pg.click(f"#placeRow [data-place={name}]")
            pg.wait_for_timeout(400)
        n = len(caps)
        pg.click("#renderBtn")
        for _ in range(80):
            if len(caps) > n:
                break
            pg.wait_for_timeout(50)
        b.close()
    assert caps, "render did not post"
    return _public(caps[-1])


@pytest.mark.slow
def test_a1_place_orders_match_fresh(audit_server):
    """All 9 X→Y posts equal Y clicked fresh. Studio decay_s is 1.80. Club decay_s is 1.80."""
    url = audit_server["url"]
    wav = audit_server["wav"]
    places = ("studio", "club", "hall")
    fresh = {y: _posted(url, wav, [y]) for y in places}
    assert fresh["studio"].get("decay_s") == pytest.approx(1.8)
    assert fresh["studio"].get("decay_lock") is True
    assert fresh["club"].get("decay_s") == pytest.approx(1.8)
    assert fresh["club"].get("decay_lock") is True
    for x in places:
        for y in places:
            got = _posted(url, wav, [x, y])
            diffs = []
            keys = set(got) | set(fresh[y])
            for k in sorted(keys):
                if got.get(k) != fresh[y].get(k):
                    diffs.append(k)
            assert not diffs, f"{x}->{y} leaked {diffs[:12]}"


_VIEWS = ["edit", "source", "mic", "mix", "space", "surfaces", "polar"]
_COLOURS = ["MEASURED_SHELF", "ASSUMED_TOYS", "BYPASS"]


def _rects_overlap(a, b) -> bool:
    return a["x"] < b["x"] + b["width"] - 1 and a["x"] + a["width"] - 1 > b["x"] and a["y"] < b["y"] + b["height"] - 1 and a["y"] + a["height"] - 1 > b["y"]


@pytest.mark.slow
def test_a2_phone_tabs(audit_server):
    """390 px: every tab is hit-testable, no page scroll, sidebar does not cover the stage.

    1600 px identity was checked against the pre-CSS shots (0 pixels outside canvases
    on all 7 tabs). Later items change the header on purpose, so that compare stays
    a one-time gate rather than a frozen screenshot of every later control.
    """
    from playwright.sync_api import sync_playwright

    url = audit_server["url"]
    with sync_playwright() as p:
        b = p.chromium.launch(
            executable_path=str(CHROME),
            headless=True,
            args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        phone = b.new_page(viewport={"width": 390, "height": 844})
        phone.goto(url)
        phone.wait_for_timeout(800)
        leaks = []
        shots = ROOT / "handoff_build_support_2" / "research_ui_wishlist" / "s_audit" / "shots_s_audit"
        shots.mkdir(parents=True, exist_ok=True)
        for mode in _COLOURS:
            phone.evaluate(
                """(mode) => {
                  const el = document.getElementById('colour_mode');
                  el.value = mode;
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                }""",
                mode,
            )
            phone.wait_for_timeout(80)
            for view in _VIEWS:
                phone.click(f'.view-tab[data-view="{view}"]')
                phone.wait_for_timeout(120)
                report = phone.evaluate(
                    """(views) => {
                      const sw = document.documentElement.scrollWidth;
                      const stage = document.querySelector('.stage').getBoundingClientRect();
                      const side = document.querySelector('.sidebar').getBoundingClientRect();
                      const hits = views.map((v) => {
                        const el = document.querySelector('.view-tab[data-view="' + v + '"]');
                        const r = el.getBoundingClientRect();
                        const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
                        return { v: v, ok: !!(hit && (hit === el || el.contains(hit))) };
                      });
                      return { sw: sw, stage: stage.toJSON(), side: side.toJSON(), hits: hits };
                    }""",
                    _VIEWS,
                )
                if report["sw"] > 391:
                    leaks.append(f"{mode}/{view} scrollWidth {report['sw']}")
                if _rects_overlap(report["stage"], report["side"]):
                    leaks.append(f"{mode}/{view} sidebar overlaps stage")
                for hit in report["hits"]:
                    if not hit["ok"]:
                        leaks.append(f"{mode}/{view} tab {hit['v']} not hit")
                if mode == "MEASURED_SHELF":
                    phone.screenshot(path=str(shots / f"a2_390_{view}.png"), full_page=True)
        assert not leaks, leaks[:12]
        b.close()


def _chrome():
    from playwright.sync_api import sync_playwright

    p = sync_playwright().start()
    b = p.chromium.launch(
        executable_path=str(CHROME),
        headless=True,
        args=[
            "--use-gl=angle",
            "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader",
            "--autoplay-policy=no-user-gesture-required",
        ],
    )
    return p, b


def _shots():
    d = ROOT / "handoff_build_support_2" / "research_ui_wishlist" / "s_audit" / "shots_s_audit"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.mark.slow
def test_a4_binaural_hides_dead_rows(audit_server):
    """Binaural hides the dead rows. Other setups show them. Posted keys do not grow, except the XY room mic."""
    p, b = _chrome()
    try:
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        posts = []

        def on_route(route):
            posts.append(json.loads(route.request.post_data or "{}"))
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"ok":false,"error":"stub"}',
            )

        pg.route("**/api/live_params", on_route)
        pg.goto(audit_server["url"])
        pg.wait_for_timeout(700)
        pg.evaluate("() => { window.LiveFDN.isRunning = () => true; }")
        pg.click('.view-tab[data-view="mic"]')
        pg.wait_for_timeout(300)

        def flags():
            return pg.evaluate(
                """() => {
                  function hid(id) {
                    const n = document.getElementById(id);
                    if (!n) return true;
                    if (n.hidden) return true;
                    return getComputedStyle(n).display === 'none';
                  }
                  const c = document.querySelector('#micPolarTrio .mic-polar-col[data-cap="C"]');
                  return {
                    colour: hid('colourModeRow'),
                    align: hid('alignHorizontalRow'),
                    centre: hid('centreMicChoice'),
                    side: hid('sideMicChoice'),
                    ccol: !c || c.hidden === true
                  };
                }"""
            )

        pg.select_option("#mic_setup", "ortf")
        pg.wait_for_timeout(200)
        shown = flags()
        assert shown == {
            "colour": False, "align": False,
            "centre": False, "side": False, "ccol": False,
        }, shown
        n = len(posts)
        pg.select_option("#mic_setup", "binaural")
        pg.wait_for_timeout(400)
        hidden = flags()
        assert hidden == {
            "colour": True, "align": True,
            "centre": True, "side": True, "ccol": True,
        }, hidden
        meta = pg.locator("#micHeroMeta").inner_text()
        assert "head" in meta.lower(), meta
        pg.screenshot(path=str(_shots() / "a4_binaural_mic.png"))
        assert len(posts) > n, "binaural did not post live_params"
        binaural = posts[-1]
        assert binaural.get("mic_setup") == "binaural"
        assert not any("hidden" in k or k.endswith("Row") for k in binaural)
        pg.select_option("#mic_setup", "xy_90")
        pg.wait_for_timeout(200)
        again = flags()
        assert again["colour"] is False and again["side"] is False and again["ccol"] is False
        keys_xy = set(posts[-1])
        keys_bin = set(binaural)
        # c097da6: XY 90 places the centre mic in the room, so Play posts that spot.
        # Binaural has no centre room mic, so those three keys stay off its post.
        extra = keys_xy - keys_bin
        missing = keys_bin - keys_xy
        assert missing == set(), sorted(missing)[:20]
        assert extra <= {"mic_x_c", "mic_y_c", "mic_z_c"}, sorted(extra)[:20]
    finally:
        b.close()
        p.stop()


@pytest.mark.slow
def test_a5_stop_suspends_and_play_resumes(audit_server):
    p, b = _chrome()
    try:
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto(audit_server["url"])
        pg.wait_for_timeout(600)
        pg.set_input_files("#wavInput", audit_server["wav"])
        pg.click("#liveBtn")
        pg.wait_for_function(
            "() => window.LiveFDN && LiveFDN.isRunning() && LiveFDN.audioState() === 'running'",
            timeout=20000,
        )
        pg.click("#liveBtn")
        pg.wait_for_function(
            "() => window.LiveFDN && !LiveFDN.isRunning() && LiveFDN.audioState() === 'suspended'",
            timeout=8000,
        )
        pg.click("#liveBtn")
        pg.wait_for_function(
            "() => window.LiveFDN && LiveFDN.isRunning() && LiveFDN.audioState() === 'running'",
            timeout=20000,
        )
    finally:
        b.close()
        p.stop()


@pytest.mark.slow
def test_a9_focus_mic_screenshot(audit_server):
    p, b = _chrome()
    try:
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        pg.goto(audit_server["url"])
        pg.wait_for_timeout(800)
        pg.click('.view-tab[data-view="mic"]')
        pg.wait_for_timeout(1200)
        box = pg.locator("#mic3dCanvas").bounding_box()
        assert box and box["width"] > 80 and box["height"] > 80
        pg.screenshot(path=str(_shots() / "a9_focus_mic.png"))
    finally:
        b.close()
        p.stop()


@pytest.mark.slow
def test_a10_header_status_on_every_tab(audit_server):
    p, b = _chrome()
    try:
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.route(
            "**/api/live_params",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"ok":false,"error":"forced live_params error"}',
            ),
        )
        pg.goto(audit_server["url"])
        pg.wait_for_timeout(700)
        pg.evaluate("() => { window.LiveFDN.isRunning = () => true; }")
        for view in _VIEWS:
            pg.click(f'.view-tab[data-view="{view}"]')
            pg.wait_for_timeout(80)
            pg.evaluate(
                """() => {
                  const el = document.getElementById('W');
                  el.value = String(Number(el.value) + 0.1);
                  el.dispatchEvent(new Event('input', { bubbles: true }));
                }"""
            )
            pg.wait_for_timeout(200)
            text = pg.locator("#headerStatus").inner_text()
            assert "forced live_params error" in text, view
            box = pg.locator("#headerStatus").bounding_box()
            assert box and box["width"] > 8 and box["height"] > 4, view
            vis = pg.evaluate(
                """() => {
                  const el = document.getElementById('headerStatus');
                  const s = getComputedStyle(el);
                  const r = el.getBoundingClientRect();
                  return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.bottom > 0;
                }"""
            )
            assert vis, view
    finally:
        b.close()
        p.stop()


@pytest.mark.slow
def test_a11_source_labels_omni_and_stale_reply(audit_server):
    """(a)(b) screenshots. (c) a late /api/images body does not replace a newer one."""
    p, b = _chrome()
    try:
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        pg.goto(audit_server["url"])
        pg.wait_for_timeout(700)
        pg.click('.view-tab[data-view="source"]')
        pg.wait_for_timeout(500)
        assert pg.locator("#sourceOnset").is_hidden()
        pg.screenshot(path=str(_shots() / "a11b_omni_polar.png"))
        pg.locator("#srcFloorCanvas").screenshot(path=str(_shots() / "a11a_source_floor.png"))

        held = []

        def grab(route):
            held.append(route)

        pg.route("**/api/images", grab)
        pg.click('.view-tab[data-view="space"]')
        pg.wait_for_timeout(500)
        deadline = time.time() + 5
        while time.time() < deadline and len(held) < 1:
            pg.wait_for_timeout(50)
        assert held, "space view did not fetch images"
        n0 = len(held)
        pg.evaluate(
            """() => {
              const el = document.getElementById('W');
              el.value = '7';
              el.dispatchEvent(new Event('input', { bubbles: true }));
            }"""
        )
        deadline = time.time() + 5
        while time.time() < deadline and len(held) <= n0:
            pg.wait_for_timeout(50)
        assert len(held) > n0, len(held)
        second, first = held[-1], held[-2]
        second.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"count": 222, "lattice": [], "selected_mics": ["C"], "c": 340, "hadamard_n": 32}),
        )
        pg.wait_for_timeout(150)
        first.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"count": 111, "lattice": [], "selected_mics": ["C"], "c": 340, "hadamard_n": 32}),
        )
        pg.wait_for_timeout(250)
        text = pg.locator("#liveMetresImg").inner_text()
        assert text.startswith("222 images"), text
    finally:
        b.close()
        p.stop()


# View and drawing controls. They do not post a room parameter.
# The evaluate also treats these as UI-only, by class or role:
# diagram enlarge, space zoom/fit, the image-view mic filter,
# the room-net face picker, and a mode chip that is already pressed
# (its unpressed siblings in the same group still have to post).
_UI_ONLY_IDS = {
    "colourRefMode",
    "polarRefresh",
    "colourHoldA",
    "colourHoldB",
    "colourClearCompare",
    "micPlaneTop",
    "micPlaneSide",
    "sourceChipA",
    "sourceChipB",
    "sourceLink",
    "materialPaintAll",
    # T10 room-size chip. Click only calls setView("edit"). It does not post.
    "roomSizeChip",
    # SL1 Room result. These redraw the model. They do not post /api/live_params.
    "slMode_flat",
    # SL3. #slMode_surfaces posts /api/live_params (decay_mode) as well as /api/room_result.
    "slTogBand",
    "slTogEbu",
    # SL5. The porous menu and the tuned-panel frequency only choose the next row.
    # + Porous and + Tuned panel post /api/live_params.
    # + Room shell repeats the rows the Surfaces chip already added on enter,
    # so this click leaves the posted scene unchanged.
    "slPorousSel",
    "slPanelF0",
    "slAddShell",
    # SL6. Suggest only. The Amount slider posts Play on release.
    "slAutoBtn",
    "slAutoTmid",
    "slAutoEbu",
    # UI-TIDY-1. Save downloads JSON. The Room mic link only calls setView("mic").
    "saveSetupBtn",
    "roomMicSetupLink",
}


@pytest.mark.slow
def test_a12_visible_controls_post_or_are_ui_only(audit_server):
    p, b = _chrome()
    try:
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        pg.goto(audit_server["url"])
        pg.wait_for_timeout(800)
        pg.set_input_files("#wavInput", audit_server["wav"])
        report = pg.evaluate(
            """async (allowIds) => {
              window.confirm = () => true;
              window.LiveFDN.isRunning = () => true;
              const posts = [];
              const orig = window.fetch;
              window.fetch = function (url, opts) {
                const u = String(url);
                if (u.indexOf('/api/live_params') >= 0) {
                  posts.push(opts && opts.body ? String(opts.body) : '');
                  return Promise.resolve(new Response(JSON.stringify({ ok: true, decay_s: 1.8 }), {
                    status: 200, headers: { 'Content-Type': 'application/json' }
                  }));
                }
                return orig.apply(this, arguments);
              };
              const views = ['edit', 'source', 'mic', 'mix', 'space', 'surfaces', 'polar'];
              function visible(el) {
                if (!el || el.disabled) return false;
                if (el.type === 'hidden' || el.type === 'file') return false;
                let p = el;
                while (p) {
                  if (p.hidden) return false;
                  const s = getComputedStyle(p);
                  if (s.display === 'none' || s.visibility === 'hidden') return false;
                  p = p.parentElement;
                }
                const r = el.getBoundingClientRect();
                return r.width > 1 && r.height > 1;
              }
              function choicePressed(el) {
                if (el.getAttribute('data-room-shape')) {
                  return el.getAttribute('aria-pressed') === 'true' || el.classList.contains('active');
                }
                if (el.getAttribute('aria-pressed') !== 'true') return false;
                return !!(el.getAttribute('data-pair') || el.getAttribute('data-pan-law') ||
                  el.getAttribute('data-link') || el.getAttribute('data-radius') ||
                  el.getAttribute('data-route') || el.getAttribute('data-place') ||
                  el.getAttribute('data-third') || el.getAttribute('data-n'));
              }
              function uiOnly(el) {
                if (!el) return true;
                if (allowIds.indexOf(el.id) >= 0) return true;
                if (el.classList.contains('view-tab')) return true;
                if (el.classList.contains('diagram-expand')) return true;
                if (el.classList.contains('rn-face')) return true;
                if (el.id === 'spaceZoomOut' || el.id === 'spaceZoomIn' || el.id === 'spaceFit' || el.id === 'micAll') return true;
                if (el.closest('#polarToggles') || el.closest('#micToggles')) return true;
                if (el.getAttribute('data-space-mode')) return true;
                if (el.getAttribute('data-polar-page')) return true;
                if (el.getAttribute('data-src-freq') || el.getAttribute('data-src-plane')) return true;
                if (el.getAttribute('data-plane')) return true;
                if (choicePressed(el)) return true;
                if (el.id === 'oneSourceBtn' && (el.getAttribute('aria-pressed') === 'true' || el.classList.contains('active'))) return true;
                if (el.id === 'surfacesSoloOff' && (el.getAttribute('aria-pressed') === 'true' || el.classList.contains('is-on'))) return true;
                return false;
              }
              function keyOf(el) {
                if (el.id) return '#' + el.id;
                const bits = [];
                ['data-route', 'data-name', 'data-place', 'data-pair', 'data-pan-law', 'data-link',
                  'data-radius', 'data-third', 'data-n', 'data-solo', 'data-letter', 'data-material',
                  'data-mic', 'aria-label'].forEach((a) => {
                  const v = el.getAttribute(a);
                  if (v) bits.push(a + '=' + v);
                });
                if (bits.length) return el.tagName + ':' + bits.join(',');
                const text = (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 40);
                return el.tagName + ':' + text;
              }
              function labelOf(el) {
                if (!el) return '?';
                if (el.id) return el.id;
                const aria = el.getAttribute('aria-label');
                if (aria) return aria.trim().slice(0, 48);
                const text = (el.textContent || '').trim().slice(0, 48);
                if (text) return text;
                return keyOf(el).slice(0, 48);
              }
              function resolve(el) {
                if (el && el.isConnected && !el.disabled) return el;
                const mat = el && el.getAttribute && el.getAttribute('data-material');
                if (mat) {
                  const n = document.querySelector('[data-material="' + mat + '"]');
                  if (n && n.isConnected && !n.disabled) return n;
                }
                if (el && el.id) {
                  const n = document.getElementById(el.id);
                  if (n && n.isConnected && !n.disabled) return n;
                }
                return null;
              }
              function attrNum(el, name) {
                const raw = el.getAttribute(name);
                if (raw == null || String(raw).trim() === '') return null;
                const n = Number(raw);
                return Number.isFinite(n) ? n : null;
              }
              function nudgeNum(el) {
                const min = attrNum(el, 'min');
                const max = attrNum(el, 'max');
                let next;
                if (min != null && max != null && max > min) {
                  const hi = min + (max - min) * 0.75;
                  const lo = min + (max - min) * 0.25;
                  next = hi;
                  const cur = Number(el.value);
                  if (Number.isFinite(cur) && Math.abs(cur - hi) < 1e-6) next = lo;
                  const parent = el.closest('label') || el.parentElement;
                  if (parent) {
                    parent.querySelectorAll('input').forEach((other) => {
                      if (other !== el && Math.abs(Number(other.value) - next) < 1e-6) {
                        next = Math.abs(next - hi) < 1e-6 ? lo : hi;
                      }
                    });
                  }
                } else {
                  const stepAttr = attrNum(el, 'step');
                  const step = (stepAttr != null && stepAttr > 0) ? stepAttr : 1;
                  let v = Number(el.value);
                  if (!Number.isFinite(v)) v = (min != null ? min : 0);
                  next = v + step;
                  if (min != null && next < min) next = min + step;
                }
                el.value = String(next);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
              }
              const seen = new Set();
              const controls = [];
              views.forEach((v) => {
                const tab = document.querySelector('.view-tab[data-view="' + v + '"]');
                tab.click();
                document.querySelectorAll('input, select, textarea, button').forEach((el) => {
                  if (!visible(el)) return;
                  if (el.id === 'renderBtn' || el.id === 'liveBtn' || el.id === 'wavInput') return;
                  const key = keyOf(el);
                  if (seen.has(key)) return;
                  seen.add(key);
                  controls.push(el);
                });
              });
              async function settle(waitForPost) {
                let last = posts.length;
                const started = posts.length;
                let stable = 0;
                const deadline = Date.now() + 2500;
                const earliest = Date.now() + 200;
                while (Date.now() < deadline) {
                  await new Promise(r => setTimeout(r, 30));
                  if (posts.length === last) stable += 1;
                  else { last = posts.length; stable = 0; }
                  if (Date.now() >= earliest && stable >= 3 && (!waitForPost || posts.length > started)) break;
                }
                return posts.length ? posts[posts.length - 1] : '';
              }
              let prev = await settle();
              const quiet = [];
              let materialPosted = false;
              for (let i = 0; i < controls.length; i++) {
                let el = resolve(controls[i]);
                if (!el) continue;
                if (el.id === 'mcx') {
                  const parity = document.getElementById('reaktor_parity');
                  if (parity && parity.checked) {
                    parity.click();
                    prev = await settle();
                  }
                }
                const tag = el.tagName;
                const type = (el.type || '').toLowerCase();
                if (el.classList.contains('desk-read')) {
                  el.click();
                  const input = el.querySelector('input');
                  if (input) {
                    const cur = Number(input.value);
                    input.value = String(Number.isFinite(cur) ? (cur + 3) : -6);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
                    input.dispatchEvent(new Event('blur'));
                  }
                } else if (tag === 'SELECT') {
                  const opts = Array.from(el.options).map(o => o.value);
                  const next = opts.find(v => v !== el.value);
                  if (next == null) continue;
                  el.value = next;
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                } else if (type === 'checkbox' || type === 'radio') {
                  el.click();
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                } else if (type === 'range' || type === 'number') {
                  nudgeNum(el);
                } else if (tag === 'BUTTON') {
                  if (el.id === 'slAddPorous' && window.RRColourSurfaces && window.RRColourSurfaces.select) {
                    window.RRColourSurfaces.select('B');
                    const wallBtn = document.getElementById('slAddPorous');
                    if (wallBtn) el = wallBtn;
                  }
                  el.click();
                } else {
                  el.dispatchEvent(new Event('input', { bubbles: true }));
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                }
                const body = await settle(el.id === 'slAddPanel');
                const mat = el.getAttribute && el.getAttribute('data-material');
                if (mat && body !== prev) materialPosted = true;
                if (body === prev && !uiOnly(el)) quiet.push(labelOf(el));
                if (body) prev = body;
              }
              const soloOn = document.querySelector('#surfaceCards [data-solo]');
              const soloOff = document.getElementById('surfacesSoloOff');
              if (soloOn && soloOff) {
                soloOn.click();
                let armed = await settle();
                if (soloOff.getAttribute('aria-pressed') === 'true') {
                  soloOn.click();
                  armed = await settle();
                }
                soloOff.click();
                const after = await settle();
                if (after === armed) quiet.push('surfacesSoloOff');
              }
              return { n: controls.length, quiet: quiet, posts: posts.length, materialPosted: materialPosted };
            }""",
            sorted(_UI_ONLY_IDS),
        )
        (_shots() / "a12_quiet.txt").write_text(
            f"n={report['n']} posts={report.get('posts')}\n" + "\n".join(report["quiet"]),
            encoding="utf-8",
        )
        assert report["n"] > 20, report
        assert report.get("materialPosted") is True, report
        assert report["quiet"] == [], report["quiet"]
    finally:
        b.close()
        p.stop()


def test_b1_chrome_plays_24bit_wav(audit_server, tmp_path):
    import numpy as np
    sys.path[:0] = [str(SW)]
    from render_pipeline import write_wav_stereo

    sr = 48000
    t = np.arange(sr // 2, dtype=np.float64) / sr
    tone = 0.2 * np.sin(2.0 * np.pi * 440.0 * t)
    path = tmp_path / "b1_play.wav"
    write_wav_stereo(str(path), tone, tone * 0.5, sr)
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    p, b = _chrome()
    try:
        pg = b.new_page()
        pg.goto(audit_server["url"])
        report = pg.evaluate(
            """async (b64) => {
              const bin = atob(b64);
              const bytes = new Uint8Array(bin.length);
              for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
              const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }));
              const audio = document.createElement('audio');
              audio.preload = 'auto';
              audio.src = url;
              await new Promise((resolve, reject) => {
                audio.onloadedmetadata = () => resolve();
                audio.onerror = () => reject(new Error('media ' + (audio.error && audio.error.code)));
              });
              await audio.play();
              const t0 = performance.now();
              while (audio.currentTime <= 0 && performance.now() - t0 < 2000) {
                await new Promise(r => setTimeout(r, 50));
              }
              return {
                duration: audio.duration,
                error: audio.error ? audio.error.code : 0,
                paused: audio.paused,
                currentTime: audio.currentTime,
                readyState: audio.readyState
              };
            }""",
            b64,
        )
        assert report["error"] == 0, report
        assert report["duration"] > 0, report
        assert report["paused"] is False, report
        assert report["currentTime"] > 0, report
    finally:
        b.close()
        p.stop()


@pytest.mark.slow
def test_b3_limiter_message_in_play_and_render(audit_server, tmp_path):
    """Hot faders: the Play badge and the Render status both name the limiter."""
    import random

    wav = tmp_path / "hot_burst.wav"
    rnd = random.Random(1)
    n = int(0.45 * 48000)
    samples = [int(max(-32767, min(32767, rnd.uniform(-0.85, 0.85) * 32767))) for _ in range(n)]
    samples.extend([0] * 4800)
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(struct.pack("<" + "h" * len(samples), *samples))
    shots = _shots()
    p, b = _chrome()
    try:
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(audit_server["url"])
        pg.wait_for_timeout(500)
        pg.set_input_files("#wavInput", str(wav))
        pg.click('.view-tab[data-view="mic"]')
        pg.select_option("#colour_mode", "BYPASS")
        for fid in ("fader_direct", "fader_fdn", "fader_early"):
            pg.locator("#" + fid).evaluate(
                "el => { el.value = '1'; el.dispatchEvent(new Event('input', { bubbles: true })); }"
            )
        pg.click("#liveBtn")
        pg.wait_for_function(
            """() => {
              const e = document.getElementById('limiterLed');
              return !!(e && !e.hidden && e.textContent.indexOf('Limiter: peak reduced by') === 0);
            }""",
            timeout=20000,
        )
        pg.locator(".top-actions").screenshot(path=str(shots / "b3_limiter_play.png"))
        pg.click("#liveBtn")
        pg.click("#renderBtn")
        pg.wait_for_function(
            """() => {
              const full = (document.getElementById('status').textContent || '');
              const head = (document.getElementById('headerStatus').textContent || '');
              return full.indexOf('Limiter: peak reduced by') === 0
                && head.indexOf('Limiter: peak reduced by') === 0;
            }""",
            timeout=180000,
        )
        pg.click('.view-tab[data-view="edit"]')
        pg.locator("#status").screenshot(path=str(shots / "b3_limiter_render.png"))
        text = pg.locator("#status").inner_text()
        head = pg.locator("#headerStatus").inner_text()
        assert text.startswith("Limiter: peak reduced by")
        assert head.startswith("Limiter: peak reduced by")
    finally:
        b.close()
        p.stop()


@pytest.mark.slow
def test_b5_mono_strips_disabled_and_restored(audit_server):
    """Mono centre greys L and R. Other setups leave those strips enabled."""
    p, b = _chrome()
    try:
        pg = b.new_page(viewport={"width": 1400, "height": 900})
        posts = []

        def on_route(route):
            posts.append(json.loads(route.request.post_data or "{}"))
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"ok":false,"error":"stub"}',
            )

        pg.route("**/api/live_params", on_route)
        pg.goto(audit_server["url"])
        pg.wait_for_timeout(600)
        pg.evaluate("() => { window.LiveFDN.isRunning = () => true; }")
        pg.click('.view-tab[data-view="mic"]')
        pg.select_option("#mic_setup", "mono_c")
        pg.wait_for_timeout(400)
        pg.click('.view-tab[data-view="mix"]')
        pg.wait_for_timeout(300)

        def strip(cap):
            return pg.evaluate(
                """(cap) => {
                  const row = document.querySelector('.desk-strip[data-cap="' + cap + '"]');
                  const controls = Array.from(row.querySelectorAll('input, button'));
                  const fader = document.getElementById('fader_' + cap);
                  const mute = document.getElementById('mute_' + cap);
                  return {
                    off: row.classList.contains('is-mono-off'),
                    title: row.title,
                    disabled: controls.every(el => el.disabled),
                    enabled: controls.some(el => !el.disabled),
                    fader: fader.value,
                    faderDisabled: fader.disabled,
                    tip: fader.title,
                    mute: mute.getAttribute('aria-pressed')
                  };
                }""",
                cap,
            )

        left = strip("l")
        right = strip("r")
        centre = strip("c")
        assert left["off"] and right["off"], (left, right)
        assert left["disabled"] and right["disabled"], (left, right)
        assert left["title"] == "Mono centre uses only C"
        assert left["tip"] == "Mono centre uses only C"
        assert right["title"] == "Mono centre uses only C"
        assert centre["off"] is False
        assert centre["faderDisabled"] is False
        assert centre["enabled"] is True
        centre_l = pg.locator('.desk-strip[data-cap="c"] .lr-btn[data-side="l"]')
        centre_r = pg.locator('.desk-strip[data-cap="c"] .lr-btn[data-side="r"]')
        assert centre_l.get_attribute("data-v") == "1"
        assert centre_r.get_attribute("data-v") == "1"
        pg.locator("#deskMics").screenshot(path=str(_shots() / "b5_mono_strips.png"))
        posted = [row for row in posts if row.get("mic_setup") == "mono_c"]
        assert posted, "mono centre did not post"
        last = posted[-1]
        assert last.get("mic_gain_l") == 0
        assert last.get("mic_gain_r") == 0
        assert last.get("mic_route_c") == "centre"
        assert abs(float(last.get("mic_gain_c")) - 1.0) < 1e-9
        # Disabled controls ignore a forced mute click. The preset mute stays on.
        n_posts = len(posts)
        pg.locator("#mute_l").evaluate(
            "el => el.dispatchEvent(new MouseEvent('click', { bubbles: true }))"
        )
        pg.locator("#fader_l").evaluate(
            "el => { el.value = '1'; el.dispatchEvent(new Event('input', { bubbles: true })); }"
        )
        pg.wait_for_timeout(200)
        after = strip("l")
        assert after["mute"] == "true", after
        assert after["faderDisabled"] is True
        assert len(posts) == n_posts, "a locked strip posted a desk change"

        pg.click('.view-tab[data-view="mic"]')
        pg.select_option("#mic_setup", "ortf")
        pg.wait_for_timeout(300)
        pg.click('.view-tab[data-view="mix"]')
        pg.wait_for_timeout(200)
        back_l = strip("l")
        back_r = strip("r")
        assert back_l["off"] is False and back_r["off"] is False
        assert back_l["faderDisabled"] is False and back_r["faderDisabled"] is False
        assert back_l["disabled"] is False and back_r["disabled"] is False
        assert back_l["mute"] == "false" and back_r["mute"] == "false"
        assert back_l["fader"] == "0.5" and back_r["fader"] == "0.5"
        xy = [row for row in posts if row.get("mic_setup") == "ortf"]
        assert xy, "leaving mono did not post ORTF"
        assert xy[-1].get("mic_gain_l") == 1
        assert xy[-1].get("mic_gain_r") == 1
    finally:
        b.close()
        p.stop()


@pytest.mark.slow
def test_b6_side_view_readout_and_drag(audit_server):
    """Side view names each capsule height, and a drag is posted to Play."""
    pose = (ROOT / "software" / "static" / "js" / "room_view_pose.js").read_text(encoding="utf-8")
    assert "height  L " in pose
    p, b = _chrome()
    try:
        pg = b.new_page(viewport={"width": 1400, "height": 900})
        posts = []

        def on_route(route):
            posts.append(json.loads(route.request.post_data or "{}"))
            route.fulfill(status=200, content_type="application/json", body='{"ok":true}')

        pg.route("**/api/live_params", on_route)
        pg.goto(audit_server["url"])
        pg.wait_for_timeout(600)
        pg.evaluate("() => { window.LiveFDN.isRunning = () => true; }")
        pg.click('.view-tab[data-view="mic"]')
        pg.click("#micPlaneSide")
        pg.locator("#align_horizontal").evaluate(
            "el => { if (el.checked) { el.checked = false; el.dispatchEvent(new Event('change', { bubbles: true })); } }"
        )
        # 17 cm ORTF stacks L on C in the side view. A wider pair separates once the view turns.
        pg.locator("#space").evaluate(
            "el => { el.value = '0.80'; el.dispatchEvent(new Event('input', { bubbles: true })); }"
        )
        canvas = pg.locator("#micFloorCanvas")
        canvas.scroll_into_view_if_needed()
        pg.wait_for_timeout(250)
        # Pointer events are built in the page so clientX matches the canvas pixels of the L handle.
        # A horizontal drag on empty canvas turns the view. The L blob is then dragged upward.
        aimed = pg.evaluate(
            """() => {
              const c = document.getElementById('micFloorCanvas');
              const ctx = c.getContext('2d');
              const rgb = { L: [167, 139, 250], C: [45, 212, 191], R: [52, 211, 153], S: [251, 191, 36] };
              function scan() {
                const img = ctx.getImageData(0, 0, c.width, c.height);
                const d = img.data;
                const out = {};
                Object.keys(rgb).forEach((key) => {
                  const t = rgb[key];
                  const bins = new Map();
                  for (let y = 0; y < c.height; y += 2) {
                    for (let x = 0; x < c.width; x += 2) {
                      const i = (y * c.width + x) * 4;
                      if (d[i + 3] < 180) continue;
                      if (Math.abs(d[i] - t[0]) > 26 || Math.abs(d[i + 1] - t[1]) > 22 || Math.abs(d[i + 2] - t[2]) > 22) continue;
                      const k = ((x / 18) | 0) + ',' + ((y / 18) | 0);
                      const b = bins.get(k) || { n: 0, x: 0, y: 0 };
                      b.n += 1; b.x += x; b.y += y;
                      bins.set(k, b);
                    }
                  }
                  let best = null;
                  bins.forEach((b) => { if (!best || b.n > best.n) best = b; });
                  out[key] = best && best.n >= 6 ? { x: best.x / best.n, y: best.y / best.n, n: best.n } : null;
                });
                return out;
              }
              function fire(type, px, py) {
                const r = c.getBoundingClientRect();
                c.dispatchEvent(new PointerEvent(type, {
                  bubbles: true, cancelable: true, view: window,
                  clientX: r.left + (px + 0.5) * r.width / c.width,
                  clientY: r.top + (py + 0.5) * r.height / c.height,
                  pointerId: 1, pointerType: 'mouse', button: 0,
                  buttons: type === 'pointerup' ? 0 : 1, isPrimary: true
                }));
              }
              function drag(x0, y0, x1, y1) {
                fire('pointerdown', x0, y0);
                for (let i = 1; i <= 8; i++) {
                  fire('pointermove', x0 + (x1 - x0) * i / 8, y0 + (y1 - y0) * i / 8);
                }
                fire('pointerup', x1, y1);
              }
              function gap(a, b) {
                if (!a || !b) return 0;
                return Math.hypot(a.x - b.x, a.y - b.y);
              }
              function emptyPoint(handles) {
                const pts = Object.keys(handles).map((k) => handles[k]).filter(Boolean);
                const spots = [[24, 24], [24, c.height * 0.72], [c.width - 28, 24], [40, c.height - 24]];
                for (let s = 0; s < spots.length; s++) {
                  let md = 1e9;
                  for (let i = 0; i < pts.length; i++) {
                    md = Math.min(md, Math.hypot(pts[i].x - spots[s][0], pts[i].y - spots[s][1]));
                  }
                  if (md > 70) return spots[s];
                }
                return [24, 24];
              }
              const before = scan();
              let spot = emptyPoint(before);
              drag(spot[0], spot[1], spot[0] + 230, spot[1]);
              let handles = scan();
              if (!handles.L || gap(handles.L, handles.C) < 28) {
                spot = emptyPoint(handles);
                drag(spot[0], spot[1], spot[0] + 180, spot[1]);
                handles = scan();
              }
              const L = handles.L;
              if (!L) return { ok: false, before: before, handles: handles };
              const y1 = Math.max(12, L.y - 80);
              drag(L.x, L.y, L.x, y1);
              return { ok: true, before: before, handles: handles, toY: y1 };
            }"""
        )
        pg.wait_for_timeout(500)
        canvas.screenshot(path=str(_shots() / "b6_side_readout.png"))
        heard = [
            row for row in posts
            if any(row.get(k) not in (None, "") for k in ("my_l", "my_r", "my_c"))
        ]
        brief = [
            {k: row.get(k) for k in ("my", "my_l", "my_r", "my_c", "sy", "align_horizontal", "space")}
            for row in posts
        ]
        assert heard, f"a side drag did not post a capsule height ({len(posts)} posts) {brief} aim={aimed}"
        last = heard[-1]
        caps = [last.get("my_l"), last.get("my_c"), last.get("my_r"), last.get("my")]
        assert any(
            v is not None and abs(float(v) - float(last.get("my"))) > 0.02
            for v in (last.get("my_l"), last.get("my_r"))
        ), caps
    finally:
        b.close()
        p.stop()
