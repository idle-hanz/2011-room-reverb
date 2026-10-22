"""Phase acceptance tests (P0-P6 + product locks + SOS colour) for 2011 Room Reverb.

Run (box, or any machine with node + a Python that can import software/app_server.py):
    python -m pytest tests -q --sw /path/to/software [--slow] [--perf-scale 1.5]
or  python run_phase_tests.py --sw /path/to/software [--slow]     (run_all.py-style table + JSON)

Read-only on --sw: everything is imported/executed from the tree, outputs go to a temp dir.
mic_fitter/ must sit next to software/ (the colour code loads it), as for run_all.py.

Status meaning (same spirit as run_all.py):
  PASS    criterion met
  FAIL    criterion not met for a feature that IS in the tree (a real bug/regression)
  XFAIL   feature not in the tree yet (probe says so) -> reason names the probe and the phase
  SKIP    tool missing (node, zig) or --slow not given
"""
from __future__ import annotations
import argparse, importlib, os, re, sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent / 'harness'
sys.path[:0] = [str(HARNESS), str(HARNESS / 'lib'), str(HERE)]


def pytest_addoption(parser):
    g = parser.getgroup('room reverb')
    g.addoption('--sw', default=os.environ.get('RR_SW'), help='software/ tree to test (read-only)')
    g.addoption('--app-python', default=os.environ.get('RR_PY', sys.executable),
                help='python for subprocess helpers (dump_params/render_ir); default: this one')
    g.addoption('--node', default='node')
    g.addoption('--slow', action='store_true', help='also run the Render-heavy tests (~1-3 min each)')
    g.addoption('--perf-scale', type=float, default=1.0, help='multiply CPU limits (slow machine > 1)')


def pytest_configure(config):
    config.addinivalue_line('markers', 'slow: Render-heavy; needs --slow')
    config.addinivalue_line('markers', 'phase(p): roadmap phase id (P0.1 ... P6, LOCK, COLOUR)')


def pytest_collection_modifyitems(config, items):
    if config.getoption('--slow'):
        return
    skip = pytest.mark.skip(reason='slow Render test: pass --slow')
    for it in items:
        if 'slow' in it.keywords:
            it.add_marker(skip)


@pytest.fixture(scope='session')
def sw(pytestconfig) -> Path:
    p = pytestconfig.getoption('--sw')
    if not p:
        pytest.exit('pass --sw <software dir> (or set RR_SW)', 2)
    p = Path(p).resolve()
    if not (p / 'app_server.py').exists():
        pytest.exit(f'{p} is not a software/ tree (no app_server.py)', 2)
    return p


@pytest.fixture(scope='session')
def src(sw):
    """src('engine/live_stereo.c') -> file text ('' if missing)."""
    cache = {}
    def read(rel):
        if rel not in cache:
            f = sw / rel
            cache[rel] = f.read_text(encoding='utf-8', errors='replace') if f.exists() else ''
        return cache[rel]
    return read


@pytest.fixture(scope='session')
def app(sw):
    """app_server imported in-process from the tree (cwd switched for its relative loads)."""
    sys.path[:0] = [str(sw), str(sw / 'engine')]
    old = os.getcwd()
    os.chdir(sw)
    try:
        mod = importlib.import_module('app_server')
    except Exception as e:  # pragma: no cover
        pytest.skip(f'cannot import app_server from {sw}: {e!r}')
    finally:
        os.chdir(old)
    return mod


@pytest.fixture(scope='session')
def ctx(sw, pytestconfig, tmp_path_factory):
    """run_all.Ctx on the same tree: ctx.params / ctx.play / ctx.play_ir / ctx.render_ir."""
    import run_all as RA
    ns = argparse.Namespace(sw=str(sw), python=pytestconfig.getoption('--app-python'),
                            node=pytestconfig.getoption('--node'), golden=str(HARNESS / 'golden'),
                            regen_golden=False, quick=not pytestconfig.getoption('--slow'),
                            perf_scale=pytestconfig.getoption('--perf-scale'),
                            workdir=str(tmp_path_factory.mktemp('rr')))
    c = RA.Ctx(ns)
    if not c.node:
        c._no_node = True
    return c


@pytest.fixture(scope='session')
def RA():
    import run_all
    return run_all


def call_harness(RA, fn, ctx):
    """Run a run_all.py test function and map its exceptions to pytest outcomes."""
    try:
        return fn(ctx)
    except RA.SkipTest as e:
        pytest.skip(str(e))
    except RA.Pending as e:
        pytest.xfail(f'PENDING in run_all: {e}')
    except RA.XFail as e:
        pytest.xfail(str(e))
