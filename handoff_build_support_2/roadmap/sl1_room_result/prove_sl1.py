"""SL1 page proof. Free port. 7860 is not touched.

Stage 1 Room result sits after .room-net-wrap. Surfaces is greyed.
Treatment and Auto-treat stay hidden. A material click posts /api/room_result
again. The 1280 px page does not grow sideways.
"""
from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
OUT = ROOT / "handoff_build_support_2" / "roadmap" / "sl1_room_result"
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
            bodies: list[dict] = []

            def on_response(resp) -> None:
                if "/api/room_result" not in resp.url or resp.status != 200:
                    return
                try:
                    bodies.append(resp.json())
                except Exception as exc:
                    bodies.append({"_error": str(exc)})

            page.on("response", on_response)
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.click('.view-tab[data-view="surfaces"]')
            page.wait_for_timeout(500)
            deadline = time.time() + 8
            while time.time() < deadline and not bodies:
                page.wait_for_timeout(100)

            shot = OUT / "sl1_surfaces_1280.png"
            page.screenshot(path=str(shot), full_page=True)

            info = page.evaluate(
                """() => {
                  const panel = document.getElementById('slRoomResult');
                  const net = document.querySelector('#surfacesPanel .room-net-wrap');
                  const surf = document.getElementById('slMode_surfaces');
                  const nat = document.getElementById('slMode_natural');
                  const flat = document.getElementById('slMode_flat');
                  const treat = document.getElementById('slTreatment');
                  const auto = document.getElementById('slAutoTreat');
                  function edge(el) {
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    const s = getComputedStyle(el);
                    return {x: r.x, y: r.y, w: r.width, h: r.height,
                            right: r.right, display: s.display, hidden: !!el.hidden};
                  }
                  const ids = ['materialPaintAll','surfacesSoloOff','jitterSlider',
                    'absorbCanvas','eqCanvas','slMode_flat','slTogBand','slTogEbu',
                    'roomNet','surfaceDetail'];
                  const boxes = {};
                  ids.forEach((id) => { boxes[id] = edge(document.getElementById(id)); });
                  let worst = 0;
                  document.querySelectorAll('#surfacesPanel button, #surfacesPanel input, #surfacesPanel output').forEach((el) => {
                    if (el.disabled || el.hidden) return;
                    const r = el.getBoundingClientRect();
                    if (r.width < 1) return;
                    worst = Math.max(worst, r.right);
                  });
                  return {
                    stage: window.RR_SL_STAGE,
                    hasPanel: !!panel,
                    afterNet: !!(panel && net && net.nextElementSibling === panel),
                    surfDisabled: surf ? surf.disabled : null,
                    surfTitle: surf ? surf.title : null,
                    natDisabled: nat ? nat.disabled : null,
                    flatPressed: flat ? flat.getAttribute('aria-pressed') : null,
                    treatHidden: treat ? treat.hidden : null,
                    autoHidden: auto ? auto.hidden : null,
                    readout: (document.getElementById('slReadout') || {}).textContent || '',
                    scroll: document.documentElement.scrollWidth,
                    client: document.documentElement.clientWidth,
                    worstRight: worst,
                    boxes: boxes,
                    material: (window.RRState && RRState.surfaces && RRState.surfaces.A)
                      ? RRState.surfaces.A.material : null
                  };
                }"""
            )
            check(info["stage"] == 1, f"stage {info['stage']}")
            check(info["hasPanel"] and info["afterNet"], "panel follows .room-net-wrap")
            check(info["surfDisabled"] is True and "coming" in (info["surfTitle"] or ""),
                  f"Surfaces chip greyed ({info['surfTitle']!r})")
            check(info["natDisabled"] is True, "Natural stays disabled")
            check(info["flatPressed"] == "true", "Flat is the pressed mode")
            check(info["treatHidden"] is True, "Treatment hidden")
            check(info["autoHidden"] is True, "Auto-treat hidden")
            check(info["scroll"] <= 1280, f"scrollWidth {info['scroll']} at 1280")
            check(info["worstRight"] <= info["client"] + 1,
                  f"controls inside the viewport (right {info['worstRight']:.1f}, client {info['client']})")
            check(bool(bodies), "room_result arrived")
            if bodies:
                check(bodies[-1].get("decay_mode") == "flat",
                      f"decay_mode {bodies[-1].get('decay_mode')!r}")
                check(bodies[-1].get("ok") is True, "room_result ok")

            before_n = len(bodies)
            before_abs = bodies[-1].get("T_absolute_mid") if bodies else None
            brick = page.locator('#materialChips button[data-material="brick_unglazed"]')
            check(brick.count() == 1, "one brick chip")
            if brick.count() == 1 and not brick.is_disabled():
                brick.click()
                deadline = time.time() + 8
                while time.time() < deadline and len(bodies) <= before_n:
                    page.wait_for_timeout(100)
                page.wait_for_timeout(200)
                after = bodies[-1] if len(bodies) > before_n else {}
                check(len(bodies) > before_n, f"material click posted room_result ({len(bodies) - before_n})")
                after_abs = after.get("T_absolute_mid")
                check(after_abs is not None and before_abs is not None and abs(after_abs - before_abs) > 0.05,
                      f"absolute mid {before_abs} -> {after_abs}")
                check(page.locator("#slReadout").inner_text().strip() != "", "readout still drawn")
            else:
                check(False, "brick chip was missing or disabled")

            page.screenshot(path=str(OUT / "sl1_surfaces_brick_1280.png"), full_page=True)
            result = {
                "port": port,
                "idle_7860_before": idle_before,
                "page_errors": page_errors,
                "info": info,
                "room_results": len(bodies),
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
    (OUT / "prove_sl1_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "errors": errors, "page_errors": page_errors, "notes": notes}, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
