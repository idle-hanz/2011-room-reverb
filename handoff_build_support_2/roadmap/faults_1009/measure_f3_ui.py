"""Read-only page check for F3 and F2. Free port. Render posts are stubbed."""
from __future__ import annotations

import json
import re
import socket
import struct
import subprocess
import time
import wave
from pathlib import Path

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
OUT = ROOT / "handoff_build_support_2" / "roadmap" / "faults_1009"
PY = SW / ".venv" / "Scripts" / "python.exe"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
if not CHROME.exists():
    alt = Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
    CHROME = alt if alt.exists() else Path()


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def tiny_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(struct.pack("<" + "h" * 480, *([0] * 480)))


def grab_params(raw: bytes) -> dict:
    text = raw.decode("utf-8", "replace")
    m = re.search(r'name="params_json"\r?\n\r?\n(\{.*\})\r?\n--', text, re.S)
    if not m:
        raise RuntimeError("params_json missing")
    return json.loads(m.group(1))


KEYS = (
    "place_l", "place_c", "place_r", "third_mic",
    "mic_gain_l", "mic_gain_c", "mic_gain_r",
    "mic_x_l", "mic_y_l", "mic_z_l",
    "mic_x_c", "mic_y_c", "mic_z_c",
    "mic_x_r", "mic_y_r", "mic_z_r",
    "yaw_l_deg", "yaw_c_deg", "yaw_r_deg",
    "mute_l", "mute_c", "mute_r",
    "mic_route_l", "mic_route_c", "mic_route_r",
    "fdn_wet", "direct_wet", "early_wet",
)


def slim(body: dict) -> dict:
    return {k: body.get(k) for k in KEYS}


def main() -> None:
    if not CHROME.exists():
        raise SystemExit("Chrome missing")
    port = free_port()
    wav = OUT / "_tiny.wav"
    tiny_wav(wav)
    proc = subprocess.Popen(
        [str(PY), "-c",
         "import uvicorn; from app_server import app; "
         f"uvicorn.run(app, host='127.0.0.1', port={port}, log_level='warning')"],
        cwd=str(SW),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}/"
    deadline = time.time() + 40
    up = False
    while time.time() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
            raise SystemExit("server exited: " + err[-800:])
        try:
            with socket.create_connection(("127.0.0.1", port), 0.3):
                up = True
                break
        except OSError:
            time.sleep(0.15)
    if not up:
        proc.kill()
        raise SystemExit("server did not listen")

    from playwright.sync_api import sync_playwright

    caps: list[dict] = []

    def on_render(route, req):
        caps.append(grab_params(req.post_data_buffer or b""))
        route.fulfill(status=200, content_type="application/json", body='{"ok":true,"status":"stub"}')

    report: dict = {"port": port, "cases": {}}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(
                executable_path=str(CHROME),
                headless=True,
                args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
            )
            pg = b.new_page(viewport={"width": 1600, "height": 1000})
            pg.route("**/api/render", on_render)
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))

            def boot():
                caps.clear()
                with pg.expect_response(lambda r: r.url.endswith("/api/defaults") and r.status == 200, timeout=20000):
                    pg.goto(url)
                pg.wait_for_timeout(700)
                pg.set_input_files("#wavInput", str(wav))
                pg.wait_for_timeout(300)

            def post_render(tag: str) -> dict:
                n = len(caps)
                pg.click("#renderBtn")
                for _ in range(80):
                    if len(caps) > n:
                        break
                    pg.wait_for_timeout(50)
                if len(caps) == n:
                    raise RuntimeError("no render post for " + tag)
                body = caps[-1]
                ui = pg.evaluate(
                    """() => {
                      function pressed(sel) {
                        const el = document.querySelector(sel);
                        return el ? el.getAttribute('aria-pressed') : null;
                      }
                      function val(id) {
                        const el = document.getElementById(id);
                        return el ? el.value : null;
                      }
                      const matrix = document.getElementById('deskMatrix');
                      return {
                        mix_room_c: pressed('[data-place="c"][data-name="room"]'),
                        mix_stand_c: pressed('[data-place="c"][data-name="array"]'),
                        mix_room_l: pressed('[data-place="l"][data-name="room"]'),
                        third_room: pressed('[data-third="room"]'),
                        third_off: pressed('[data-third="off"]'),
                        third_centre: pressed('[data-third="centre"]'),
                        room_c_x: val('room_c_x'),
                        room_c_y: val('room_c_y'),
                        room_c_z: val('room_c_z'),
                        room_c_yaw: val('room_c_yaw'),
                        room_l_x: val('room_l_x'),
                        room_l_z: val('room_l_z'),
                        matrix: matrix ? matrix.textContent : null,
                        metres: (document.getElementById('liveMetres') || {}).textContent || null,
                        mic_metres: (document.getElementById('liveMetresMic') || {}).textContent || null
                      };
                    }"""
                )
                report["cases"][tag] = {"ui": ui, "posted": slim(body)}
                print(tag, json.dumps(slim(body)), flush=True)
                print("  ui", json.dumps(ui), flush=True)
                return body

            boot()
            pg.click('[data-view="mix"]')
            pg.wait_for_timeout(200)
            post_render("boot")

            pg.click('[data-place="c"][data-name="room"]')
            pg.wait_for_timeout(250)
            post_render("mix_room_c")

            boot()
            pg.click('[data-view="mic"]')
            pg.wait_for_timeout(300)
            pg.click('[data-third="room"]')
            pg.wait_for_timeout(300)
            post_render("mic_room_c")

            # F2: move the room spot, then see what Space and the Mic top-view text use.
            pg.evaluate(
                """() => {
                  function setv(id, v) {
                    const el = document.getElementById(id);
                    el.value = String(v);
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                  }
                  setv('room_c_x', 5.5);
                  setv('room_c_z', 0.4);
                  setv('room_c_y', 2.5);
                  setv('room_c_yaw', 10);
                }"""
            )
            pg.wait_for_timeout(200)
            images = {}
            with pg.expect_response(lambda r: "/api/images" in r.url and r.status == 200, timeout=20000) as ir:
                pg.click('[data-view="space"]')
            img = ir.value.json()
            req = ir.value.request.post_data or ""
            images["response_mics"] = img.get("mics")
            images["response_geometry_mic_centre"] = (img.get("geometry") or {}).get("mic_centre")
            images["request_has_mic_x_c"] = "mic_x_c" in req
            images["request_has_room_c_x"] = "room_c_x" in req
            report["f2_images"] = images
            print("F2 images mics", images["response_mics"], "req mic_x", images["request_has_mic_x_c"], flush=True)

            polar_req = {}
            with pg.expect_response(lambda r: "/api/polar" in r.url and r.status == 200, timeout=20000) as pr:
                pg.click('[data-view="mic"]')
            preq = pr.value.request.post_data or ""
            polar_req["has_mic_x_c"] = "mic_x_c" in preq
            polar_req["has_room_c_x"] = "room_c_x" in preq
            try:
                sent = json.loads(preq)
                polar_req["room_c_x"] = sent.get("room_c_x")
                polar_req["third_mic"] = sent.get("third_mic")
                polar_req["place_c"] = sent.get("place_c")
                polar_req["mcx"] = sent.get("mcx")
                polar_req["mcz"] = sent.get("mcz")
            except Exception as exc:
                polar_req["parse_error"] = str(exc)
            report["f2_polar_request"] = polar_req
            top = pg.evaluate(
                """() => ({
                  mic: (document.getElementById('liveMetresMic') || {}).textContent || null,
                  room_c_x: (document.getElementById('room_c_x') || {}).value || null,
                  room_c_y: (document.getElementById('room_c_y') || {}).value || null,
                  room_c_z: (document.getElementById('room_c_z') || {}).value || null,
                  hint: (document.getElementById('micPlaneHint') || {}).textContent || null
                })"""
            )
            report["f2_mic_dom"] = top
            print("F2 polar", json.dumps(polar_req), flush=True)
            print("F2 dom", json.dumps(top), flush=True)

            boot()
            pg.click('[data-view="mix"]')
            pg.wait_for_timeout(200)
            pg.click('[data-place="l"][data-name="room"]')
            pg.wait_for_timeout(250)
            post_render("mix_room_l")

            report["page_errors"] = errors
            b.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    OUT.joinpath("ui_capture.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("wrote ui_capture.json", flush=True)


if __name__ == "__main__":
    main()
