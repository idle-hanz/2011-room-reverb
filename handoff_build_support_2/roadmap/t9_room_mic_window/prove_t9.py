"""T9 Mic-page room window, Return to stand, B6 and B7.

Playwright on the real Mic tab. Windows Chrome, free port, 7860 left alone.
Shots land in this folder.
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
    posts: list[dict] = []
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
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("dialog", lambda d: d.dismiss())

        def on_request(req) -> None:
            if req.method == "POST" and req.url.endswith("/api/live_params"):
                try:
                    posts.append(json.loads(req.post_data or "{}"))
                except json.JSONDecodeError:
                    posts.append({"_bad": True})

        page.on("request", on_request)
        try:
            with page.expect_response(lambda r: r.url.endswith("/api/defaults") and r.ok, timeout=30000):
                page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)

            def show(view: str) -> None:
                page.locator(f'.view-tab[data-view="{view}"]').click()
                page.wait_for_timeout(200)

            def row_hidden(cap: str) -> bool:
                return page.evaluate(
                    """(cap) => {
                      const row = document.querySelector('[data-room-spot="' + cap + '"]');
                      return !row || row.hidden === true;
                    }""",
                    cap,
                )

            def type_field(cap: str, key: str, value: str) -> None:
                loc = page.locator(f"#room_{cap}_{key}")
                loc.scroll_into_view_if_needed()
                loc.fill(value)
                loc.dispatch_event("input")

            show("mic")
            closed = {cap: row_hidden(cap) for cap in ("l", "c", "r")}
            box_hidden = page.locator("#roomFields").get_attribute("hidden") is not None
            id_counts = page.evaluate(
                """() => {
                  const out = {};
                  for (const cap of ["l", "c", "r"]) {
                    for (const k of ["x", "z", "y", "yaw"]) {
                      const id = "room_" + cap + "_" + k;
                      out[id] = document.querySelectorAll("#" + id).length;
                    }
                  }
                  out.roomFields = document.querySelectorAll("#roomFields").length;
                  out.micPolarC = document.querySelectorAll("#micPolarC").length;
                  return out;
                }"""
            )

            show("mix")
            page.locator('.desk-strip[data-cap="r"] [data-place="r"][data-name="room"]').click()
            page.wait_for_timeout(200)
            show("mic")
            page.locator('[data-room-spot="r"]').scroll_into_view_if_needed()
            open_rows = {cap: row_hidden(cap) for cap in ("l", "c", "r")}
            title = page.locator('[data-room-spot="r"] .room-window-title').inner_text()
            # Source x/z have no inputs. The live metres line is "Src " + fmt(sx) + "," + fmt(sz).
            painted = page.evaluate(
                """() => {
                  const row = document.querySelector('[data-room-spot="r"]');
                  const spot = {
                    x: Number(document.getElementById("room_r_x").value),
                    y: Number(document.getElementById("room_r_y").value),
                    z: Number(document.getElementById("room_r_z").value)
                  };
                  const live = document.getElementById("liveMetres").textContent || "";
                  const m = live.match(/Src\\s+([0-9.]+),([0-9.]+)/);
                  const src = {
                    x: m ? Number(m[1]) : NaN,
                    y: Number(document.getElementById("sy").value),
                    z: m ? Number(m[2]) : NaN
                  };
                  const W = Number(document.getElementById("W").value);
                  const L = Number(document.getElementById("L").value);
                  return {
                    source: row.querySelector('[data-room-read="source"]').textContent,
                    wall: row.querySelector('[data-room-read="wall"]').textContent,
                    expectSource: "Source: " + RRRoomWindow.sourceMetres(src, spot).toFixed(1) + " m",
                    expectWall: "Nearest wall: " + RRRoomWindow.nearestWallMetres(spot, W, L).toFixed(1) + " m",
                    live: live, spot: spot, src: src
                  };
                }"""
            )
            polar = {"yaw": "", "pe": "", "w": 0}
            for _ in range(40):
                polar = page.evaluate(
                    """() => {
                      const c = document.getElementById("roomPolarR");
                      const style = getComputedStyle(c);
                      return {
                        yaw: c.dataset.drawnYaw || "",
                        pe: style.pointerEvents,
                        w: c.getBoundingClientRect().width
                      };
                    }"""
                )
                if polar["yaw"] and polar["w"] >= 40:
                    break
                page.wait_for_timeout(250)
            pattern_home = page.evaluate(
                """() => {
                  const preset = document.getElementById("mic_preset_r");
                  const block = document.getElementById("rPatternBlock");
                  return {
                    presetInRoom: !!preset.closest("[data-room-spot='r']"),
                    patternHidden: !!(block && block.hidden),
                    splitParent: document.getElementById("sideSplitR").parentElement.id
                  };
                }"""
            )
            page.locator('[data-link="split"]').click()
            page.wait_for_timeout(150)
            pattern_split = page.evaluate(
                """() => {
                  const preset = document.getElementById("mic_preset_r");
                  const fam = document.getElementById("family_r");
                  const pol = document.getElementById("polar_r");
                  const hpf = document.getElementById("mic_hpf_r");
                  const block = document.getElementById("rPatternBlock");
                  return {
                    presetInRoom: !!preset.closest("[data-room-spot='r']"),
                    famInRoom: !!fam.closest("[data-room-spot='r']"),
                    polInRoom: !!pol.closest("[data-room-spot='r']"),
                    hpfInRoom: !!hpf.closest("[data-room-spot='r']"),
                    patternHidden: !!(block && block.hidden)
                  };
                }"""
            )
            page.locator('[data-link="mirror"]').click()
            page.wait_for_timeout(150)
            pattern_mirror = page.evaluate(
                """() => document.getElementById("sideSplitR").parentElement.id"""
            )
            page.locator("#roomFields").screenshot(path=str(OUT / "t9_room_window_r.png"))

            type_field("r", "x", "1.00")
            type_field("r", "z", "6.00")
            type_field("r", "y", "1.50")
            typed = page.evaluate(
                """() => ({
                  x: document.getElementById("room_r_x").value,
                  z: document.getElementById("room_r_z").value,
                  y: document.getElementById("room_r_y").value
                })"""
            )
            show("edit")
            page.locator("#floorCanvas").scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            pixel = page.evaluate(
                """() => {
                  const c = document.getElementById("floorCanvas");
                  const W = Number(document.getElementById("W").value);
                  const L = Number(document.getElementById("L").value);
                  const pad = 52;
                  const scale = Math.min((c.width - pad * 2) / W, (c.height - pad * 2) / L);
                  const rw = W * scale, rh = L * scale;
                  const ox = (c.width - rw) / 2, oy = (c.height - rh) / 2 + 4;
                  const x = Number(document.getElementById("room_r_x").value);
                  const z = Number(document.getElementById("room_r_z").value);
                  const px = Math.round(ox + x * scale);
                  const py = Math.round(oy + (L - z) * scale);
                  const d = c.getContext("2d").getImageData(px, py, 1, 1).data;
                  const old = c.getContext("2d").getImageData(
                    Math.round(ox + 4 * scale), Math.round(oy + (L - 2) * scale), 1, 1).data;
                  return { r: d[0], g: d[1], b: d[2], px: px, py: py,
                           oldR: old[0], oldG: old[1], oldB: old[2] };
                }"""
            )
            page.locator("#floorCanvas").screenshot(path=str(OUT / "t9_source_moved.png"))

            def layouts() -> dict:
                return page.evaluate(
                    """() => {
                      const W = Number(document.getElementById("W").value);
                      const L = Number(document.getElementById("L").value);
                      const c = document.getElementById("floorCanvas");
                      const pad = 52;
                      const scale = Math.min((c.width - pad * 2) / W, (c.height - pad * 2) / L);
                      const rw = W * scale, rh = L * scale;
                      return { ox: (c.width - rw) / 2, oy: (c.height - rh) / 2 + 4, scale, W, L, bw: c.width, bh: c.height };
                    }"""
                )

            def css_of(bx: float, by: float, lay: dict) -> tuple[float, float]:
                box = page.locator("#floorCanvas").bounding_box()
                if not box:
                    raise SystemExit("floorCanvas has no box")
                return box["x"] + bx * box["width"] / lay["bw"], box["y"] + by * box["height"] / lay["bh"]

            lay = layouts()
            x0, z0 = 1.0, 6.0
            x1, z1 = 2.5, 4.0
            b0 = (lay["ox"] + x0 * lay["scale"], lay["oy"] + (lay["L"] - z0) * lay["scale"])
            b1 = (lay["ox"] + x1 * lay["scale"], lay["oy"] + (lay["L"] - z1) * lay["scale"])
            p0 = css_of(*b0, lay)
            p1 = css_of(*b1, lay)
            page.mouse.move(*p0)
            page.mouse.down()
            page.mouse.move(*p1, steps=12)
            page.mouse.up()
            page.wait_for_timeout(200)
            dragged = page.evaluate(
                """() => ({
                  x: document.getElementById("room_r_x").value,
                  z: document.getElementById("room_r_z").value,
                  y: document.getElementById("room_r_y").value
                })"""
            )
            show("mic")
            page.locator('[data-room-spot="r"] [data-place="r"][data-name="array"]').click()
            page.wait_for_timeout(200)
            after_return = {cap: row_hidden(cap) for cap in ("l", "c", "r")}
            place_r = page.evaluate(
                """() => document.querySelector('.desk-strip[data-cap="r"] [data-place="r"][data-name="array"]').getAttribute("aria-pressed")"""
            )
            page.screenshot(path=str(OUT / "t9_return_r.png"))

            page.locator('#thirdMicRow [data-third="centre"]').click()
            page.wait_for_timeout(150)
            prior = page.evaluate(
                """() => document.querySelector('#thirdMicRow [data-third="centre"]').getAttribute("aria-pressed")"""
            )
            page.locator('#thirdMicRow [data-third="room"]').click()
            page.wait_for_timeout(200)
            centre_open = not row_hidden("c")
            page.locator('[data-room-spot="c"]').screenshot(path=str(OUT / "t9_centre_room.png"))
            centre_parked = page.evaluate(
                """() => {
                  const preset = document.getElementById("mic_preset_centre");
                  const fam = document.getElementById("family_c");
                  const pol = document.getElementById("polar_c");
                  const hpf = document.getElementById("mic_hpf_centre");
                  const block = document.getElementById("centrePatternBlock");
                  return {
                    preset: !!preset.closest("[data-room-spot='c']"),
                    fam: !!fam.closest("[data-room-spot='c']"),
                    pol: !!pol.closest("[data-room-spot='c']"),
                    hpf: !!hpf.closest("[data-room-spot='c']"),
                    patternHidden: !!(block && block.hidden)
                  };
                }"""
            )
            page.locator('[data-room-spot="c"] [data-place="c"][data-name="array"]').click()
            page.wait_for_timeout(200)
            centre_back = page.evaluate(
                """() => ({
                  hidden: document.querySelector('[data-room-spot="c"]').hidden === true,
                  third: document.querySelector('#thirdMicRow [aria-pressed="true"]').getAttribute("data-third"),
                  presetHome: document.getElementById("mic_preset_centre").closest("#centreMicChoice") != null
                })"""
            )
            page.screenshot(path=str(OUT / "t9_centre_returned.png"))

            page.select_option("#mic_setup", "binaural")
            page.wait_for_timeout(300)
            binaural = page.evaluate(
                """() => {
                  function hid(id) {
                    const n = document.getElementById(id);
                    if (!n) return true;
                    if (n.hidden) return true;
                    return getComputedStyle(n).display === "none";
                  }
                  const link = document.getElementById("link_heights_mic");
                  const lab = link ? link.parentElement : null;
                  const src = document.getElementById("link_heights");
                  return {
                    third: hid("thirdMicRow"),
                    linkLabel: !!(lab && (lab.hidden || getComputedStyle(lab).display === "none")),
                    sourceLinkHidden: !!(src && src.hidden),
                    align: hid("alignHorizontalRow"),
                    space: hid("spaceRow"),
                    hint: document.getElementById("micHaloHint").textContent,
                    badge: document.getElementById("micHonestyBadge").textContent,
                    metres: document.getElementById("liveMetresMic").textContent,
                    cCol: document.querySelector('#micPolarTrio .mic-polar-col[data-cap="C"]').hidden === true
                  };
                }"""
            )
            page.screenshot(path=str(OUT / "t9_binaural.png"))

            page.select_option("#mic_setup", "ortf")
            page.wait_for_timeout(250)
            before_mono = page.evaluate(
                """() => ({
                  space: document.getElementById("space").value,
                  align: document.getElementById("align_horizontal").checked
                })"""
            )
            page.select_option("#mic_setup", "mono_c")
            page.wait_for_timeout(250)
            # A space edit marks the setup custom, so the hide would lift.
            # Snapshot the preset space, then resync through Colour. The hide
            # path must leave that value and the align checkbox alone.
            mono_snap = page.evaluate(
                """() => ({
                  space: document.getElementById("space").value,
                  align: document.getElementById("align_horizontal").checked,
                  setup: document.getElementById("mic_setup").value
                })"""
            )
            page.select_option("#colour_mode", "BYPASS")
            page.wait_for_timeout(100)
            page.select_option("#colour_mode", "MEASURED_SHELF")
            page.wait_for_timeout(150)
            mono = page.evaluate(
                """() => {
                  function hid(id) {
                    const n = document.getElementById(id);
                    if (!n) return true;
                    if (n.hidden) return true;
                    return getComputedStyle(n).display === "none";
                  }
                  const off = document.querySelector('#thirdMicRow button[data-third="off"]');
                  return {
                    link: hid("linkModeRow"),
                    third: hid("thirdMicRow"),
                    offDisabled: !!(off && off.disabled),
                    align: hid("alignHorizontalRow"),
                    space: hid("spaceRow"),
                    spaceValue: document.getElementById("space").value,
                    alignOn: document.getElementById("align_horizontal").checked
                  };
                }"""
            )
            page.screenshot(path=str(OUT / "t9_mono.png"))

            page.select_option("#mic_setup", "ortf")
            page.wait_for_timeout(200)
            show("mix")
            page.locator('.desk-strip[data-cap="r"] [data-place="r"][data-name="room"]').click()
            page.wait_for_timeout(150)
            show("mic")

            def overflow(width: int) -> dict:
                page.set_viewport_size({"width": width, "height": 844})
                page.wait_for_timeout(250)
                show("mic")
                page.locator("#room_r_x").scroll_into_view_if_needed()
                report = page.evaluate(
                    """(limit) => {
                      const ids = ["room_r_x", "room_r_z", "room_r_y", "room_r_yaw"];
                      const controls = ids.map((id) => {
                        const el = document.getElementById(id);
                        const r = el.getBoundingClientRect();
                        return { id: id, left: r.left, right: r.right, width: r.width, n: document.querySelectorAll("#" + id).length };
                      });
                      return {
                        sw: document.documentElement.scrollWidth,
                        cw: document.documentElement.clientWidth,
                        controls: controls,
                        off: controls.filter((c) => c.n !== 1 || c.left < -1 || c.right > limit + 1)
                      };
                    }""",
                    width,
                )
                page.screenshot(path=str(OUT / f"t9_{width}.png"), full_page=True)
                return report

            wide = overflow(1280)
            phone = overflow(390)

            new_keys = sorted({k for row in posts for k in row if k not in ("sample_rate", "colour_rev")})
            banned = [k for k in new_keys if k.endswith("Row") or "nearest" in k or k.startswith("room_read")]

            result = {
                "port": port,
                "idle_7860_left_alone": idle_7860,
                "page_errors": errs,
                "closed": closed,
                "box_hidden": box_hidden,
                "id_counts": id_counts,
                "open_rows": open_rows,
                "title": title,
                "painted": painted,
                "polar": polar,
                "pattern_home": pattern_home,
                "pattern_split": pattern_split,
                "pattern_mirror": pattern_mirror,
                "typed": typed,
                "pixel": pixel,
                "dragged": dragged,
                "after_return": after_return,
                "place_r": place_r,
                "prior_centre_pressed": prior,
                "centre_open": centre_open,
                "centre_parked": centre_parked,
                "centre_back": centre_back,
                "binaural": binaural,
                "before_mono": before_mono,
                "mono_snap": mono_snap,
                "mono": mono,
                "wide": wide,
                "phone": phone,
                "banned_keys": banned,
            }
            (OUT / "t9_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

            problems = []
            if errs:
                problems.append("page errors: " + " | ".join(errs))
            if not box_hidden or not all(closed.values()):
                problems.append(f"window showed with nobody on Room: {closed} box {box_hidden}")
            if any(id_counts[k] != 1 for k in id_counts):
                problems.append(f"cloned ids: {id_counts}")
            if open_rows != {"l": True, "c": True, "r": False}:
                problems.append(f"R room did not open only R: {open_rows}")
            if title != "Room mic (R)":
                problems.append("title " + title)
            if painted["source"] != painted["expectSource"] or painted["wall"] != painted["expectWall"]:
                problems.append(f"readouts {painted['source']} / {painted['wall']} != {painted['expectSource']} / {painted['expectWall']}")
            if polar["pe"] != "none" or not polar["yaw"] or polar["w"] < 40:
                problems.append(f"room polar {polar}")
            if pattern_home["presetInRoom"] or pattern_home["splitParent"] != "sidePatternSplit":
                problems.append(f"mirror parked R controls: {pattern_home}")
            if not pattern_home["patternHidden"]:
                problems.append("measured pattern was visible in the stand split block")
            if not all(pattern_split[k] for k in ("presetInRoom", "famInRoom", "polInRoom", "hpfInRoom", "patternHidden")):
                problems.append(f"split did not move R controls: {pattern_split}")
            if pattern_mirror != "sidePatternSplit":
                problems.append("mirror did not put R controls back: " + str(pattern_mirror))
            if abs(float(typed["x"]) - 1.0) > 0.001 or abs(float(typed["z"]) - 6.0) > 0.001:
                problems.append(f"typing did not stick: {typed}")
            if not (pixel["g"] > 150 and pixel["g"] > pixel["r"] + 40 and pixel["g"] > pixel["b"]):
                problems.append(f"source object was not the R colour at the typed spot: {pixel}")
            if abs(float(dragged["x"]) - 2.5) > 0.02 or abs(float(dragged["z"]) - 4.0) > 0.02:
                problems.append(f"T8 drag did not update the window: {dragged}")
            if abs(float(dragged["y"]) - 1.5) > 0.02:
                problems.append(f"floor drag wrote height: {dragged}")
            if after_return["r"] is not True or place_r != "true":
                problems.append(f"return did not hide R: {after_return} pressed {place_r}")
            if prior != "true" or not centre_open:
                problems.append(f"centre room chip did not open: prior {prior} open {centre_open}")
            if not all(centre_parked[k] for k in ("preset", "fam", "pol", "hpf", "patternHidden")):
                problems.append(f"C controls did not move: {centre_parked}")
            if not centre_back["hidden"] or centre_back["third"] != "centre" or not centre_back["presetHome"]:
                problems.append(f"return did not restore centre: {centre_back}")
            if not binaural["third"] or not binaural["linkLabel"] or binaural["sourceLinkHidden"]:
                problems.append(f"binaural hide: {binaural}")
            if "SADIE II KU100" not in binaural["hint"] or "Left and right ears" not in binaural["hint"]:
                problems.append("halo " + binaural["hint"])
            if binaural["badge"] != "Head: SADIE II KU100":
                problems.append("badge " + binaural["badge"])
            if "preset data: measured" in binaural["badge"]:
                problems.append("badge fell back to measured")
            if "cm" in binaural["metres"] and "C " in binaural["metres"]:
                problems.append("live metres still names C: " + binaural["metres"])
            if not binaural["cCol"]:
                problems.append("binaural still shows the C polar column")
            if not mono["link"] or not mono["third"] or not mono["offDisabled"]:
                problems.append(f"mono hide: {mono}")
            if mono["align"] or mono["space"]:
                problems.append(f"mono hid align or space: {mono}")
            if mono_snap["setup"] != "mono_c":
                problems.append(f"mono setup did not apply: {mono_snap}")
            if mono["spaceValue"] != mono_snap["space"] or mono["alignOn"] != mono_snap["align"]:
                problems.append(f"mono wrote align or space: snap {mono_snap} after {mono}")
            if not mono["alignOn"] or mono["alignOn"] != before_mono["align"]:
                problems.append(f"mono changed align: before {before_mono} after {mono}")
            if wide["sw"] > 1281 or wide["off"]:
                problems.append(f"1280 overflow: {wide}")
            if phone["sw"] > 391 or phone["off"]:
                problems.append(f"390 overflow: {phone}")
            if banned:
                problems.append("posted keys: " + ", ".join(banned))
            if problems:
                raise SystemExit("FAIL\n" + "\n".join(problems))
            print("PASS")
            print(json.dumps({
                "painted": painted,
                "dragged": dragged,
                "centre_back": centre_back,
                "binaural_badge": binaural["badge"],
                "mono": mono,
                "phone_sw": phone["sw"],
                "wide_sw": wide["sw"],
                "page_errors": errs,
            }, indent=2))
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
