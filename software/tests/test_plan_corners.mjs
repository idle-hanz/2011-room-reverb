// Typed plan corners, the selected corner, and the 5–8 add and delete limits.
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
const editor = readFileSync(join(here, "../static/js/room_editor.js"), "utf8");
const app = readFileSync(join(here, "../static/js/app.js"), "utf8");
const settings = readFileSync(join(here, "../static/js/rr_settings.js"), "utf8");

function near(a, b) {
  assert.ok(Math.abs(a - b) < 0.02, a + " vs " + b);
}

test("a typed corner is stored at two decimals and round-trips in the setup JSON", () => {
  const base = RS.encodePlan(RS.regularPlan(6, 6, 8));
  const pts = RS.planPoints(base);
  const typed = RS.typePlanCorner(base, 0, pts[0][0] + 0.11, pts[0][1], 6, 8);
  const next = RS.planPoints(typed);
  assert.notEqual(typed, base);
  assert.equal(RS.planDragNote(), "");
  assert.equal(RS.normalize(typed), "plan");
  assert.equal(next.length, 6);
  near(next[0][0], pts[0][0] + 0.11);
  near(next[0][1], pts[0][1]);
  assert.match(typed, /plan:[0-9.]+,[0-9.]+/);
  for (let i = 1; i < 6; i++) {
    near(next[i][0], pts[i][0]);
    near(next[i][1], pts[i][1]);
  }
  const saved = JSON.parse(JSON.stringify({ room_shape: typed, W: 6, H: 3, L: 8 }));
  assert.equal(saved.room_shape, typed);
  assert.equal(Object.prototype.hasOwnProperty.call(saved, "planSelected"), false);
  assert.match(settings, /JSON\.stringify\(state\)/);
  assert.match(settings, /state\[k\] = data\[k\]/);
  assert.match(room, /typePlanCorner/);
});

test("delete removes only the selected corner", () => {
  const six = RS.encodePlan(RS.regularPlan(6, 6, 8));
  const before = RS.planPoints(six);
  const cut = RS.delPlanCorner(six, 2);
  const after = RS.planPoints(cut);
  assert.equal(RS.planNote(), "");
  assert.equal(after.length, 5);
  const expect = before.filter(function (_, i) { return i !== 2; });
  after.forEach(function (p, i) {
    near(p[0], expect[i][0]);
    near(p[1], expect[i][1]);
  });
});

test("a dent is refused and the 5 and 8 limits keep the token", () => {
  const plan = RS.encodePlan([[1, 1], [5, 1], [5, 6], [3, 7], [1, 6]]);
  const dent = RS.typePlanCorner(plan, 2, 2, 2, 6, 8);
  assert.equal(dent, plan);
  assert.equal(RS.planDragNote(), "That corner would dent the plan");

  const five = RS.encodePlan(RS.regularPlan(5, 6, 8));
  assert.equal(RS.delPlanCorner(five, 1), five);
  assert.equal(RS.planNote(), "At least 5 corners");

  const eight = RS.encodePlan(RS.regularPlan(8, 6, 8));
  assert.equal(RS.addPlanCorner(eight, 3), eight);
  assert.equal(RS.planNote(), "At most 8 corners");
});

test("plus inserts the midpoint of the wall after the selected corner", () => {
  const token = RS.encodePlan(RS.regularPlan(6, 6, 8));
  const pts = RS.planPoints(token);
  const grown = RS.addPlanCorner(token, 0);
  const next = RS.planPoints(grown);
  assert.equal(RS.planNote(), "");
  assert.equal(next.length, 7);
  near(next[0][0], pts[0][0]);
  near(next[0][1], pts[0][1]);
  near(next[1][0], (pts[0][0] + pts[1][0]) * 0.5);
  near(next[1][1], (pts[0][1] + pts[1][1]) * 0.5);
  near(next[2][0], pts[1][0]);
  near(next[2][1], pts[1][1]);
  const bare = RS.addPlanCorner(RS.encodePlan(RS.regularPlan(5, 6, 8)));
  assert.equal(RS.planPoints(bare).length, 6);
});

test("the corner list is plan-only and a floor click selects that corner", () => {
  assert.match(page, /id="roomCornerList" hidden/);
  assert.match(page, /id="roomCornerNote" hidden/);
  assert.match(room, /function paintRoomCorners/);
  assert.match(room, /name === "plan"/);
  assert.match(room, /Corner " \+ \(i \+ 1\) \+ " X metres/);
  assert.match(room, /data-axis", "z"/);
  assert.match(editor, /RoomShape\.selectPlanCorner\(planHit\.index\)/);
  assert.match(editor, /#f5c16c/);
  assert.match(app, /addPlanCorner\(state\.room_shape, idx\)/);
  assert.match(app, /delPlanCorner\(state\.room_shape, idx\)/);
  RS.selectPlanCorner(4);
  assert.equal(RS.planSelection(), 4);
  RS.selectPlanCorner(-2);
  assert.equal(RS.planSelection(), 0);
});
