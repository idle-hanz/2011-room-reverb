// Fan and Octagon are plan starters. Mirror flips a plan left to right.
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
const mix = readFileSync(join(here, "../static/js/rr_mix.js"), "utf8");

function inside(pts, W, L) {
  pts.forEach(function (p) {
    assert.ok(p[0] >= -1e-6 && p[0] <= W + 1e-6, p[0]);
    assert.ok(p[1] >= -1e-6 && p[1] <= L + 1e-6, p[1]);
  });
}

function starter(name, W, L) {
  const token = RS.storedShape(name, W, 3, L, "box");
  const pts = RS.planPoints(token);
  assert.equal(token === "box", false, name);
  assert.equal(RS.normalize(token), "plan", name + " " + W + "x" + L);
  assert.ok(pts && pts.length >= 5 && pts.length <= 8, name);
  inside(pts, W, L);
  assert.notEqual(token, RS.encodePlan([[0, 0], [W, 0], [W, L], [0, L]]));
  return pts;
}

test("Fan and Octagon are convex plans inside the box, and Box stays the word box", () => {
  [ [6, 8], [1, 2], [80, 120] ].forEach(function (size) {
    const fan = starter("fan", size[0], size[1]);
    const oct = starter("octagon", size[0], size[1]);
    assert.equal(fan.length, 6);
    assert.equal(oct.length, 8);
    const back = fan.filter(function (p) { return p[1] <= 0.02; });
    const front = fan.filter(function (p) { return Math.abs(p[1] - size[1]) <= 0.02; });
    const backW = Math.max.apply(null, back.map(function (p) { return p[0]; })) - Math.min.apply(null, back.map(function (p) { return p[0]; }));
    const frontW = Math.max.apply(null, front.map(function (p) { return p[0]; })) - Math.min.apply(null, front.map(function (p) { return p[0]; }));
    assert.ok(frontW < backW * 0.5, frontW + " vs " + backW);
    const cut = 0.29 * Math.min(size[0], size[1]);
    assert.ok(Math.abs(oct[0][0] - cut) <= 0.02, oct[0][0]);
    assert.ok(Math.abs(oct[0][1]) <= 0.02);
  });
  assert.equal(RS.storedShape("box", 6, 3, 8, "splay"), "box");
  assert.equal(RS.planNote(), "");
  assert.match(mix, /o\.room_shape = String\(state\.room_shape\)/);
  assert.equal((page.match(/data-room-shape="fan"/g) || []).length, 2);
  assert.equal((page.match(/data-room-shape="octagon"/g) || []).length, 2);
  assert.match(page, /id="roomPlanMirror"/);
  assert.match(room, /RoomShape\.mirrorPlan/);
});

test("mirror twice restores the plan, and a four-corner floor stays put", () => {
  const fan = RS.storedShape("fan", 6, 3, 8, "box");
  assert.equal(RS.mirrorPlan(RS.mirrorPlan(fan, 6, 8), 6, 8), fan);
  const oct = RS.storedShape("octagon", 6, 3, 8, "box");
  assert.equal(RS.mirrorPlan(RS.mirrorPlan(oct, 6, 8), 6, 8), oct);
  const lede = RS.storedShape("plan", 6, 3, 8, "lede");
  assert.equal(RS.mirrorPlan(RS.mirrorPlan("lede", 6, 8), 6, 8), lede);
  const hex = RS.storedShape("plan", 6, 3, 8, "hex");
  assert.equal(RS.mirrorPlan(RS.mirrorPlan("hex", 6, 8), 6, 8), hex);
  ["box", "splay", "live", "gable", "tilt:4.00:0.100"].forEach(function (cur) {
    assert.equal(RS.mirrorPlan(cur, 6, 8), cur);
    assert.equal(RS.planNote(), "Fewer than 5 corners");
  });
});
