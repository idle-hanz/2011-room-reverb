"""Place chips keep the source, stand and mics centred on the room.

Studio to Hall used to leave the stand at its studio x, on the left wall of the
hall. The chip stores the positions and puts them back exactly on the way home.
Slow. From software\\:

software\\.venv\\Scripts\\python.exe -m pytest tests\\test_place_centre.py -q -m slow
"""
from __future__ import annotations

import socket
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
PY = SW / ".venv" / "Scripts" / "python.exe"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
if not CHROME.exists():
    alt = Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
    CHROME = alt if alt.exists() else Path()

_SET = """
(spec) => {
  function setRange(id, v) {
    var el = document.getElementById(id);
    if (!el) throw new Error("missing " + id);
    el.value = String(v);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }
  setRange("mcx", spec.mcx);
  setRange("mcz", spec.mcz);
  setRange("my", spec.my);
  setRange("sy", spec.sy);
  state.sx = spec.sx;
  state.sz = spec.sz;
  if (window.RoomMath && RoomMath.clampRoom) Object.assign(state, RoomMath.clampRoom(state));
  syncUI();
}
"""

_ORIG = """
() => {
  window.__placeOrig = {
    W: state.W, H: state.H, L: state.L,
    sx: state.sx, sz: state.sz, sy: state.sy,
    mcx: state.mcx, mcz: state.mcz, my: state.my
  };
  return window.__placeOrig;
}
"""

_HALL = """
() => {
  var o = window.__placeOrig;
  var M = 0.10;
  function shift(v, oldSize, newSize) {
    var next = v - oldSize * 0.5 + newSize * 0.5;
    if (!(newSize < oldSize)) return next;
    var lo = M;
    var hi = newSize - lo;
    if (next < lo) return lo;
    if (next > hi) return hi;
    return next;
  }
  var axes = { sx: "W", sz: "L", sy: "H", mcx: "W", mcz: "L", my: "H" };
  var bad = [];
  Object.keys(axes).forEach(function (k) {
    var want = shift(o[k], o[axes[k]], state[axes[k]]);
    if (state[k] !== want) bad.push(k + " " + state[k] + " != " + want);
    if (!(state[k] >= M && state[k] <= state[axes[k]] - M)) bad.push(k + " outside");
  });
  var geo = RoomMath.compute(state);
  [geo.source, geo.mic_centre, geo.mic_left, geo.mic_right].forEach(function (p, i) {
    if (!(p.x > 0 && p.x < state.W && p.z > 0 && p.z < state.L && p.y > 0 && p.y < state.H)) {
      bad.push("point " + i + " outside");
    }
  });
  if (!(state.W > o.W && state.L > o.L && state.H > o.H)) bad.push("room did not grow");
  return { bad: bad, W: state.W, sx: state.sx, mcx: state.mcx, mcz: state.mcz };
}
"""

_BACK = """
() => {
  var o = window.__placeOrig;
  var keys = ["sx", "sz", "sy", "mcx", "mcz", "my"];
  var bad = [];
  keys.forEach(function (k) {
    if (state[k] !== o[k]) bad.push(k + " " + state[k] + " != " + o[k]);
  });
  if (state.W !== o.W || state.H !== o.H || state.L !== o.L) bad.push("size");
  return { bad: bad, sx: state.sx, mcx: state.mcx, mcz: state.mcz };
}
"""


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def place_server():
    if not CHROME.exists():
        pytest.fail("Chrome is not installed; the place-centre gate cannot run")
    port = _free_port()
    boot = (
        "import uvicorn\n"
        "import app_server\n"
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
    yield url
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.mark.slow
def test_studio_hall_keeps_centre_and_restores(place_server):
    """Non-default Studio positions stay centre-relative in Hall and come back exactly."""
    from playwright.sync_api import sync_playwright

    spec = {"sx": 1.25, "sz": 5.40, "sy": 0.90, "mcx": 4.05, "mcz": 2.35, "my": 1.70}
    with sync_playwright() as p:
        b = p.chromium.launch(
            executable_path=str(CHROME),
            headless=True,
            args=[
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
            ],
        )
        pg = b.new_page(viewport={"width": 1400, "height": 900})
        pg.on("dialog", lambda d: d.accept())
        with pg.expect_response(lambda r: r.url.endswith("/api/settings?part=defaults") and r.status == 200, timeout=20000):
            pg.goto(place_server)
        pg.click("#placeRow [data-place=studio]")
        pg.wait_for_timeout(200)
        pg.evaluate(_SET, spec)
        pg.wait_for_timeout(50)
        orig = pg.evaluate(_ORIG)
        assert orig["sx"] == pytest.approx(spec["sx"])
        assert orig["mcx"] == pytest.approx(spec["mcx"])
        assert orig["mcz"] == pytest.approx(spec["mcz"])
        assert orig["mcx"] != pytest.approx(2.8)
        pg.click("#placeRow [data-place=hall]")
        pg.wait_for_timeout(200)
        hall = pg.evaluate(_HALL)
        assert not hall["bad"], hall
        pg.click("#placeRow [data-place=studio]")
        pg.wait_for_timeout(200)
        back = pg.evaluate(_BACK)
        assert not back["bad"], back
        b.close()
