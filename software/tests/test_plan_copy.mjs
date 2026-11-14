// Plan copies a 5-8 corner outline. A shoebox, a tilt, or a dent stays on its preset.
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

function nearOutline(token, preset) {
  const got = RS.planPoints(token);
  const want = RS.floorOutline(preset, 6, 8);
  assert.equal(got.length, want.length, preset);
  for (let i = 0; i < want.length; i++) {
    assert.ok(Math.abs(got[i][0] - want[i][0]) <= 0.01, preset + " x " + got[i][0]);
    assert.ok(Math.abs(got[i][1] - want[i][1]) <= 0.01, preset + " z " + got[i][1]);
  }
}

test("Plan copies LEDE and Hex and leaves the preset word until the click", () => {
  assert.equal(RS.storedShape("lede", 6, 3, 8, "box"), "lede");
  assert.equal(RS.storedShape("hex", 6, 3, 8, "box"), "hex");
  assert.equal(RS.planNote(), "");
  const lede = RS.storedShape("plan", 6, 3, 8, "lede");
  assert.equal(RS.normalize(lede), "plan");
  nearOutline(lede, "lede");
  assert.equal(RS.planNote(), "");
  const hex = RS.storedShape("plan", 6, 3, 8, "hex");
  assert.equal(RS.normalize(hex), "plan");
  nearOutline(hex, "hex");
  assert.equal(RS.storedShape("plan", 6, 3, 8, hex), hex);
});

test("Box, Splay, Live, Gable and a tilt floor stay put", () => {
  ["box", "splay", "live", "gable", "tilt:4:0.1"].forEach(function (cur) {
    assert.equal(RS.storedShape("plan", 6, 3, 8, cur), cur);
    assert.equal(RS.planNote(), "Fewer than 5 corners");
  });
  assert.equal(RS.storedShape("splay", 6, 3, 8, "box"), "splay");
  assert.equal(RS.planNote(), "");
});

test("more than eight corners or a dent is refused", () => {
  const nine = [];
  for (let i = 0; i < 9; i++) {
    const a = -Math.PI / 2 + i * 2 * Math.PI / 9;
    nine.push([3 + 2 * Math.cos(a), 4 + 2.5 * Math.sin(a)]);
  }
  assert.equal(RS.planFromOutline(nine, "lede"), "lede");
  assert.equal(RS.planNote(), "More than 8 corners");
  const dent = [[0, 0], [6, 0], [6, 8], [3, 4], [0, 8]];
  assert.equal(RS.planFromOutline(dent, "hex"), "hex");
  assert.equal(RS.planNote(), "Outline is not convex");
});

test("the shape panel says why a Plan click was refused", () => {
  assert.match(page, /id="roomPlanNote"/);
  assert.match(room, /roomPlanNote/);
  assert.match(room, /RoomShape\.planNote/);
});
