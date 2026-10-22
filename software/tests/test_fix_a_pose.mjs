// node --test test_fix_a_pose.mjs
// FIX-A. Mix Room on C, and which point a Room strip draws. Display maths only.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const Pose = require("../static/js/room_view_pose.js");
const Drag = require("../static/js/drag_model.js");

const STAND_HINT_TOP = "The stand, from above. Scroll to zoom. Drag a capsule in or out, and the amber front to aim.";
const STAND_HINT_SIDE = "The stand, from the side. Drag left or right to turn the view. Drag a mic up or down.";

test("Mix Room on C sets third_mic after the save, and a repeat click keeps the save", () => {
  const first = Pose.mixThird("off", "c", "room", false, null);
  assert.equal(first.saved, "off");
  assert.equal(first.third, "room");
  const again = Pose.mixThird("room", "c", "room", true, first.saved);
  assert.equal(again.saved, "off");
  assert.equal(again.third, "room");
  const back = Pose.mixThird(again.third, "c", "array", true, again.saved);
  assert.equal(back.third, "off");
  assert.equal(back.saved, "off");
});

test("Mix Room on C restores a centre mic, and L does not touch third_mic", () => {
  const on = Pose.mixThird("centre", "c", "room", false, null);
  assert.equal(on.saved, "centre");
  assert.equal(on.third, "room");
  const ret = Pose.mixThird("room", "c", "array", true, on.saved);
  assert.equal(ret.third, "centre");
  const left = Pose.mixThird("off", "l", "room", false, null);
  assert.equal(left.third, "off");
  assert.equal(left.saved, null);
  const right = Pose.mixThird("room", "r", "array", true, "off");
  assert.equal(right.third, "room");
  assert.equal(right.saved, "off");
});

test("Return with nothing saved leaves third_mic alone", () => {
  const step = Pose.mixThird("room", "c", "array", true, null);
  assert.equal(step.third, "room");
  assert.equal(step.saved, null);
});

test("Top setback and the metres line read the room spot only while C is Room", () => {
  const stand = { mic_setup: "ortf", centre_dz: 0, space: 0.17, my: 1.5, third_mic: "off", place_c: "array" };
  const spot = { x: 5.5, y: 2.5, z: 0.4 };
  assert.equal(Pose.topSetback(stand, spot), " \u00b7 C setback 0 cm");
  assert.equal(Pose.metresMic(stand, spot), "space 0.17 m \u00b7 C 0 cm \u00b7 1.50 m high");
  const room = Object.assign({}, stand, { third_mic: "room", place_c: "room" });
  assert.equal(Pose.topSetback(room, spot), " \u00b7 C 5.50 m, 0.40 m");
  assert.equal(Pose.metresMic(room, spot), "space 0.17 m \u00b7 C 5.50 m, 0.40 m \u00b7 2.50 m high");
  const ears = Object.assign({}, room, { mic_setup: "binaural" });
  assert.equal(Pose.topSetback(ears, spot), "");
  assert.equal(Pose.metresMic(ears, spot), "space 0.17 m \u00b7 1.50 m high");
});

test("Side heights use the room spot per strip and leave on-stand capsules on the stand", () => {
  const state = { place_l: "array", place_c: "room", place_r: "array", third_mic: "room" };
  const stands = { l: { y: 1.2 }, c: { y: 1.5 }, r: { y: 1.8 } };
  const spots = { l: { y: 0.2 }, c: { y: 2.5 }, r: { y: 0.3 } };
  assert.equal(Pose.sideHeightLine(state, stands, spots), "height  L 1.20  C 2.50  R 1.80 m");
  const none = { place_l: "array", place_c: "array", place_r: "array", third_mic: "off" };
  assert.equal(Pose.sideHeightLine(none, stands, spots), "height  L 1.20  C 1.50  R 1.80 m");
});

test("Plane hints stay the stand sentences until a strip is Room", () => {
  assert.equal(Pose.planeHint("top", false), STAND_HINT_TOP);
  assert.equal(Pose.planeHint("side", false), STAND_HINT_SIDE);
  assert.match(Pose.planeHint("top", true), /Room mics sit at their spots/);
  assert.match(Pose.planeHint("side", true), /Drag one up or down/);
});

test("A room capsule's 3D local is the spot minus the stand, and on-stand stays on the bar", () => {
  const bar = Pose.capsuleLocal(false, { x: -0.085, y: 1.5, z: 0 }, { x: 3, z: 6.5 }, { x: 5.5, y: 2.5 }, 7.6);
  assert.deepEqual(bar, { x: -0.085, y: 1.5, z: 0, room: false });
  const moved = Pose.capsuleLocal(true, { x: 0, y: 1.5, z: 0 }, { x: 3, z: 6.5 }, { x: 5.5, y: 2.5, z: 0.4 }, 7.6);
  assert.equal(moved.room, true);
  assert.ok(Math.abs(moved.x - 2.5) < 1e-9);
  assert.ok(Math.abs(moved.y - 2.5) < 1e-9);
  assert.ok(Math.abs(moved.z - 1.1) < 1e-9);
});

test("A room-capsule drag writes room_c_* and not the stand", () => {
  const floor = Drag.roomFloorDragTo({ W: 6, L: 8 }, "c", 5.55, 0.44);
  assert.deepEqual(Object.keys(floor).sort(), ["room_c_x", "room_c_z"]);
  assert.equal(floor.room_c_x, 5.55);
  assert.equal(floor.room_c_z, 0.44);
  assert.equal(floor.centre_dz, undefined);
  assert.equal(floor.space, undefined);
  assert.equal(floor.mcx, undefined);
  const height = Drag.roomHeightDragTo({ H: 3 }, "c", 2.54);
  assert.deepEqual(Object.keys(height), ["room_c_y"]);
  assert.equal(height.room_c_y, 2.54);
  assert.equal(height.my, undefined);
  assert.equal(height.my_c, undefined);
});
