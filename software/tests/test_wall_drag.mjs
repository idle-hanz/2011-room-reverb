// node --test tests/test_wall_drag.mjs
// Backlog B: existing drag_model wall and ceiling maths, and the room_editor call.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const D = require("../static/js/drag_model.js");
const here = dirname(fileURLToPath(import.meta.url));
const editor = readFileSync(join(here, "../static/js/room_editor.js"), "utf8");
const page = readFileSync(join(here, "../static/index.html"), "utf8");

const state = {
  W: 6, L: 8, H: 3,
  sx: 3, sz: 6, sy: 1.5,
  mcx: 3, mcz: 2, my: 1.2,
  space: 0.17,
  two_sources: false,
  place_l: "stand", place_c: "stand", place_r: "stand",
};

const lay = { ox: 50, oy: 40, scale: 50, W: 6, L: 8, H: 3 };

test("a wall band hits, the room centre does not", () => {
  const right = D.hitWall(50 + 6 * 50, 40 + 4 * 50, lay);
  assert.equal(right.kind, "wall");
  assert.deepEqual(right.walls, ["x1"]);
  const corner = D.hitWall(50 + 6 * 50, 40, lay);
  assert.equal(corner.kind, "corner");
  assert.deepEqual(corner.walls, ["x1", "z1"]);
  assert.equal(D.hitWall(50 + 3 * 50, 40 + 4 * 50, lay), null);
});

test("the right wall grows width and leaves the source", () => {
  const hit = D.hitWall(350, 240, lay);
  const ctx = D.beginWallDrag(state, hit, lay, 350, 240);
  const res = D.wallDragTo(ctx, 400, 240, { shift: false, mode: "stop" });
  assert.equal(res.patch.W, 7);
  assert.equal(res.patch.sx, undefined);
  assert.equal(res.patch.L, 8);
});

test("the left wall grows width and shifts the source so it stays put", () => {
  const hit = D.hitWall(50, 240, lay);
  assert.deepEqual(hit.walls, ["x0"]);
  const ctx = D.beginWallDrag(state, hit, lay, 50, 240);
  const res = D.wallDragTo(ctx, 0, 240, { shift: false, mode: "stop" });
  assert.equal(res.patch.W, 7);
  assert.equal(res.patch.sx, 4);
});

test("the ceiling grows height and leaves the source height", () => {
  const elay = { ox: 50, oy: 30, scale: 40, L: 8, H: 3 };
  const hit = D.hitCeiling(210, 30, elay);
  assert.equal(hit.kind, "ceiling");
  assert.equal(D.hitCeiling(210, 80, elay), null);
  const ctx = D.beginWallDrag(state, hit, elay, 210, 30);
  const res = D.ceilingDragTo(ctx, 210, -10, elay, {});
  assert.equal(res.patch.H, 4);
  assert.equal(res.patch.sy, undefined);
});

test("room_editor calls wall and ceiling drag only after a handle miss", () => {
  const floorDown = editor.indexOf('floorCanvas.addEventListener("pointerdown"');
  const floorMove = editor.indexOf('floorCanvas.addEventListener("pointermove"');
  const floor = editor.slice(floorDown, floorMove);
  assert.ok(floor.indexOf("hitFloor") < floor.indexOf("hitWall"));
  assert.match(floor, /kind:\s*"wall"/);
  const elevDown = editor.indexOf('elevCanvas.addEventListener("pointerdown"');
  const elevMove = editor.indexOf('elevCanvas.addEventListener("pointermove"');
  const elev = editor.slice(elevDown, elevMove);
  assert.ok(elev.indexOf("hitElev") < elev.indexOf("hitCeiling"));
  assert.match(elev, /kind:\s*"ceiling"/);
  assert.match(editor, /function viewForPatch/);
  assert.match(editor, /mode:\s*"stop"/);
  assert.match(page, /room_editor\.js\?v=21/);
  assert.match(page, /drag a wall or corner to resize/);
  assert.match(page, /drag the ceiling to resize/);
});
