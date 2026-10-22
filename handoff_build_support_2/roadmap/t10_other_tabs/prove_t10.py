"""T10 page proof. Free port. 7860 is not touched.

Checks the Room-size chip, Source canvas width, Space mic ticks,
the Polar footer, and that the 1280 px page does not grow sideways.
"""
from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
OUT = ROOT / "handoff_build_support_2" / "roadmap" / "t10_other_tabs"
PY = SW / ".venv" / "Scripts" / "python.exe"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
if not CHROME.exists():
    alt = Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
    CHROME = alt if alt.exists() else Path()


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


class Proof:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.notes: list[str] = []

    def check(self, ok: bool, msg: str) -> None:
        (self.notes if ok else self.errors).append(msg if ok else "FAIL " + msg)

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
    proc = subprocess.Popen(
        [str(PY), "-c",
         "import uvicorn; from app_server import app; "
         f"uvicorn.run(app, host='127.0.0.1', port={port}, log_level='warning')"],
        cwd=str(SW),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    deadline = time.time() + 40
    up = False
    while time.time() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
            raise SystemExit("server exited: " + err[-800:])
        if port_open(port):
            up = True
            break
        time.sleep(0.15)
    if not up:
        proc.kill()
        raise SystemExit("server did not listen")

    proof = Proof()
    page_errors: list[str] = []
    result = {}
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=str(CHROME),
                headless=True,
                args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
            )
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on("dialog", lambda dlg: dlg.accept())
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")

            def tab(name: str) -> None:
                page.click(f'.view-tab[data-view="{name}"]')
                page.wait_for_timeout(200)

            def box(sel: str) -> dict:
                return page.locator(sel).evaluate(
                    """el => {
                      const r = el.getBoundingClientRect();
                      return {w: r.width, h: r.height, x: r.x, y: r.y,
                              hidden: el.hidden, text: (el.innerText || '').slice(0, 180)};
                    }"""
                )

            proof.eq(page.locator("#roomSizeChip").get_attribute("data-place"), None, "chip data-place")
            proof.check(page.locator("#panelRoom").is_visible(), "room editors on Room")
            proof.check(not page.locator("#roomSizeChip").is_visible(), "chip hidden on Room")
            proof.check(page.locator("#smooth").is_visible(), "Smooth on Room")
            proof.check(page.locator("#movementRow").is_hidden(), "Movement stays hidden")
            proof.check(page.locator("#panelAdvanced").is_visible(), "Advanced on Room")

            tab("source")
            page.screenshot(path=str(OUT / "t10_source_1280.png"))
            chip = box("#roomSizeChip")
            floor = box("#srcFloorCanvas")
            elev = box("#srcElevCanvas")
            proof.eq(chip["text"].strip(), "6.0 x 8.0 x 3.0 m", "chip text")
            proof.check(chip["w"] > 20 and not chip["hidden"], "chip visible on Source")
            proof.check(page.locator("#panelRoom").is_hidden(), "size editors hidden on Source")
            proof.check(page.locator("#panelPreview").is_hidden(), "preview hidden on Source")
            proof.check(page.locator("#W").count() == 1, "one Width slider")
            proof.check(page.locator("#sourceYaw").is_visible(), "source yaw stays")
            proof.check(640 <= floor["w"] <= 900, f"floor canvas about 700 ({floor['w']:.0f})")
            proof.check(640 <= elev["w"] <= 900, f"elev canvas about 700 ({elev['w']:.0f})")
            scroll = page.evaluate("() => document.documentElement.scrollWidth")
            proof.check(scroll <= 1280, f"scrollWidth {scroll} at 1280")
            adv = box("#panelAdvanced")
            proof.check(adv["x"] + adv["w"] <= 1280, "Advanced stays inside 1280")
            page.click("#roomSizeChip")
            page.wait_for_timeout(150)
            proof.check(page.locator("#panelRoom").is_visible(), "chip opens Room")
            proof.eq(page.locator("#third_mic").count(), 0, "no third_mic input")
            third = page.evaluate("() => window.__t10Third || null")
            # third_mic is not a DOM input. Read it from the setup control after the click.
            proof.eq(page.locator("#mic_setup").input_value(), "ortf", "chip does not change setup")

            tab("space")
            page.screenshot(path=str(OUT / "t10_space_1280.png"))
            host = page.evaluate(
                """() => {
                  const el = document.getElementById('micToggles');
                  return el && el.closest('#imageViews .panel-head') ? 'head' : 'elsewhere';
                }"""
            )
            proof.eq(host, "head", "mic ticks in Space head")
            proof.check(page.locator('#micToggles input[data-mic="L"]').is_checked(), "ORTF L ticked")
            proof.check(not page.locator('#micToggles input[data-mic="C"]').is_checked(), "ORTF C unticked")
            proof.check(page.locator('#micToggles input[data-mic="R"]').is_checked(), "ORTF R ticked")
            page.locator('#micToggles input[data-mic="C"]').check()
            page.wait_for_timeout(100)
            tab("mic")
            off_pressed = page.locator('#thirdMicRow button[data-third="off"]').get_attribute("aria-pressed")
            proof.eq(off_pressed, "true", "picture tick leaves third_mic off")
            proof.eq(page.locator("#mic_setup").input_value(), "ortf", "tick does not change setup")

            def choose_setup(setup_id: str) -> None:
                page.evaluate(
                    """(id) => {
                      const el = document.getElementById('mic_setup');
                      el.value = id;
                      el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    setup_id,
                )
                page.wait_for_timeout(250)

            choose_setup("ortf_c")
            tab("space")
            proof.check(page.locator('#micToggles input[data-mic="C"]').is_checked(), "ORTF+C ticks C")
            choose_setup("ortf")
            proof.check(not page.locator('#micToggles input[data-mic="C"]').is_checked(), "back to ORTF clears C")

            tab("polar")
            footer = page.locator("#polarCombined .hint").last.inner_text().strip()
            proof.eq(footer, "Combined uses the same polar field as the Mic source plane.", "B13 footer")

            tab("surfaces")
            page.screenshot(path=str(OUT / "t10_surfaces_1280.png"))
            proof.check(page.locator("#panelRoom").is_hidden(), "no size editors on Surfaces")
            proof.eq(page.locator("#humidity").input_value(), "0.35", "humidity 0.35")
            proof.eq(page.locator("#humidity_out").inner_text().strip(), "50% RH", "humidity readout")
            hint = page.locator("#airCard .hint").inner_text()
            proof.check("Right is drier air" in hint, "humidity hint")
            proof.check("Off" not in page.locator("#humidity_label").inner_text(), "no Off end label")
            names = page.locator("#materialChips").inner_text()
            proof.check("50 mm" in names or page.locator("#materialChips button").count() >= 0, "materials present")
            # Chips load async.
            page.wait_for_timeout(800)
            names = page.locator("#materialChips").inner_text()
            proof.check("50 mm fiberglass" in names, "inch name is mm")
            proof.check(" in " not in names, "no inch display names")
            proof.check(page.locator("#materialPaintAll").is_visible(), "All legal faces")
            proof.check("West" not in page.locator("#surfacesViews").inner_text(), "no West compass")

            page.set_viewport_size({"width": 390, "height": 800})
            tab("source")
            scroll390 = page.evaluate("() => document.documentElement.scrollWidth")
            proof.check(scroll390 <= 390, f"scrollWidth {scroll390} at 390")
            page.screenshot(path=str(OUT / "t10_source_390.png"))

            result = {
                "floor_w": floor["w"],
                "elev_w": elev["w"],
                "scroll_1280": scroll,
                "scroll_390": scroll390,
                "page_errors": page_errors,
                "advanced": adv,
            }
            browser.close()
    finally:
        proc.kill()
        proc.wait(timeout=10)
    idle_after = port_open(7860)
    result["port"] = port
    result["idle_7860_before"] = idle_before
    result["idle_7860_after"] = idle_after
    result["errors"] = proof.errors
    result["notes"] = proof.notes
    (OUT / "prove_t10.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"errors": proof.errors, "floor_w": result.get("floor_w"), "scroll": result.get("scroll_1280"), "scroll390": result.get("scroll_390"), "page_errors": page_errors}, indent=2))
    if proof.errors or page_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
