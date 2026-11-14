// Typed wall angle and ceiling percent apply only from the Apply button.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const RS = require("../static/js/room_shape.js");
const page = readFileSync(join(here, "../static/index.html"), "utf8");
const room = readFileSync(join(here, "../static/js/rr_room.js"), "utf8");
const app = readFileSync(join(here, "../static/js/app.js"), "utf8");

test("typed degrees and percent clamp before they are stored", () => {
  assert.equal(RS.encodeTiltFields(6, 0), "tilt:6.00:0.000");
  assert.equal(RS.encodeTiltFields(25, 0), "tilt:20.00:0.000");
  assert.equal(RS.encodeTiltFields(-25, 0), "tilt:-20.00:0.000");
  assert.equal(RS.encodeTiltFields(0, 10), "tilt:0.00:0.100");
  assert.equal(RS.encodeTiltFields(0, 45), "tilt:0.00:0.450");
  assert.equal(RS.encodeTiltFields(0, 50), "tilt:0.00:0.450");
  assert.equal(RS.encodeTiltFields(0, -50), "tilt:0.00:-0.450");
  assert.equal(RS.encodeTiltFields(0, 0), "box");
  assert.equal(RS.encodeTilt(0, 0), "box");
});

test("Apply writes the shape and typing does not", () => {
  assert.match(page, /id="roomTiltDeg"/);
  assert.match(page, /id="roomSlopePct"/);
  assert.match(page, /id="roomTiltApply"/);
  assert.match(room, /encodeTiltFields/);
  assert.match(room, /getElementById\("roomTiltApply"\)/);
  assert.match(room, /state\.room_shape = RoomShape\.encodeTiltFields/);
  assert.match(room, /activeElement !== degEl/);
  assert.equal(room.includes('addEventListener("input"'), false);
  assert.equal(room.includes("addEventListener('input'"), false);
  assert.match(app, /RoomShape\.cycleTilt/);
  assert.equal(app.includes("roomTiltDeg"), false);
  assert.equal(app.includes("roomSlopePct"), false);
  assert.equal(app.includes("roomTiltApply"), false);
});
