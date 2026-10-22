// node --test test_drag_model.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const D = createRequire(import.meta.url)("./drag_model.js");
// app defaults (app.js 74-97): W6 H3 L8, sx 2.6 sz 4.75 sy 1.2, mcx 3 mcz 1.5 my 1.5, space 0.17 (ORTF)
const S = () => ({ W: 6, H: 3, L: 8, sx: 2.6, sz: 4.75, sy: 1.2, mcx: 3, mcz: 1.5, my: 1.5, space: 0.17,
  two_sources: false, place_l: "array", place_c: "array", place_r: "array", room_x: 1, room_z: 6, room_y: 2, room_yaw: 0 });
const lay = { ox: 50, oy: 20, scale: 50, W: 6, L: 8 };          // room drawn 300 x 400 px
const px = (x) => lay.ox + x * lay.scale, py = (z) => lay.oy + (lay.L - z) * lay.scale;

test("hit-test: walls, corners, inside, outside", () => {
  assert.deepEqual(D.hitWall(px(6) + 3, py(4), lay), { kind: "wall", walls: ["x1"] });
  assert.deepEqual(D.hitWall(px(0) - 2, py(4), lay), { kind: "wall", walls: ["x0"] });
  assert.deepEqual(D.hitWall(px(3), py(8) + 1, lay), { kind: "wall", walls: ["z1"] });  // Front, top of page
  assert.deepEqual(D.hitWall(px(3), py(0) - 4, lay), { kind: "wall", walls: ["z0"] });  // Back, bottom
  assert.deepEqual(D.hitWall(px(6) - 5, py(8) + 5, lay), { kind: "corner", walls: ["x1", "z1"] });
  assert.equal(D.hitWall(px(3), py(4), lay), null);
  assert.equal(D.hitWall(px(6) + 20, py(4), lay), null);
});
test("drag right wall: W follows the pointer, nothing else moves", () => {
  const c = D.beginWallDrag(S(), { kind: "wall", walls: ["x1"] }, lay);
  const r = D.wallDragTo(c, px(7.234), py(4), {});
  assert.deepEqual(r.patch, { W: 7.23, L: 8 });
  assert.equal(r.label, "Width 7.23 m");
  assert.equal(D.wallDragTo(c, px(7.234), py(4), { shift: true }).patch.W, 7.2);
});
test("drag left wall: W shrinks and every x shifts so objects stay put on screen", () => {
  const c = D.beginWallDrag(S(), { kind: "wall", walls: ["x0"] }, lay);
  const r = D.wallDragTo(c, px(1), py(4), {});
  assert.equal(r.patch.W, 5);
  assert.equal(r.patch.sx, 1.6); assert.equal(r.patch.mcx, 2); assert.equal(r.patch.room_x, 0);
});
test("'stop' mode: a wall cannot pass an object (+10 cm)", () => {
  const c = D.beginWallDrag(S(), { kind: "wall", walls: ["x1"] }, lay);
  const r = D.wallDragTo(c, px(2), py(4), {});
  // rightmost object is the R capsule at 3 + 0.085 = 3.085 -> wall stops at 3.185
  assert.ok(Math.abs(r.patch.W - 3.185) < 1e-9, r.patch.W); assert.equal(r.held, true);
  const c2 = D.beginWallDrag(S(), { kind: "wall", walls: ["z1"] }, lay);
  assert.equal(D.wallDragTo(c2, px(3), py(3), {}).patch.L, 4.85);   // source at z 4.75
});
test("'push' mode clamps objects instead", () => {
  const c = D.beginWallDrag(S(), { kind: "wall", walls: ["x1"] }, lay);
  const r = D.wallDragTo(c, px(2), py(4), { mode: "push" });
  assert.equal(r.patch.W, 2); assert.equal(r.patch.mcx, 1.9); assert.equal(r.patch.sx, 1.9);
});
test("limits from the sliders hold (W 1..80, L 2..120)", () => {
  const big = { ...S(), sx: 0.5, mcx: 0.5, space: 0, room_x: 0.3 };
  const c = D.beginWallDrag(big, { kind: "wall", walls: ["x1"] }, lay);
  assert.equal(D.wallDragTo(c, px(500), py(4), {}).patch.W, 80);
  assert.equal(D.wallDragTo(c, px(0.2), py(4), { mode: "push" }).patch.W, 1);
});
test("grab offset: grabbing 2 px outside the wall does not make it jump", () => {
  const c = D.beginWallDrag(S(), { kind: "wall", walls: ["x1"] }, lay, px(6) + 2, py(4));
  assert.equal(D.wallDragTo(c, px(6) + 2, py(4), {}).patch.W, 6);
  assert.equal(D.wallDragTo(c, px(7.5) + 2, py(4), {}).patch.W, 7.5);
  const c2 = D.beginWallDrag(S(), { kind: "wall", walls: ["z0"] }, lay, px(3), py(0) + 3);
  assert.equal(D.wallDragTo(c2, px(3), py(0.5) + 3, {}).patch.L, 7.5);
});
test("corner drag sets W and L together", () => {
  const c = D.beginWallDrag(S(), { kind: "corner", walls: ["x1", "z1"] }, lay);
  const r = D.wallDragTo(c, px(7), py(9), {});
  assert.deepEqual([r.patch.W, r.patch.L], [7, 9]); assert.equal(r.label, "Width 7.00 m \u00b7 Length 9.00 m");
});
test("ceiling: stops above the highest mic/source", () => {
  const elay = { ox: 40, oy: 20, scale: 50, L: 8, H: 3 };
  const c = D.beginWallDrag(S(), { kind: "ceiling", walls: ["y1"] }, elay);
  const yPx = (y) => elay.oy + (elay.H - y) * elay.scale;
  assert.equal(D.ceilingDragTo(c, 100, yPx(4.2), elay).patch.H, 4.2);
  assert.equal(D.ceilingDragTo(c, 100, yPx(1.0), elay).patch.H, 1.6);   // mic at 1.5 + 0.1
  assert.ok(D.hitCeiling(100, elay.oy + 3, elay)); assert.equal(D.hitCeiling(100, elay.oy + 30, elay), null);
});
test("mic drag: mirror sets space, linked moves stand, split frees R", () => {
  assert.deepEqual(D.micDragTo(S(), "r", 3.5, 2, "mirror"), { space: 1, mcz: 2 });
  assert.deepEqual(D.micDragTo(S(), "l", 2.5, 2, "linked"), { mcx: 2.585, mcz: 2 });
  assert.deepEqual(D.micDragTo(S(), "r", 5, 7, "split"), { place_r: "room", room_r_x: 5, room_r_z: 7 });
  const s = { ...S(), place_c: "room" };
  assert.deepEqual(D.micDragTo(s, "c", 9, -1, "mirror"), { place_c: "room", room_c_x: 6, room_c_z: 0 });
  // mirror space is capped by the nearer wall
  assert.equal(D.micDragTo({ ...S(), mcx: 1 }, "r", 4, 2, "mirror").space, 2);
});
test("T7 migration copies the shared room spot to each strip (no value changes)", () => {
  const p = D.migrateRoomSpots(S());
  assert.deepEqual([p.room_l_x, p.room_c_z, p.room_r_y, p.room_r_yaw], [1, 6, 2, 0]);
  assert.deepEqual(D.migrateRoomSpots({ ...S(), room_l_x: 4 }).room_l_x, undefined);
});
test("wall field for double-click typing", () => {
  assert.equal(D.fieldForWall({ kind: "wall", walls: ["z0"] }), "L");
  assert.equal(D.fieldForWall({ kind: "ceiling", walls: ["y1"] }), "H");
});
