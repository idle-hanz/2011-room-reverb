"""Disk cache for expensive test renders.

The key is a hash of the engine Python, live_stereo.c, the wasm, the worklet
JS, the settings or scene, and the calling test file. A change re-renders.
``pytest --no-render-cache`` or ``RR_NO_RENDER_CACHE=1`` skips the cache.
Files live under ``software/.render_cache`` (gitignored).
"""
from __future__ import annotations

import functools
import hashlib
import inspect
import os
import pickle
import struct
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "software" / ".render_cache"
_ENABLED = False
_FINGERPRINT = None
_MISS = object()
_NO_VALUES = ("1", "true", "yes")


def _no_cache() -> bool:
    return os.environ.get("RR_NO_RENDER_CACHE", "").lower() in _NO_VALUES


def enabled() -> bool:
    return bool(_ENABLED) and not _no_cache()


def _py_modules():
    sw = ROOT / "software"
    names = (
        "render_pipeline.py",
        "app_server.py",
        "image_geometry.py",
        "surface_colour.py",
        "solo_match.py",
        "polar_field.py",
        "mic_display.py",
        "settings_table.py",
    )
    for name in names:
        yield sw / name
    engine = sw / "engine"
    if engine.is_dir():
        for path in engine.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".py", ".c", ".h", ".inc", ".json"}:
                yield path
    for folder in (sw / "presets", sw / "mic_colour", ROOT / "mic_fitter" / "presets"):
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".py", ".json"}:
                yield path
    wasm = sw / "static" / "wasm" / "live_stereo.wasm"
    yield wasm
    js = sw / "static" / "js"
    for name in ("fdn_worklet.js", "live_fdn.js", "pack_room.js"):
        yield js / name
    harness = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"
    yield harness / "run_all.py"
    lib = harness / "lib"
    if lib.is_dir():
        for path in lib.iterdir():
            if path.is_file() and path.suffix.lower() in {".py", ".js"}:
                yield path
    tests = sw / "tests"
    for name in ("_sl_render.py", "_sl_harness.py", "_harness.py"):
        yield tests / name
    for path in tests.glob("fixture*.json"):
        yield path
    fix = tests / "fixtures"
    if fix.is_dir():
        for path in fix.glob("*.json"):
            yield path
    air = ROOT / "air_fitter" / "presets"
    if air.is_dir():
        for path in air.glob("*.json"):
            yield path


def fingerprint() -> bytes:
    """Hash of every file that can change a render, except the per-call scene and test."""
    global _FINGERPRINT
    if _FINGERPRINT is not None:
        return _FINGERPRINT
    digest = hashlib.sha256()
    seen = set()
    for path in sorted(set(_py_modules()), key=lambda p: p.as_posix().lower()):
        if not path.is_file():
            continue
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        rel = path.resolve().relative_to(ROOT).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    _FINGERPRINT = digest.digest()
    return _FINGERPRINT


def _feed(digest, obj) -> None:
    if obj is None:
        digest.update(b"n")
        return
    if isinstance(obj, bool):
        digest.update(b"b1" if obj else b"b0")
        return
    if isinstance(obj, (np.integer, int)):
        digest.update(b"i")
        digest.update(str(int(obj)).encode("utf-8"))
        return
    if isinstance(obj, (np.floating, float)):
        digest.update(b"f")
        digest.update(struct.pack("<d", float(obj)))
        return
    if isinstance(obj, str):
        digest.update(b"s")
        digest.update(obj.encode("utf-8"))
        return
    if isinstance(obj, (bytes, bytearray, memoryview)):
        raw = bytes(obj)
        digest.update(b"y")
        digest.update(str(len(raw)).encode("utf-8"))
        digest.update(raw)
        return
    if isinstance(obj, Path):
        digest.update(b"p")
        if obj.is_file():
            digest.update(obj.read_bytes())
        else:
            digest.update(str(obj).encode("utf-8"))
        return
    if isinstance(obj, np.ndarray):
        arr = np.ascontiguousarray(obj)
        digest.update(b"a")
        digest.update(str(arr.dtype).encode("utf-8"))
        digest.update(str(arr.shape).encode("utf-8"))
        digest.update(arr.tobytes())
        return
    if isinstance(obj, dict):
        digest.update(b"d")
        for key in sorted(obj.keys(), key=repr):
            _feed(digest, key)
            _feed(digest, obj[key])
        return
    if isinstance(obj, (list, tuple)):
        digest.update(b"l" if isinstance(obj, list) else b"t")
        digest.update(str(len(obj)).encode("utf-8"))
        for item in obj:
            _feed(digest, item)
        return
    if isinstance(obj, set):
        digest.update(b"e")
        for item in sorted(obj, key=repr):
            _feed(digest, item)
        return
    if callable(obj) and not isinstance(obj, type):
        digest.update(b"c")
        _callable_bytes(digest, obj)
        return
    digest.update(b"r")
    digest.update(repr(obj).encode("utf-8", "replace"))


def _callable_bytes(digest, fn, seen=None) -> None:
    """Bytecode, not the function id, so a monkeypatch changes the key."""
    if seen is None:
        seen = set()
    marker = id(fn)
    if marker in seen:
        return
    seen.add(marker)
    code = getattr(fn, "__code__", None)
    if code is None:
        digest.update(repr(fn).encode("utf-8", "replace"))
        return
    digest.update(code.co_code)
    digest.update(b"\0")
    digest.update(code.co_name.encode("utf-8", "replace"))
    closure = getattr(fn, "__closure__", None) or ()
    for cell in closure:
        try:
            contents = cell.cell_contents
        except ValueError:
            digest.update(b"?")
            continue
        if getattr(contents, "__code__", None) is not None:
            _callable_bytes(digest, contents, seen)
        else:
            _feed(digest, contents)


def live_stamp() -> bytes:
    """In-process hooks render() reads that are not in the kwargs.

    Tests replace ``_scale_inject_reflect`` and still expect a new render.
    File bytes do not move when that happens, so the key includes the live
    function bytecode on the render module.
    """
    import types
    import render_pipeline

    digest = hashlib.sha256()
    digest.update(b"live")
    for name in sorted(vars(render_pipeline)):
        if name.startswith("__"):
            continue
        try:
            val = getattr(render_pipeline, name)
        except Exception:
            continue
        if isinstance(val, types.ModuleType) or isinstance(val, type):
            continue
        digest.update(name.encode("utf-8"))
        if callable(val):
            _callable_bytes(digest, val)
        elif isinstance(val, (bool, int, float, str, bytes, type(None), tuple)):
            _feed(digest, val)
    ctx = getattr(render_pipeline, "_SURF_CTX", None)
    if ctx is not None:
        try:
            _feed(digest, ctx.get())
        except Exception:
            digest.update(b"ctx")
    return digest.digest()


def calling_test_file():
    for frame in inspect.stack():
        path = Path(frame.filename).resolve()
        if path.name.startswith("test_") and path.suffix == ".py":
            return path
    # A thread started at play_ir has no test frame. Pytest records the file
    # on the process, and threads see that environment.
    raw = os.environ.get("PYTEST_CURRENT_TEST", "")
    head = raw.split(" (", 1)[0].split("::", 1)[0].strip()
    if head.endswith(".py"):
        path = Path(head)
        if not path.is_file():
            path = ROOT / "software" / head
        if path.is_file():
            return path.resolve()
    return None


def _key(kind: str, scene, test_file) -> str:
    digest = hashlib.sha256()
    digest.update(fingerprint())
    digest.update(live_stamp())
    digest.update(kind.encode("utf-8"))
    _feed(digest, scene)
    path = Path(test_file) if test_file else calling_test_file()
    digest.update(b"tf")
    if path is not None and Path(path).is_file():
        file_path = Path(path).resolve()
        digest.update(file_path.as_posix().encode("utf-8"))
        digest.update(file_path.read_bytes())
    else:
        digest.update(b"-")
    return digest.hexdigest()


def _log(text: str) -> None:
    line = "RR_RENDER_CACHE " + text + "\n"
    try:
        sys.stderr.write(line)
    except Exception:
        pass
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        with (CACHE / "events.log").open("a", encoding="utf-8") as handle:
            handle.write(line)
    except Exception:
        pass


def _load(path: Path):
    if not path.is_file():
        return _MISS
    try:
        return pickle.loads(path.read_bytes())
    except Exception as exc:
        _log("bad " + path.name[:12] + " " + exc.__class__.__name__)
        return _MISS


def _store(path: Path, value):
    blob = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    tmp.write_bytes(blob)
    os.replace(tmp, path)


def _acquire(lock: Path):
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            if time.time() - lock.stat().st_mtime > 1200:
                lock.unlink()
                fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            else:
                return None
        except OSError:
            return None
    os.close(fd)
    return True


def _release(lock: Path) -> None:
    try:
        lock.unlink()
    except OSError:
        pass


def _wait(path: Path, lock: Path, timeout: float = 1200) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.is_file():
            return True
        if not lock.exists():
            return False
        try:
            # A killed worker leaves the lock. Waiters must drop it or they sit out the timeout.
            if time.time() - lock.stat().st_mtime > 1200:
                lock.unlink()
                return False
        except OSError:
            return False
        time.sleep(0.25)
    return path.is_file()


def cached_call(kind: str, scene, compute, test_file=None):
    """Return compute(), or the stored result when the key matches."""
    if not enabled():
        return compute()
    try:
        key = _key(kind, scene, test_file)
    except Exception as exc:
        _log("keyfail " + kind + " " + exc.__class__.__name__)
        return compute()
    path = CACHE / key[:2] / key
    hit = _load(path)
    if hit is not _MISS:
        _log("hit " + kind + " " + key[:12])
        return hit
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(key + ".lock")
    owned = _acquire(lock)
    if not owned:
        if _wait(path, lock):
            hit = _load(path)
            if hit is not _MISS:
                _log("hit " + kind + " " + key[:12])
                return hit
        owned = _acquire(lock)
    try:
        hit = _load(path)
        if hit is not _MISS:
            _log("hit " + kind + " " + key[:12])
            return hit
        _log("miss " + kind + " " + key[:12])
        value = compute()
        try:
            _store(path, value)
        except Exception as exc:
            _log("uncacheable " + kind + " " + exc.__class__.__name__)
        return value
    finally:
        if owned:
            _release(lock)


def _rebind(orig, wrapped) -> None:
    for mod in list(sys.modules.values()):
        if mod is None:
            continue
        try:
            names = list(vars(mod).items())
        except Exception:
            continue
        for name, val in names:
            if val is orig:
                try:
                    setattr(mod, name, wrapped)
                except Exception:
                    pass


def _patch_render() -> None:
    import render_pipeline

    current = render_pipeline.render
    if getattr(current, "_rr_cache", False):
        return
    orig = current

    def wrapped(*args, **kwargs):
        if not enabled():
            return orig(*args, **kwargs)
        scene = (args, kwargs)
        return cached_call("render", scene, lambda: orig(*args, **kwargs))

    functools.wraps(orig)(wrapped)
    wrapped._rr_cache = True
    render_pipeline.render = wrapped
    _rebind(orig, wrapped)


def install(enabled_flag: bool = True) -> None:
    """Turn the cache on or off and wrap in-process render()."""
    global _ENABLED
    _ENABLED = bool(enabled_flag) and not _no_cache()
    if _ENABLED:
        os.environ["RR_RENDER_CACHE"] = "1"
        os.environ.pop("RR_NO_RENDER_CACHE", None)
    else:
        os.environ["RR_NO_RENDER_CACHE"] = "1"
        os.environ.pop("RR_RENDER_CACHE", None)
    _patch_render()


def install_from_env() -> None:
    """Child processes inherit RR_RENDER_CACHE from the pytest worker."""
    if _no_cache():
        install(False)
    elif os.environ.get("RR_RENDER_CACHE") == "1":
        install(True)


def pool_ping() -> str:
    return "ok"
