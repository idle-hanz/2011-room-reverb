// Shoebox ratios, axial chart, tilt, plan, and panel rows. Display plus the room_shape token.
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
const editor = readFileSync(join(here, "../static/js/room_editor.js"), "utf8");
const sl = readFileSync(join(here, "../static/js/sl_room_result.js"), "utf8");
const RD = require("../static/js/room_draw.js");

test("ratios are not the 6 by 3 by 8 default and modes use 340", () => {
  const bolt = RS.ratioSize("bolt", 6, 3, 8);
  const sep = RS.ratioSize("sepmeyer", 6, 3, 8);
  const lou = RS.ratioSize("louden", 6, 3, 8);
  [bolt, sep, lou].forEach(function (row) {
    assert.ok(Math.abs(row.W - 6) > 0.05 || Math.abs(row.H - 3) > 0.05 || Math.abs(row.L - 8) > 0.05);
  });
  const modes = RS.axialModes(6, 3, 8, 340);
  assert.equal(modes.c, 340);
  assert.ok(Math.abs(modes.W[0] - 340 / 12) < 1e-9);
  assert.ok(Math.abs(modes.H[0] - 340 / 6) < 1e-9);
  assert.ok(Math.abs(modes.L[0] - 340 / 16) < 1e-9);
  assert.match(RS.axialText(6, 3, 8), /340 m\/s/);
  assert.match(page, /id="roomModes"/);
  assert.match(page, /data-ratio="bolt"/);
});

test("tilt zero and a flat ceiling stay the box word", () => {
  assert.equal(RS.normalize("tilt:0:0"), "box");
  assert.equal(RS.encodeTilt(0, 0), "box");
  assert.equal(RS.normalize("nope"), "box");
  assert.equal(RS.normalize("plan"), "box");
  assert.equal(RS.cycleTilt("box"), "tilt:4.00:0.000");
  assert.equal(RS.normalize(RS.cycleTilt("box")), "tilt");
  assert.equal(RS.cycleSlope("box"), "tilt:0.00:0.100");
  assert.equal(RS.cycleTilt("tilt:12.00:0.000"), "box");
  assert.deepEqual(RS.floorOutline("box", 6, 8), [[0, 0], [6, 0], [6, 8], [0, 8]]);
  assert.equal(RS.ceilingAt("box", 2, 3, 8), 3);
  const sloped = RS.ceilingAt("tilt:0:0.2", 0, 3, 8);
  assert.ok(sloped < 3);
  assert.match(app, /RoomShape\.cycleTilt/);
  assert.equal(room.indexOf("state.wall_tilt"), -1);
  assert.equal(room.indexOf("state.plan_xy"), -1);
});

test("a plan is five to eight corners and panels use the treatment rows", () => {
  const token = RS.encodePlan(RS.regularPlan(6, 6, 8));
  assert.equal(RS.normalize(token), "plan");
  assert.equal(RS.planPoints(token).length, 6);
  const five = RS.encodePlan(RS.regularPlan(5, 6, 8));
  const eight = RS.encodePlan(RS.regularPlan(8, 6, 8));
  assert.equal(RS.planPoints(five).length, 5);
  assert.equal(RS.planPoints(eight).length, 8);
  assert.equal(RS.planPoints(RS.delPlanCorner(five)).length, 5);
  assert.equal(RS.planPoints(RS.addPlanCorner(eight)).length, 8);
  const grown = RS.addPlanCorner(five);
  assert.equal(RS.planPoints(grown).length, 6);
  const moved = RS.movePlanPoint(token, 0, 0.2, 0.2, 6, 8);
  assert.equal(RS.normalize(moved), "plan");
  const diff = RS.panelRow("diffuser");
  const trap = RS.panelRow("trap");
  const cloud = RS.panelRow("cloud");
  assert.equal(diff.type, "porous");
  assert.equal(diff.face, "A");
  assert.equal(trap.type, "membrane");
  assert.equal(trap.build, "Bass trap");
  assert.equal(cloud.face, "F");
  assert.equal(cloud.build, "Cloud");
  assert.match(editor, /RoomShape\.hitPlan/);
  assert.match(editor, /RoomShape\.movePlanPoint/);
  assert.match(page, /id="roomAddDiffuser"/);
});

test("a plan or tilt token hides mirror and draws the slope", () => {
  const plan = RS.encodePlan(RS.regularPlan(6, 6, 8));
  assert.equal(RS.normalize(plan), "plan");
  assert.equal(RS.showMirrorToggle(plan), false);
  assert.equal(RS.showMirrorToggle("tilt:4:0.2"), false);
  assert.equal(RS.showMirrorToggle("plan"), true);
  assert.match(room, /showMirrorToggle\(state\.room_shape\)/);
  assert.equal(room.includes("showMirrorToggle(name)"), false);
  const elev = RS.elevOutline("tilt:0:0.2", 3, 8);
  assert.equal(elev[2][0], 8);
  assert.ok(Math.abs(elev[2][1] - 3) < 1e-9);
  assert.ok(Math.abs(elev[3][1] - 2.4) < 1e-9);
  const inset = Math.min(2.4, Math.abs(8 * Math.tan(4 * Math.PI / 180)));
  const floor = RS.floorOutline("tilt:4:0.2", 6, 8);
  assert.ok(Math.abs(floor[0][0] - inset) < 1e-9);
  assert.ok(Math.abs(floor[1][0] - (6 - inset)) < 1e-9);
  assert.deepEqual(floor[2], [6, 8]);
  assert.deepEqual(floor[3], [0, 8]);
});

test("the heat map uses a reflected denominator and stays a shoebox field", () => {
  const note = "First-order shoebox images, geometric 1/r, no absorption, no air, no tail";
  assert.equal(RS.heatMapNote("box"), note);
  assert.equal(RS.heatMapNote(RS.encodePlan(RS.regularPlan(6, 6, 8))), null);
  assert.equal(RS.heatMapNote("tilt:4:0.2"), null);
  assert.equal(RS.heatMapNote("splay"), null);
  const rev = RD.reverbDistance([2, 2, 2, 2, 2, 2]);
  assert.ok(Math.abs(rev - (1 / 3)) < 1e-12);
  const drr = RD.drrDb(1, rev);
  assert.ok(drr != null);
  assert.notEqual(drr, RD.levelDb(1));
  assert.match(editor, /RoomShape\.heatMapNote/);
  assert.match(editor, /Shoebox image map hidden/);
  assert.match(page, /id="floorHeatNote"/);
  assert.match(sl, /bp\.disabled/);
  assert.match(sl, /Every face is full \(90 %\)\./);
});
