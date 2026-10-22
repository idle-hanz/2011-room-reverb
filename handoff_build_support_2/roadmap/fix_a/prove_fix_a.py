"""FIX-A page proof. Free port. Render posts are stubbed. 7860 is not touched.

Shows: Mix Room on C posts mic_gain_c 1 and the matrix reads C −6.0 / −6.0;
a repeat Room click still Returns to the saved third; Mix Room on L leaves C off;
Top, Side, and the 3D capsule follow a Room C; a drag writes room_c_* only;
an on-stand L drag still changes space; Binaural Top still skips C.
"""
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
OUT = ROOT / "handoff_build_support_2" / "roadmap" / "fix_a"
PY = SW / ".venv" / "Scripts" / "python.exe"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
if not CHROME.exists():
    alt = Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
    CHROME = alt if alt.exists() else Path()

MINUS = "\u2212"
MATRIX_C = "C " + MINUS + "6.0 / " + MINUS + "6.0"
STAND_HINT = (
    "The stand, from above. Scroll to zoom. "
    "Drag a capsule in or out, and the amber front to aim."
)
ROOM_HINT = "Room mics sit at their spots."


def port_open(port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.25)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def free_port() -> int:
    for _ in range(8):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        if port != 7860:
            return port
    raise SystemExit("could not find a free port other than 7860")


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
        raise AssertionError("params_json missing from render post")
    return json.loads(m.group(1))


def near(a, b, tol=1e-3) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


class Proof:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.notes: list[str] = []

    def check(self, ok: bool, msg: str) -> None:
        if ok:
            self.notes.append("ok " + msg)
        else:
            self.errors.append(msg)

    def eq(self, got, want, msg: str) -> None:
        self.check(got == want, f"{msg}: got {got!r} want {want!r}")


def main() -> None:
    if not CHROME.exists():
        raise SystemExit("Chrome missing")
    if not PY.exists():
        raise SystemExit("venv python missing")
    OUT.mkdir(parents=True, exist_ok=True)
    idle_before = port_open(7860)
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
            raise SystemExit("server exited: " + err[-600:])
        if port_open(port):
            up = True
            break
        time.sleep(0.15)
    if not up:
        proc.kill()
        raise SystemExit("server did not listen")

    proof = Proof()
    page_errors: list[str] = []
    console_errors: list[str] = []
    posts: list[dict] = []

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=str(CHROME),
                headless=True,
                args=[
                    "--use-gl=angle",
                    "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader",
                ],
            )
            pg = browser.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda exc: page_errors.append(str(exc)))
            pg.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            def on_route(route):
                posts.append(grab_params(route.request.post_data_buffer or b""))
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body='{"ok":true,"status":"stub"}',
                )

            pg.route("**/api/render", on_route)

            def boot() -> None:
                with pg.expect_response(lambda r: r.url.endswith("/api/defaults") and r.status == 200, timeout=20000):
                    pg.goto(url)
                pg.wait_for_function(
                    """() => {
                      const off = document.querySelector('[data-third="off"]');
                      const space = document.getElementById('space_out');
                      return !!(off && off.getAttribute('aria-pressed') === 'true'
                        && space && space.textContent.indexOf('0.17') >= 0);
                    }""",
                    timeout=15000,
                )
                pg.set_input_files("#wavInput", str(wav))
                pg.wait_for_timeout(250)

            def tab(name: str) -> None:
                pg.click(f'.view-tab[data-view="{name}"]')
                pg.wait_for_timeout(200)

            def render_post() -> dict:
                n0 = len(posts)
                pg.click("#renderBtn")
                deadline_r = time.time() + 15
                while time.time() < deadline_r:
                    if len(posts) > n0:
                        return posts[-1]
                    pg.wait_for_timeout(100)
                status = pg.locator("#status").inner_text()
                raise AssertionError("no render post; status=" + status)

            def pressed(sel: str) -> str | None:
                return pg.evaluate(
                    """sel => {
                      const el = document.querySelector(sel);
                      return el ? el.getAttribute('aria-pressed') : null;
                    }""",
                    sel,
                )

            def set_room(cap: str, x: float, y: float, z: float) -> None:
                pg.evaluate(
                    """([cap, x, y, z]) => {
                      function set(id, v) {
                        const el = document.getElementById(id);
                        el.value = String(v);
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                      }
                      set('room_' + cap + '_x', x);
                      set('room_' + cap + '_y', y);
                      set('room_' + cap + '_z', z);
                    }""",
                    [cap, x, y, z],
                )
                pg.wait_for_timeout(150)

            def probe():
                return pg.evaluate("() => window.micDesk.probe()")

            def worlds(canvas_id: str):
                return pg.evaluate(
                    """id => {
                      const c = document.getElementById(id);
                      if (!c || !c._room3d || !c._room3d.capsuleWorld) return null;
                      c._room3d.redraw();
                      return c._room3d.capsuleWorld();
                    }""",
                    canvas_id,
                )

            def show_floor() -> None:
                pg.locator("#micFloorCanvas").scroll_into_view_if_needed()
                pg.wait_for_function(
                    """() => {
                      const c = document.getElementById('micFloorCanvas');
                      const r = c.getBoundingClientRect();
                      return c.width > 10 && r.width > 10 && r.height > 10;
                    }""",
                    timeout=10000,
                )

            def drag(x: float, y: float, dx: float, dy: float) -> None:
                pg.mouse.move(x, y)
                pg.mouse.down()
                pg.mouse.move(x + dx, y + dy, steps=12)
                pg.mouse.up()
                pg.wait_for_timeout(200)

            def scroll_width() -> dict:
                return pg.evaluate(
                    """() => ({
                      scrollWidth: document.documentElement.scrollWidth,
                      clientWidth: document.documentElement.clientWidth
                    })"""
                )

            # --- F3: Mix Room on C ---
            boot()
            tab("mix")
            pg.click('.place-row [data-place="c"][data-name="room"]')
            pg.wait_for_timeout(200)
            body = render_post()
            matrix = pg.locator("#deskMatrix").inner_text()
            proof.check(near(body.get("mic_gain_c"), 1, 1e-6), "F3 mic_gain_c is 1")
            proof.check(MATRIX_C in matrix, "F3 matrix has " + MATRIX_C + " ; got " + matrix)
            proof.eq(body.get("third_mic"), "room", "F3 posted third_mic")
            proof.eq(body.get("place_c"), "room", "F3 posted place_c")
            proof.eq(pressed('[data-third="room"]'), "true", "F3 third chip Room")
            proof.notes.append("F3 matrix " + matrix)
            pg.screenshot(path=str(OUT / "fix_a_mix_matrix.png"))

            # Repeat Room, then Return, restores off.
            pg.click('.place-row [data-place="c"][data-name="room"]')
            pg.wait_for_timeout(150)
            pg.click('.place-row [data-place="c"][data-name="array"]')
            pg.wait_for_timeout(200)
            proof.eq(pressed('[data-third="off"]'), "true", "repeat Room then Return restores off")
            proof.eq(pressed('[data-place="c"][data-name="room"]'), "false", "Return leaves C on the stand")

            # Centre was saved, so Return restores centre.
            boot()
            tab("mic")
            pg.click('[data-third="centre"]')
            pg.wait_for_timeout(200)
            proof.eq(pressed('[data-third="centre"]'), "true", "third chip Centre before Mix Room")
            tab("mix")
            pg.click('.place-row [data-place="c"][data-name="room"]')
            pg.wait_for_timeout(150)
            pg.click('.place-row [data-place="c"][data-name="room"]')
            pg.wait_for_timeout(150)
            pg.click('.place-row [data-place="c"][data-name="array"]')
            pg.wait_for_timeout(200)
            proof.eq(pressed('[data-third="centre"]'), "true", "Return restores centre")

            # Mix Room on L leaves C off.
            boot()
            n_before_l = len(posts)
            tab("mix")
            pg.click('.place-row [data-place="l"][data-name="room"]')
            pg.wait_for_timeout(200)
            left = render_post()
            proof.eq(left.get("third_mic"), "off", "Mix Room on L leaves third_mic off")
            proof.check(near(left.get("mic_gain_c"), 0, 1e-9), "Mix Room on L leaves mic_gain_c 0")
            proof.check(near(left.get("mic_gain_l"), 1, 1e-6), "Mix Room on L posts mic_gain_l 1")
            proof.eq(left.get("place_l"), "room", "Mix Room on L posts place_l room")
            proof.check("mic_x_c" not in left, "Mix Room on L does not post mic_x_c")
            proof.check("mic_x_l" in left, "Mix Room on L posts mic_x_l")
            boot_keys_note = n_before_l

            # --- F2 display ---
            boot()
            tab("mic")
            show_floor()
            fresh = probe()
            proof.eq(fresh["hint"], STAND_HINT, "on-stand Top hint")
            proof.check("C 0 cm" in fresh["metres"], "on-stand metres include C 0 cm: " + fresh["metres"])
            proof.check(fresh["c"]["room"] is False, "boot C is on the stand")
            proof.check(near(fresh["stand"]["room_l_x"], 4, 1e-6), "migrated room_l_x is 4")

            tab("edit")
            pg.wait_for_timeout(300)
            world_stand = worlds("view3dCanvas")
            proof.check(world_stand is not None, "room view capsuleWorld exists")

            tab("mix")
            pg.click('.place-row [data-place="c"][data-name="room"]')
            pg.wait_for_timeout(200)
            set_room("c", 5.5, 2.5, 0.4)

            tab("mic")
            pg.click("#micPlaneTop")
            show_floor()
            top = probe()
            proof.eq(top["plane"], "top", "Top plane")
            proof.check(top["c"]["room"] is True, "Top C is the room spot")
            proof.check(near(top["c"]["x"], 5.5) and near(top["c"]["y"], 2.5) and near(top["c"]["z"], 0.4),
                        f"Top C spot {top['c']}")
            proof.check(0 <= top["c"]["px"] <= pg.evaluate("() => document.getElementById('micFloorCanvas').width"),
                        "Top C px is inside the canvas")
            proof.check(ROOM_HINT in top["hint"], "Top hint names room spots: " + top["hint"])
            proof.check("C 5.50 m, 0.40 m" in top["metres"], "metres name the room spot: " + top["metres"])
            proof.check("2.50 m high" in top["metres"], "metres use room height: " + top["metres"])
            proof.check("C 0 cm" not in top["metres"], "room metres drop the setback")
            proof.check(top["l"]["room"] is False and top["r"]["room"] is False, "L and R stay on the stand")
            proof.check(near(top["l"]["x"], top["stand"]["mcx"] - top["stand"]["space"] * 0.5, 1e-3),
                        "on-stand L x is the bar")
            proof.check(near(top["l"]["z"], top["stand"]["mcz"], 1e-3), "on-stand L z is the stand")
            proof.eq(top["cHit"], "capC", "Top hit on the room C capsule")
            pg.screenshot(path=str(OUT / "fix_a_mic_top.png"))

            pg.click("#micPlaneSide")
            pg.wait_for_timeout(200)
            side = probe()
            proof.eq(side["plane"], "side", "Side plane")
            proof.check(side["c"]["room"] is True and near(side["c"]["y"], 2.5), f"Side C height {side['c']}")
            proof.check(ROOM_HINT in side["hint"], "Side hint names room spots: " + side["hint"])
            pg.screenshot(path=str(OUT / "fix_a_mic_side.png"))

            tab("edit")
            pg.locator("#view3dCanvas").scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
            world = worlds("view3dCanvas")
            proof.check(world is not None and world["focusMic"] is False, "room view is the whole room")
            if world and world_stand:
                proof.check(
                    near(world["c"]["x"], 5.5) and near(world["c"]["y"], 2.5) and near(world["c"]["z"], 7.6),
                    f"room-view C world {world['c']}",
                )
                proof.check(near(world["l"]["x"], world_stand["l"]["x"]) and near(world["l"]["z"], world_stand["l"]["z"]),
                            f"on-stand L world stayed {world['l']} vs {world_stand['l']}")
                proof.check(near(world["r"]["x"], world_stand["r"]["x"]) and near(world["r"]["z"], world_stand["r"]["z"]),
                            f"on-stand R world stayed {world['r']}")
                proof.check(near(world["l"]["lz"], 0, 1e-6) and near(world["r"]["lz"], 0, 1e-6),
                            f"L/R local z {world['l']['lz']} {world['r']['lz']}")
                proof.check(near(world["l"]["lx"], -float(top["stand"]["space"]) * 0.5, 1e-4),
                            f"L local x stays -half {world['l']['lx']}")
            pg.screenshot(path=str(OUT / "fix_a_room_3d.png"))

            # 3D pointer drag does not move the spot.
            before_drag_3d = pg.evaluate(
                """() => ({
                  x: document.getElementById('room_c_x').value,
                  metres: document.getElementById('liveMetres').textContent,
                  mcx: document.getElementById('mcx').value
                })"""
            )
            box = pg.locator("#view3dCanvas").bounding_box()
            if box:
                drag(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.45, 80, 40)
            after_drag_3d = pg.evaluate(
                """() => ({
                  x: document.getElementById('room_c_x').value,
                  metres: document.getElementById('liveMetres').textContent,
                  mcx: document.getElementById('mcx').value
                })"""
            )
            proof.eq(after_drag_3d, before_drag_3d, "3D pointer drag leaves the spot and the stand")

            tab("mic")
            show_floor()
            pg.wait_for_function(
                """() => {
                  const c = document.getElementById('mic3dCanvas');
                  return c && c._room3d && c.getBoundingClientRect().width > 2;
                }""",
                timeout=10000,
            )
            mic_world = worlds("mic3dCanvas")
            proof.check(mic_world is not None and mic_world["focusMic"] is True, "mic close-up focusMic")
            if mic_world:
                proof.check(near(mic_world["c"]["x"], 5.5) and near(mic_world["c"]["z"], 0.4),
                            f"mic close-up C world z is the room z {mic_world['c']}")
                proof.check(near(mic_world["l"]["lz"], 0, 1e-6), "mic close-up L local z stays 0")

            # Viewports.
            wide = scroll_width()
            proof.check(wide["scrollWidth"] <= 1281, f"1280 scrollWidth {wide}")
            pg.screenshot(path=str(OUT / "fix_a_1280.png"))
            pg.set_viewport_size({"width": 390, "height": 800})
            pg.wait_for_timeout(300)
            tab("mic")
            pg.click("#micPlaneTop")
            show_floor()
            phone = probe()
            proof.check(phone["c"]["room"] is True and near(phone["c"]["x"], 5.5) and near(phone["c"]["z"], 0.4),
                        f"390 Top still reads the room spot {phone['c']}")
            narrow = scroll_width()
            proof.check(narrow["scrollWidth"] <= 391, f"390 scrollWidth {narrow}")
            pg.screenshot(path=str(OUT / "fix_a_390.png"), full_page=True)
            pg.set_viewport_size({"width": 1280, "height": 900})
            pg.wait_for_timeout(250)

            # Top drag writes room_c_x or room_c_z only.
            tab("mic")
            pg.click("#micPlaneTop")
            show_floor()
            pre = probe()
            dx = -120 if pre["c"]["cssX"] > 180 else 120
            drag(pre["c"]["cssX"], pre["c"]["cssY"], dx, 0)
            post = probe()
            moved_xz = (not near(post["stand"]["room_c_x"], pre["stand"]["room_c_x"], 0.005)
                        or not near(post["stand"]["room_c_z"], pre["stand"]["room_c_z"], 0.005))
            proof.check(moved_xz, f"Top drag moved room_c_x/z {pre['stand']} -> {post['stand']}")
            proof.check(near(post["stand"]["room_c_y"], pre["stand"]["room_c_y"], 1e-6), "Top drag leaves room_c_y")
            for key in ("space", "centre_dz", "mcx", "mcz", "my", "my_c", "room_l_x"):
                proof.check(near(post["stand"][key], pre["stand"][key], 1e-6),
                            f"Top drag leaves {key}")
            proof.eq(post["stand"]["place_l"], "array", "Top drag leaves L on the stand")

            # Side drag writes room_c_y only.
            pg.click("#micPlaneSide")
            pg.wait_for_timeout(200)
            show_floor()
            pre_s = probe()
            dy = 90 if pre_s["c"]["cssY"] < 80 else -90
            drag(pre_s["c"]["cssX"], pre_s["c"]["cssY"], 0, dy)
            post_s = probe()
            proof.check(not near(post_s["stand"]["room_c_y"], pre_s["stand"]["room_c_y"], 0.005),
                        f"Side drag moved room_c_y {pre_s['stand']['room_c_y']} -> {post_s['stand']['room_c_y']}")
            proof.check(near(post_s["stand"]["my"], pre_s["stand"]["my"], 1e-6), "Side drag leaves my")
            proof.check(near(post_s["stand"]["my_c"] or 0, pre_s["stand"]["my_c"] or 0, 1e-6)
                        or (post_s["stand"]["my_c"] is None and pre_s["stand"]["my_c"] is None),
                        f"Side drag leaves my_c {pre_s['stand']['my_c']} {post_s['stand']['my_c']}")

            # On-stand L drag still changes space and not room_l_x.
            pg.click("#micPlaneTop")
            tab("mix")
            pg.click('.place-row [data-place="c"][data-name="array"]')
            pg.wait_for_timeout(200)
            tab("mic")
            pg.click("#micPlaneTop")
            show_floor()
            pre_l = probe()
            proof.check(pre_l["c"]["room"] is False and pre_l["l"]["room"] is False, "C is back on the stand")
            drag(pre_l["l"]["cssX"], pre_l["l"]["cssY"], -100, 0)
            post_l = probe()
            proof.check(not near(post_l["stand"]["space"], pre_l["stand"]["space"], 0.005),
                        f"on-stand L drag changes space {pre_l['stand']['space']} -> {post_l['stand']['space']}")
            proof.check(near(post_l["stand"]["room_l_x"], pre_l["stand"]["room_l_x"], 1e-6),
                        "on-stand L drag leaves room_l_x")
            proof.check(near(post_l["stand"]["centre_dz"], pre_l["stand"]["centre_dz"], 1e-6),
                        "on-stand L drag leaves centre_dz")
            proof.eq(post_l["stand"]["place_l"], "array", "on-stand L drag leaves place_l array")

            # Binaural Top skips C.
            boot()
            tab("mic")
            pg.select_option("#mic_setup", "binaural")
            pg.wait_for_timeout(300)
            pg.click("#micPlaneTop")
            show_floor()
            ears = probe()
            proof.check(" · C " not in ears["metres"], "binaural metres omit C: " + ears["metres"])
            proof.check(ears["cHit"] not in ("capC", "yawC"), f"binaural Top does not hit C ({ears['cHit']})")
            pg.screenshot(path=str(OUT / "fix_a_binaural_top.png"))

            proof.check(not page_errors, "page errors: " + " | ".join(page_errors[:6]))
            proof.notes.append(f"scroll 1280 {wide} ; 390 {narrow}")
            proof.notes.append(f"console errors {len(console_errors)}")
            proof.notes.append(f"render posts {len(posts)} ; L-check index {boot_keys_note}")
            if console_errors:
                proof.notes.append("console: " + " | ".join(console_errors[:6]))

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        try:
            wav.unlink()
        except OSError:
            pass

    idle_after = port_open(7860)
    report = {
        "port": port,
        "idle_7860_before": idle_before,
        "idle_7860_after": idle_after,
        "ok": proof.notes,
        "errors": proof.errors,
        "page_errors": page_errors,
    }
    (OUT / "prove_fix_a_result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"errors": proof.errors, "n_ok": len(proof.notes), "idle_before": idle_before, "idle_after": idle_after, "port": port}, indent=2))
    if proof.errors or idle_before != idle_after:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
