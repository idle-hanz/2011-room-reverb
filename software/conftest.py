"""Loaded with the software rootdir, before pytest-xdist picks a worker count."""
import os

# Python 3.14's new Windows stdio raises OSError 22 on the pipe xdist uses
# to send the next test. Workers inherit this and start on the legacy stdio.
os.environ.setdefault("PYTHONLEGACYWINDOWSSTDIO", "1")

import pytest


def half_workers() -> int:
    """Leave a core free for a render pool and for Chrome."""
    logical = os.cpu_count() or 8
    return max(4, logical // 2)


os.environ.setdefault("PYTEST_XDIST_AUTO_NUM_WORKERS", str(half_workers()))


@pytest.hookimpl(tryfirst=True)
def pytest_xdist_auto_num_workers(config):
    return half_workers()
