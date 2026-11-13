import os
import sys
import time
from pathlib import Path

# The colour realtime gate times one second of audio. Other xdist workers
# push that over the limit, so they pause while it runs.
_CPU_GATE = Path(os.environ.get("TEMP", ".")) / "rr_colour_cpu_gate"
_CPU_BUSY = _CPU_GATE / "busy"
_CPU_HOLD = _CPU_GATE / "hold"

# Half the logical processors. -n auto on all 20 threads, plus the render
# pools and Chrome, makes each render late and the Playwright gates time out.
# PYTEST_XDIST_AUTO_NUM_WORKERS is read by pytest-xdist before it spawns.
_logical = os.cpu_count() or 8
os.environ.setdefault("PYTEST_XDIST_AUTO_NUM_WORKERS", str(max(4, _logical // 2)))


def pytest_addoption(parser):
    parser.addoption(
        "--no-render-cache",
        action="store_true",
        default=False,
        help="Re-render instead of reading software/.render_cache.",
    )


def _win_priority(cls: int) -> None:
    if os.name != "nt":
        return
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), cls)


def _keep_worker_stdin() -> None:
    """Playwright and the app server inherit this process.

    On Windows that inheritance closes the pipe pytest-xdist uses to send the
    next test, and the worker dies with 'not properly terminated'. The pipe
    stays open for xdist and is not handed to those children.
    """
    if os.name != "nt":
        return
    import ctypes
    import msvcrt
    try:
        handle = msvcrt.get_osfhandle(sys.stdin.fileno())
    except (OSError, ValueError):
        return
    ctypes.windll.kernel32.SetHandleInformation(handle, 1, 0)


def _cpu_gate_hold() -> bool:
    return _CPU_HOLD.exists()


def _enter_busy(item) -> None:
    """Register this test, unless the realtime gate is holding the machine."""
    deadline = time.time() + 180
    while time.time() < deadline:
        if _cpu_gate_hold():
            time.sleep(0.02)
            continue
        _CPU_BUSY.mkdir(parents=True, exist_ok=True)
        pidf = _CPU_BUSY / f"{os.getpid()}-{id(item)}"
        pidf.write_text(item.nodeid, encoding="utf-8")
        if _cpu_gate_hold():
            try:
                pidf.unlink()
            except OSError:
                pass
            time.sleep(0.02)
            continue
        item._rr_busy = pidf
        return
    item._rr_busy = None


def _leave_busy(item) -> None:
    pidf = getattr(item, "_rr_busy", None)
    if pidf is None:
        return
    try:
        pidf.unlink()
    except OSError:
        pass


def pytest_runtest_setup(item):
    if item.name != "test_colour_stays_finite_and_realtime":
        _enter_busy(item)
        return
    # Wait until the other workers are between tests, then time on a free core.
    _CPU_GATE.mkdir(parents=True, exist_ok=True)
    _CPU_HOLD.write_text("1", encoding="utf-8")
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            busy = [p for p in _CPU_BUSY.glob("*") if p.is_file()]
        except OSError:
            busy = []
        if not busy:
            break
        time.sleep(0.02)
    _win_priority(0x8000)  # ABOVE_NORMAL_PRIORITY_CLASS


def pytest_runtest_teardown(item):
    _leave_busy(item)
    if item.name == "test_colour_stays_finite_and_realtime":
        try:
            _CPU_HOLD.unlink()
        except OSError:
            pass
        _win_priority(0x20)  # NORMAL_PRIORITY_CLASS


def pytest_configure(config):
    # The slow suite shares the machine with Chrome. Below-normal keeps the
    # limiter LED inside its 20 s wait. The fast suite has a 1 s CPU gate, so
    # those workers stay at normal priority. The master clears a stale gate.
    if not getattr(config, "workerinput", None):
        import shutil
        shutil.rmtree(_CPU_GATE, ignore_errors=True)
    if getattr(config, "workerinput", None):
        _keep_worker_stdin()
        mark = str(getattr(config.option, "markexpr", "") or "")
        if "slow" in mark and "not slow" not in mark:
            _win_priority(0x4000)  # BELOW_NORMAL_PRIORITY_CLASS
    config.addinivalue_line(
        "markers",
        "slow: longer than about 5 s. Default pytest skips these. "
        "Before a push: pytest -n auto --dist loadscope -m slow",
    )
    no = bool(config.getoption("--no-render-cache"))
    if os.environ.get("RR_NO_RENDER_CACHE", "").lower() in ("1", "true", "yes"):
        no = True
    tests = str(Path(__file__).resolve().parent)
    if tests not in sys.path:
        sys.path.insert(0, tests)
    cur = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p and p != tests]
    os.environ["PYTHONPATH"] = os.pathsep.join([tests] + cur)
    os.environ["RR_TESTS_DIR"] = tests
    if no:
        os.environ["RR_NO_RENDER_CACHE"] = "1"
        os.environ.pop("RR_RENDER_CACHE", None)
    else:
        os.environ.pop("RR_NO_RENDER_CACHE", None)
        os.environ["RR_RENDER_CACHE"] = "1"
    from _render_cache import install
    install(not no)
