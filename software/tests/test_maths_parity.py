"""Each maths topic: the Python module and the page script return the same numbers."""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from maths_bands import exact_third_centres  # noqa: E402
from maths_db import db_to_lin, lin_to_db  # noqa: E402
from maths_distance import geometric_level  # noqa: E402
from maths_image import image_position_corner  # noqa: E402
from maths_look import look_vector  # noqa: E402
from maths_pattern import first_order_gain, polar_a_from_slider  # noqa: E402

JS_DIR = ROOT / "static" / "js"
SRC = (2.6, 1.2, 4.75)
ROOM = (6.0, 3.0, 8.0)
NS = ((0, 0, 0), (-1, 0, 0), (1, 0, 0), (2, 0, 0), (-2, 0, 0), (0, 0, 2))
YAWS = (0.0, 55.0 * math.pi / 180.0, -math.pi / 2.0, math.pi / 2.0)
DISTS = (0.0, 1e-12, 0.3, 1.0, 2.5, 7.0, 40.0)
DBS = (0.0, -6.0, -60.0, 12.0)
LINS = (1.0, 0.5)
THETAS = (0.0, math.pi / 2.0, math.pi)
AS = (0.5, 0.37, 0.25)

_NODE = r"""
const fs = require("fs");
const vm = require("vm");
const path = require("path");
const dir = process.argv[1];
const sandbox = {};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.Math = Math;
sandbox.console = console;
vm.createContext(sandbox);
for (const name of ["maths_look.js", "maths_pattern.js", "maths_distance.js", "maths_db.js", "maths_bands.js", "maths_image.js"]) {
  vm.runInContext(fs.readFileSync(path.join(dir, name), "utf8"), sandbox, { filename: name });
}
const L = sandbox.RRLook;
const P = sandbox.RRPattern;
const D = sandbox.RRDistance;
const B = sandbox.RRDb;
const N = sandbox.RRBands;
const I = sandbox.RRImage;
const yaw = [0, 55 * Math.PI / 180, -Math.PI / 2, Math.PI / 2];
const look = yaw.map((y) => {
  const v = L.lookVector(y);
  return [v.x, v.y, v.z];
});
const polars = [0, 0.5, 1].map((p) => P.polarA("cardioid", p, null));
const hyper = P.polarA("cardioid", 1, "hypercardioid");
const bi = P.polarA("bi", 0.5, "cardioid");
const gains = [];
for (const a of [0.5, 0.37, 0.25]) {
  for (const th of [0, Math.PI / 2, Math.PI]) gains.push(P.firstOrderGain(th, a));
}
const dists = [0, 1e-12, 0.3, 1, 2.5, 7, 40].map((d) => D.geometricLevel(d));
const dbs = [0, -6, -60, 12].map((db) => B.dbToLin(db));
const lins = [1, 0.5].map((v) => B.linToDb(v));
const bands = N.exactThirdCentres(-10, 11);
const src = { x: 2.6, y: 1.2, z: 4.75 };
const room = { W: 6, H: 3, L: 8 };
const ns = [[0, 0, 0], [-1, 0, 0], [1, 0, 0], [2, 0, 0], [-2, 0, 0], [0, 0, 2]];
const images = ns.map((n) => {
  const p = I.imagePoint(src, room, n, false);
  return [p.x, p.y, p.z];
});
const face = I.imagePoint(src, room, [0, 0, 2], true);
console.log(JSON.stringify({
  look, polars, hyper, bi, gains, dists, dbs, lins, bands, images,
  face: [face.x, face.y, face.z]
}));
"""


def _js():
    run = subprocess.run(
        ["node", "-e", _NODE, str(JS_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr[-500:]
    return json.loads(run.stdout)


def _close(a, b, tol=1e-9):
    assert abs(float(a) - float(b)) <= tol, (a, b)


def test_look_matches():
    js = _js()["look"]
    assert look_vector(0.0) == (0.0, 0.0, 1.0)
    for got, yaw in zip(js, YAWS):
        want = look_vector(yaw)
        for a, b in zip(got, want):
            _close(a, b, 1e-12)


def test_pattern_matches():
    js = _js()
    for got, polar in zip(js["polars"], (0.0, 0.5, 1.0)):
        _close(got, polar_a_from_slider(polar), 1e-12)
    _close(js["hyper"], polar_a_from_slider(1.0, "hypercardioid"), 1e-12)
    _close(js["hyper"], 0.25, 1e-12)
    _close(polar_a_from_slider(1.0), 0.37, 1e-12)
    # Family "bi" is the desk short-circuit. The Python slider has no family.
    assert js["bi"] == 0
    i = 0
    for a in AS:
        for theta in THETAS:
            _close(js["gains"][i], first_order_gain(theta, a), 1e-12)
            i += 1
    _close(first_order_gain(0.4, 0.5), 0.5 * (1.0 + math.cos(0.4)), 1e-12)


def test_distance_matches():
    js = _js()["dists"]
    for got, dist in zip(js, DISTS):
        _close(got, geometric_level(dist), 1e-12)
    assert geometric_level(2.0) == 0.5


def test_db_matches():
    js = _js()
    for got, db in zip(js["dbs"], DBS):
        _close(got, db_to_lin(db), 1e-12)
    for got, lin in zip(js["lins"], LINS):
        _close(got, lin_to_db(lin), 1e-9)


def test_bands_match():
    js = np.asarray(_js()["bands"], dtype=np.float64)
    py = np.asarray(exact_third_centres(-10, 11), dtype=np.float64)
    old = 1000.0 * 2.0 ** (np.arange(-10, 11) / 3.0)
    assert np.array_equal(py, old)
    assert np.array_equal(exact_third_centres(-14, 10), 1000.0 * 2.0 ** (np.arange(-14, 10) / 3.0))
    assert np.array_equal(exact_third_centres(-14, 11), 1000.0 * 2.0 ** (np.arange(-14, 11) / 3.0))
    assert np.allclose(js, py, rtol=0.0, atol=1e-6)


def test_image_matches():
    js = _js()
    for got, n in zip(js["images"], NS):
        want = image_position_corner(SRC, ROOM, n, z_face_4l=False)
        for a, b in zip(got, want):
            _close(a, b, 1e-9)
    face = image_position_corner(SRC, ROOM, (0, 0, 2), z_face_4l=True)
    for a, b in zip(js["face"], face):
        _close(a, b, 1e-9)
