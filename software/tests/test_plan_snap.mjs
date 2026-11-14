// A plan corner snaps, then a dent or a point still outside is refused.
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
const editor = readFileSync(join(here, "../static/js/room_editor.js"), "utf8");

const PLAN = RS.encodePlan([[1, 1], [5, 1], [5, 6], [3, 7], [1, 6]]);

function pt(token, i) {
  return RS.planPoints(token)[i];
}

test("the step snaps before the corner is stored", () => {
  const shifted = RS.movePlanPoint(PLAN, 0, 1.04, 2.06, 6, 8, 0.1);
  assert.equal(RS.planDragNote(), "");
  assert.ok(Math.abs(pt(shifted, 0)[0] - 1) <= 1e-9);
  assert.ok(Math.abs(pt(shifted, 0)[1] - 2.1) <= 1e-9);
  assert.match(shifted, /1\.00,2\.10/);

  const fine = RS.movePlanPoint(PLAN, 0, 1.004, 1.006, 6, 8);
  assert.ok(Math.abs(pt(fine, 0)[0] - 1) <= 1e-9);
  assert.ok(Math.abs(pt(fine, 0)[1] - 1.01) <= 1e-9);

  const edge = RS.movePlanPoint(PLAN, 0, 0.004, 1, 6, 8, 0.01);
  assert.equal(RS.planDragNote(), "");
  assert.ok(Math.abs(pt(edge, 0)[0] - 0) <= 1e-9);
  assert.equal(RS.normalize(edge), "plan");

  const onWall = RS.movePlanPoint(PLAN, 1, 6.04, 4, 6, 8, 0.1);
  assert.equal(RS.planDragNote(), "");
  assert.ok(Math.abs(pt(onWall, 1)[0] - 6) <= 1e-9);
  assert.ok(Math.abs(pt(onWall, 1)[1] - 4) <= 1e-9);
});

test("a point still outside or a dent keeps the old corner", () => {
  const outside = RS.movePlanPoint(PLAN, 1, 6.04, 4, 6, 8, 0.01);
  assert.equal(outside, PLAN);
  assert.equal(RS.planDragNote(), "Corner stays outside the room");

  const dent = RS.movePlanPoint(PLAN, 2, 2, 2, 6, 8, 0.01);
  assert.equal(dent, PLAN);
  assert.equal(RS.planDragNote(), "That corner would dent the plan");

  const hex = RS.encodePlan(RS.regularPlan(6, 6, 8));
  const moved = RS.movePlanPoint(hex, 0, 0.2, 0.2, 6, 8);
  assert.equal(typeof moved, "string");
  assert.equal(RS.normalize(moved), "plan");
});

test("both floor plans can show the drag note", () => {
  assert.match(page, /id="floorPlanNote"/);
  assert.match(page, /id="srcFloorPlanNote"/);
  assert.match(editor, /evt\.shiftKey \? 0\.1 : 0\.01/);
  assert.match(editor, /floorPlanNote/);
  assert.match(editor, /srcFloorPlanNote/);
  assert.match(editor, /RoomShape\.planDragNote/);
});
