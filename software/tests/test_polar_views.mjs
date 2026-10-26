// node --test tests/test_polar_views.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const V = require("../static/js/polar_views.js");
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");
const desk = fs.readFileSync(path.join(here, "../static/js/mic_desk.js"), "utf8");
const field = fs.readFileSync(path.join(here, "../static/js/polar_field.js"), "utf8");

test("six switches live in one object", () => {
  assert.deepEqual(Object.keys(V.SWITCHES), [
    "slice", "angle", "readouts", "compare", "arrivals", "balloon"
  ]);
  assert.deepEqual(V.SWITCHES, {
    slice: true,
    angle: true,
    readouts: false,
    compare: false,
    arrivals: false,
    balloon: false,
  });
  assert.match(page, /id="polarExtras"/);
  assert.match(desk, /RRPolarViews.paintArrivals/);
  assert.match(field, /PolarFieldView.prototype.showBalloon/);
  assert.match(field, /_bindOrbit/);
});

test("a cardioid band reports front, side, and directivity", () => {
  const row = V.cardioidDbRow(72);
  assert.ok(Math.abs(V.frontBackDb(row) - 300) < 1e-6);
  assert.ok(Math.abs(V.level90Db(row) - (20 * Math.log10(0.5))) < 0.05);
  assert.ok(Math.abs(V.directivityIndexDb(row) - 4.771) < 0.05);
});

test("the angle axis is logarithmic from 20 Hz to 16 kHz", () => {
  assert.deepEqual(V.ANGLE_DEG, [0, 45, 90, 135, 180]);
  assert.equal(V.logX(20, 0, 100), 0);
  assert.ok(Math.abs(V.logX(16000, 0, 100) - 100) < 1e-9);
  const mid = Math.sqrt(20 * 16000);
  assert.ok(Math.abs(V.logX(mid, 0, 100) - 50) < 1e-6);
});

test("arrival marks follow the source", () => {
  const room = { W: 6, H: 3, L: 8 };
  const mic = { x: 3, y: 1.5, z: 6 };
  const look = { x: 0, z: 1 };
  const home = V.arrivalMarks(room, { x: 3, y: 1.5, z: 2 }, mic, look);
  assert.equal(home.length, 7);
  assert.equal(home[0].name, "Direct");
  assert.ok(Math.abs(home[0].azimuth - Math.PI) < 1e-9);
  const image = V.imagePoint({ x: 3, y: 1.5, z: 2 }, room, [1, 0, 0]);
  assert.deepEqual(image, { x: 9, y: 1.5, z: 2 });
  const moved = V.arrivalMarks(room, { x: 5, y: 1.5, z: 2 }, mic, look);
  assert.ok(Math.abs(moved[0].azimuth - home[0].azimuth) > 0.05);
  const names = home.map((row) => row.name);
  assert.ok(names.indexOf("Floor") >= 0 && names.indexOf("Ceiling") >= 0);
});
