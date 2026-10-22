"""SL2 page proof. Free port. 7860 is not touched.

Stage 2 enables the Surfaces chip. The click posts /api/room_result only.
Play stays labelled Render only. Treatment and Auto-treat stay hidden.
"""
from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
OUT = ROOT / "handoff_build_support_2" / "roadmap" / "sl2_loop"
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

    errors: list[str] = []
    notes: list[str] = []

    def check(ok: bool, msg: str) -> None:
        (notes if ok else errors).append(msg if ok else "FAIL " + msg)

    page_errors: list[str] = []
    result: dict = {}
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
            posts: list[str] = []
            bodies: list[dict] = []

            def on_request(req) -> None:
                if req.method == "POST":
                    posts.append(req.url)

            def on_response(resp) -> None:
                if "/api/room_result" not in resp.url or resp.status != 200:
                    return
                try:
                    bodies.append(resp.json())
                except Exception as exc:
                    bodies.append({"_error": str(exc)})

            page.on("request", on_request)
            page.on("response", on_response)
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.click('.view-tab[data-view="surfaces"]')
            page.wait_for_timeout(600)

            def snap(width: int) -> dict:
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(200)
                return page.evaluate(
                    """() => {
                      const surf = document.getElementById('slMode_surfaces');
                      const nat = document.getElementById('slMode_natural');
                      const flat = document.getElementById('slMode_flat');
                      const hint = document.querySelector('#slDecayMode .hint');
                      const treat = document.getElementById('slTreatment');
                      const auto = document.getElementById('slAutoTreat');
                      return {
                        stage: window.RR_SL_STAGE,
                        surfDisabled: surf ? surf.disabled : null,
                        surfTitle: surf ? surf.title : '',
                        natDisabled: nat ? nat.disabled : null,
                        flatPressed: flat ? flat.getAttribute('aria-pressed') : null,
                        hint: hint ? hint.textContent : '',
                        treatHidden: treat ? treat.hidden : null,
                        autoHidden: auto ? auto.hidden : null,
                        scroll: document.documentElement.scrollWidth
                      };
                    }"""
                )

            info = snap(1280)
            page.screenshot(path=str(OUT / "sl2_surfaces_1280.png"), full_page=True)
            phone = snap(390)
            page.screenshot(path=str(OUT / "sl2_surfaces_390.png"), full_page=True)
            page.set_viewport_size({"width": 1280, "height": 900})

            check(info["stage"] == 2, f"stage {info['stage']}")
            check(info["surfDisabled"] is False, "Surfaces chip is live")
            check("coming" not in (info["surfTitle"] or ""), f"title {info['surfTitle']!r}")
            check("Render only" in (info["hint"] or ""), f"hint {info['hint']!r}")
            check(info["natDisabled"] is True, "Natural stays disabled")
            check(info["flatPressed"] == "true", "Flat is pressed at boot")
            check(info["treatHidden"] is True, "Treatment hidden")
            check(info["autoHidden"] is True, "Auto-treat hidden")
            check(info["scroll"] == 1280, f"scrollWidth {info['scroll']} at 1280")
            check(phone["scroll"] == 390, f"scrollWidth {phone['scroll']} at 390")

            before = len(bodies)
            live_before = sum(1 for u in posts if "/api/live_params" in u)
            page.click("#slMode_surfaces")
            deadline = time.time() + 8
            while time.time() < deadline and len(bodies) <= before:
                page.wait_for_timeout(100)
            page.wait_for_timeout(300)
            live_after = sum(1 for u in posts if "/api/live_params" in u)
            mode = bodies[-1].get("decay_mode") if len(bodies) > before else None
            check(len(bodies) > before, "Surfaces click posted /api/room_result")
            check(mode == "surfaces", f"decay_mode {mode!r}")
            check(live_after == live_before, f"live_params posts {live_before} -> {live_after}")
            pressed = page.locator("#slMode_surfaces").get_attribute("aria-pressed")
            check(pressed == "true", f"Surfaces pressed {pressed!r}")

            result = {
                "port": port,
                "idle_7860_before": idle_before,
                "page_errors": page_errors,
                "info": info,
                "phone": phone,
                "notes": notes,
                "errors": errors,
            }
            browser.close()
    finally:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except Exception:
            pass

    result["idle_7860_after"] = port_open(7860)
    result["ok"] = not errors and not page_errors
    (OUT / "prove_sl2_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "errors": errors, "page_errors": page_errors, "notes": notes}, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
