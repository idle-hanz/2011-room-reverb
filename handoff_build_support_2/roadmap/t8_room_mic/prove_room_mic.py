"""T8 Source-page room mic. Playwright on the real #floorCanvas and #elevCanvas.

One floor drag, one height drag, one aim drag, each matching the four number
fields after typing the same numbers. The floor drag stops 10 cm short of a
wall. An empty click still moves the source or the stand. Does not use port 7860.
"""
from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SW = ROOT / "software"
PY = SW / ".venv" / "Scripts" / "python.exe"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
OUT = Path(__file__).resolve().parent
CAP = "r"


def free_port() -> int:
    for _ in range(8):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        if port != 7860:
            return port
    raise SystemExit("could not take a free port other than 7860")


def listening(port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.2)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def wait_up(port: int, proc: subprocess.Popen, seconds: float = 30) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
            raise SystemExit("server exited: " + err[-800:])
        if listening(port):
            return
        time.sleep(0.15)
    raise SystemExit("server did not listen")


def nums(fields: dict) -> dict:
    return {k: float(fields[k]) for k in ("x", "z", "y", "yaw")}


def same(a: dict, b: dict) -> bool:
    return all(abs(a[k] - b[k]) < 1e-9 for k in ("x", "z", "y", "yaw"))


def main() -> None:
    if not CHROME.exists():
        raise SystemExit("Chrome is not installed")
    idle_7860 = listening(7860)
    port = free_port()
    proc = subprocess.Popen(
        [str(PY), "-c",
         "import uvicorn; from app_server import app; "
         f"uvicorn.run(app, host='127.0.0.1', port={port}, log_level='warning')"],
        cwd=str(SW),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}/"
    OUT.mkdir(parents=True, exist_ok=True)
    errs: list[str] = []
    try:
        wait_up(port, proc)
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            executable_path=str(CHROME),
            headless=True,
            args=[
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )
        page = browser.new_page(viewport={"width": 1500, "height": 1100})
        page.on("pageerror", lambda e: errs.append(str(e)))
        try:
            with page.expect_response(lambda r: r.url.endswith("/api/defaults") and r.ok, timeout=30000):
                page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(400)
            page.locator('.view-tab[data-view="mix"]').click()
            page.locator('[data-place="r"][data-name="room"]').click()
            page.wait_for_function(
                """() => document.querySelector('[data-place="r"][data-name="room"]').getAttribute('aria-pressed') === 'true'"""
            )

            def show(view: str) -> None:
                page.locator(f'.view-tab[data-view="{view}"]').click()

            def read_fields() -> dict:
                return page.evaluate(
                    """(cap) => {
                      const o = {};
                      for (const k of ["x", "z", "y", "yaw"]) {
                        o[k] = document.getElementById("room_" + cap + "_" + k).value;
                      }
                      o.readout = document.getElementById("liveMetres").textContent;
                      return o;
                    }""",
                    CAP,
                )

            def type_fields(vals: dict) -> None:
                show("mic")
                for k, v in vals.items():
                    loc = page.locator(f"#room_{CAP}_{k}")
                    loc.scroll_into_view_if_needed()
                    loc.fill(f"{float(v):.2f}" if k != "yaw" else f"{float(v):.1f}")
                    loc.dispatch_event("input")

            def layouts() -> dict:
                return page.evaluate(
                    """() => {
                      const W = Number(document.getElementById("W").value);
                      const H = Number(document.getElementById("H").value);
                      const L = Number(document.getElementById("L").value);
                      const c = document.getElementById("floorCanvas");
                      const pad = 52;
                      const scale = Math.min((c.width - pad * 2) / W, (c.height - pad * 2) / L);
                      const rw = W * scale, rh = L * scale;
                      const e = document.getElementById("elevCanvas");
                      const padX = 52, padY = 28;
                      const es = Math.min((e.width - padX * 2) / L, (e.height - padY * 2) / H);
                      const erw = L * es, erh = H * es;
                      return {
                        floor: { ox: (c.width - rw) / 2, oy: (c.height - rh) / 2 + 4, scale, W, L, bw: c.width, bh: c.height },
                        elev: { ox: (e.width - erw) / 2, oy: (e.height - erh) / 2, scale: es, L, H, bw: e.width, bh: e.height }
                      };
                    }"""
                )

            def css_of(canvas_sel: str, bmp_x: float, bmp_y: float, bw: float, bh: float) -> tuple[float, float]:
                box = page.locator(canvas_sel).bounding_box()
                if not box:
                    raise SystemExit(canvas_sel + " has no box")
                return (
                    box["x"] + bmp_x * box["width"] / bw,
                    box["y"] + bmp_y * box["height"] / bh,
                )

            def drag(canvas_sel: str, x0: float, y0: float, x1: float, y1: float) -> None:
                page.mouse.move(x0, y0)
                page.mouse.down()
                page.mouse.move(x1, y1, steps=12)
                page.mouse.up()

            def floor_bmp(x: float, z: float, lay: dict) -> tuple[float, float]:
                return lay["ox"] + x * lay["scale"], lay["oy"] + (lay["L"] - z) * lay["scale"]

            def elev_bmp(z: float, y: float, lay: dict) -> tuple[float, float]:
                return lay["ox"] + z * lay["scale"], lay["oy"] + (lay["H"] - y) * lay["scale"]

            base = {"x": 3.0, "z": 2.0, "y": 1.5, "yaw": 10.0}
            type_fields(base)
            show("edit")
            page.locator("#floorCanvas").scroll_into_view_if_needed()
            page.locator("#floorCanvas").screenshot(path=str(OUT / "t8_floor_room_mic.png"))

            lay = layouts()
            fl = lay["floor"]
            bx, by = floor_bmp(base["x"], base["z"], fl)
            tx, ty = floor_bmp(2.5, 4.0, fl)
            drag("#floorCanvas", *css_of("#floorCanvas", bx, by, fl["bw"], fl["bh"]),
                 *css_of("#floorCanvas", tx, ty, fl["bw"], fl["bh"]))
            dragged_floor = nums(read_fields())
            page.locator("#floorCanvas").screenshot(path=str(OUT / "t8_floor_drag.png"))
            stand_after_floor = read_fields()["readout"]
            type_fields(base)
            type_fields({"x": dragged_floor["x"], "z": dragged_floor["z"], "y": dragged_floor["y"], "yaw": dragged_floor["yaw"]})
            typed_floor = nums(read_fields())

            type_fields(base)
            show("edit")
            page.locator("#elevCanvas").scroll_into_view_if_needed()
            lay = layouts()
            el = lay["elev"]
            hx, hy = elev_bmp(base["z"], base["y"], el)
            htx, hty = elev_bmp(base["z"], 2.0, el)
            drag("#elevCanvas", *css_of("#elevCanvas", hx, hy, el["bw"], el["bh"]),
                 *css_of("#elevCanvas", htx, hty, el["bw"], el["bh"]))
            dragged_height = nums(read_fields())
            page.locator("#elevCanvas").screenshot(path=str(OUT / "t8_side_height.png"))
            type_fields(base)
            type_fields(dragged_height)
            typed_height = nums(read_fields())

            type_fields(base)
            show("edit")
            page.locator("#floorCanvas").scroll_into_view_if_needed()
            lay = layouts()
            fl = lay["floor"]
            cx, cy = floor_bmp(base["x"], base["z"], fl)
            import math
            yaw = math.radians(base["yaw"])
            ax, ay = cx + 28 * math.sin(yaw), cy - 28 * math.cos(yaw)
            zx, zy = cx, cy - 70
            drag("#floorCanvas", *css_of("#floorCanvas", ax, ay, fl["bw"], fl["bh"]),
                 *css_of("#floorCanvas", zx, zy, fl["bw"], fl["bh"]))
            dragged_aim = nums(read_fields())
            page.locator("#floorCanvas").screenshot(path=str(OUT / "t8_aim.png"))
            type_fields(base)
            type_fields(dragged_aim)
            typed_aim = nums(read_fields())

            type_fields(base)
            show("edit")
            page.locator("#floorCanvas").scroll_into_view_if_needed()
            lay = layouts()
            fl = lay["floor"]
            sx, sy = floor_bmp(base["x"], base["z"], fl)
            wx, wy = floor_bmp(-1.0, base["z"], fl)
            drag("#floorCanvas", *css_of("#floorCanvas", sx, sy, fl["bw"], fl["bh"]),
                 *css_of("#floorCanvas", wx, wy, fl["bw"], fl["bh"]))
            wall = nums(read_fields())
            page.locator("#floorCanvas").screenshot(path=str(OUT / "t8_wall_stop.png"))
            type_fields({"x": wall["x"], "z": wall["z"], "y": wall["y"], "yaw": wall["yaw"]})
            typed_wall = nums(read_fields())

            before_empty = read_fields()
            show("edit")
            page.locator("#floorCanvas").scroll_into_view_if_needed()
            lay = layouts()
            fl = lay["floor"]
            ex, ey = floor_bmp(2.0, 5.0, fl)
            page.mouse.click(*css_of("#floorCanvas", ex, ey, fl["bw"], fl["bh"]))
            page.wait_for_timeout(100)
            after_empty = read_fields()
            page.locator("#floorCanvas").screenshot(path=str(OUT / "t8_empty_click.png"))
            show("mic")
            page.locator("#roomFields").screenshot(path=str(OUT / "t8_fields.png"))

            result = {
                "port": port,
                "idle_7860_left_alone": idle_7860,
                "page_errors": errs,
                "floor": {"drag": dragged_floor, "typed": typed_floor, "stand_readout": stand_after_floor},
                "height": {"drag": dragged_height, "typed": typed_height},
                "aim": {"drag": dragged_aim, "typed": typed_aim},
                "wall": {"drag": wall, "typed": typed_wall},
                "empty": {"before": before_empty["readout"], "after": after_empty["readout"],
                          "fields_before": nums(before_empty), "fields_after": nums(after_empty)},
            }
            (OUT / "t8_room_mic_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

            problems = []
            if errs:
                problems.append("page errors: " + " | ".join(errs))
            if not same(dragged_floor, typed_floor):
                problems.append(f"floor drag {dragged_floor} != typed {typed_floor}")
            if abs(dragged_floor["x"] - 2.5) > 1e-9 or abs(dragged_floor["z"] - 4.0) > 1e-9:
                problems.append(f"floor drag did not land on 2.50, 4.00: {dragged_floor}")
            if abs(dragged_floor["y"] - base["y"]) > 1e-9 or abs(dragged_floor["yaw"] - base["yaw"]) > 1e-9:
                problems.append(f"floor drag wrote height or aim: {dragged_floor}")
            if "Mic 3.00,1.50" not in stand_after_floor:
                problems.append("stand moved on floor drag: " + stand_after_floor)
            if not same(dragged_height, typed_height):
                problems.append(f"height drag {dragged_height} != typed {typed_height}")
            if abs(dragged_height["y"] - 2.0) > 1e-9 or abs(dragged_height["z"] - base["z"]) > 1e-9:
                problems.append(f"height drag did not write y=2.00 only: {dragged_height}")
            if not same(dragged_aim, typed_aim):
                problems.append(f"aim drag {dragged_aim} != typed {typed_aim}")
            if abs(dragged_aim["yaw"] - 0.0) > 1e-9 or abs(dragged_aim["x"] - base["x"]) > 1e-9:
                problems.append(f"aim drag did not write yaw=0 only: {dragged_aim}")
            if abs(wall["x"] - 0.1) > 1e-9 or abs(wall["z"] - base["z"]) > 1e-9:
                problems.append(f"wall stop was not 0.10: {wall}")
            if not same(wall, typed_wall):
                problems.append(f"wall value {wall} != typed {typed_wall}")
            if not same(nums(before_empty), nums(after_empty)):
                problems.append("empty click changed the room fields")
            if "Src 2.00,5.00" not in after_empty["readout"]:
                problems.append("empty click did not move the source: " + after_empty["readout"])
            if "Mic 3.00,1.50" not in after_empty["readout"]:
                problems.append("empty click moved the stand: " + after_empty["readout"])
            if problems:
                raise SystemExit("FAIL\n" + "\n".join(problems))
            print("PASS")
            print(json.dumps({k: result[k] for k in ("floor", "height", "aim", "wall", "empty", "page_errors")}, indent=2))
        finally:
            browser.close()
            pw.stop()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
