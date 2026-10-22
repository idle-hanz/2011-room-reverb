// node --test test_t8_room_mic_drag.mjs
// T8 room-mic drag: height, aim, floor inset, and the side-view overlap order.
// Points at the live drag_model.js, the same way test_t7_room_spots.mjs does.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const D = createRequire(import.meta.url)("../static/js/drag_model.js");

const room = { W: 6, H: 3, L: 8 };

function keysOf(p) {
  return Object.keys(p).sort();
}

function onStep(v, decimals) {
  const shown = Number(v).toFixed(decimals);
  assert.equal(Number(shown), v);
  assert.equal(shown.split(".")[1].length, decimals);
}

test("floor drag writes only X and Z, 10 cm short of each wall, on the 0.01 step", () => {
  const p = D.roomFloorDragTo(room, "r", 2.234, 3.235);
  assert.deepEqual(keysOf(p), ["room_r_x", "room_r_z"]);
  assert.equal(p.room_r_x, 2.23);
  assert.equal(p.room_r_z, 3.24);
  onStep(p.room_r_x, 2);
  onStep(p.room_r_z, 2);
  const wall = D.roomFloorDragTo(room, "l", -1, 9);
  assert.equal(wall.room_l_x, 0.1);
  assert.equal(wall.room_l_z, 7.9);
  assert.equal(wall.place_l, undefined);
  const far = D.roomFloorDragTo(room, "c", 0, 0);
  assert.equal(far.room_c_x, 0.1);
  assert.equal(far.room_c_z, 0.1);
});

test("height drag writes only Y, between 0.10 and H-0.10, not the Mic height slider", () => {
  assert.deepEqual(keysOf(D.roomHeightDragTo(room, "r", 1.234)), ["room_r_y"]);
  assert.equal(D.roomHeightDragTo(room, "r", 1.234).room_r_y, 1.23);
  assert.equal(D.roomHeightDragTo(room, "r", 1.235).room_r_y, 1.24);
  assert.equal(D.roomHeightDragTo(room, "c", 0.05).room_c_y, 0.1);
  assert.equal(D.roomHeightDragTo(room, "l", 19).room_l_y, 2.9);
  const y = D.roomHeightDragTo(room, "r", 2).room_r_y;
  onStep(y, 2);
  assert.ok(y >= 0.1 && y <= room.H - 0.1);
});

test("aim drag writes only yaw, on the 0.1 degree step", () => {
  assert.deepEqual(keysOf(D.roomAimDragTo(room, "r", 10.04)), ["room_r_yaw"]);
  assert.equal(D.roomAimDragTo(room, "r", 10.04).room_r_yaw, 10);
  assert.equal(D.roomAimDragTo(room, "r", 10.05).room_r_yaw, 10.1);
  assert.equal(D.roomAimDragTo(room, "l", -10.05).room_l_yaw, -10.1);
  assert.equal(D.roomAimDragTo(room, "c", 0).room_c_yaw, 0);
  assert.equal(D.roomAimDragTo(room, "r", 190).room_r_yaw, -170);
  assert.equal(D.roomAimDragTo(room, "r", 179.97).room_r_yaw, 180);
  const yaw = D.roomAimDragTo(room, "r", 20).room_r_yaw;
  onStep(yaw, 1);
  assert.equal(D.roomAimDragTo(room, "r", 20).place_r, undefined);
});

test("side-view overlap at the same Z: the dragged mic wins, otherwise the last drawn", () => {
  // Draw order is L, then C, then R. R is painted last, so R is on top.
  assert.deepEqual(D.ROOM_DRAW_ORDER, ["l", "c", "r"]);
  assert.equal(D.pickRoomMic(D.ROOM_DRAW_ORDER, ["l", "r"], null), "r");
  assert.equal(D.pickRoomMic(D.ROOM_DRAW_ORDER, ["l", "c", "r"], null), "r");
  assert.equal(D.pickRoomMic(D.ROOM_DRAW_ORDER, ["l", "r"], "l"), "l");
  assert.equal(D.pickRoomMic(D.ROOM_DRAW_ORDER, ["c"], "r"), "c");
});
