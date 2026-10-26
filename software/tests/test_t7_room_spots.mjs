// node --test test_t7_room_spots.mjs
// Migration and the heard spot. A stored per-strip key wins. Missing keys copy the shared room_*.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const D = require("../static/js/drag_model.js");
const here = dirname(fileURLToPath(import.meta.url));

const shared = { room_x: 4, room_z: 2, room_y: 1.5, room_yaw: 0 };

test("migrate copies the shared spot onto every strip", () => {
  const p = D.migrateRoomSpots(shared);
  for (const cap of ["l", "c", "r"]) {
    assert.equal(p["room_" + cap + "_x"], 4);
    assert.equal(p["room_" + cap + "_z"], 2);
    assert.equal(p["room_" + cap + "_y"], 1.5);
    assert.equal(p["room_" + cap + "_yaw"], 0);
  }
});

test("a stored per-strip key is not overwritten", () => {
  const p = D.migrateRoomSpots({ ...shared, room_r_x: 5.5, room_l_yaw: -12 });
  assert.equal(p.room_r_x, undefined);
  assert.equal(p.room_l_yaw, undefined);
  assert.equal(p.room_r_z, 2);
  assert.equal(p.room_l_x, 4);
});

test("roomSpot falls back to the shared spot, then prefers the stored one", () => {
  assert.deepEqual(D.roomSpot(shared, "r"), { x: 4, y: 1.5, z: 2, yaw: 0 });
  const stored = { ...shared, room_r_x: 5.5, room_r_z: 6, room_r_y: 1.2, room_r_yaw: 15 };
  assert.deepEqual(D.roomSpot(stored, "r"), { x: 5.5, y: 1.2, z: 6, yaw: 15 });
  assert.deepEqual(D.roomSpot(stored, "l"), { x: 4, y: 1.5, z: 2, yaw: 0 });
});

test("RoomMath stand pose is mcx ± space/2 at stand height and Z", () => {
  globalThis.window = globalThis;
  const src = readFileSync(join(here, "../static/js/room_math.js"), "utf8");
  eval(src);
  const g = globalThis.RoomMath.compute({
    W: 6, H: 3, L: 8, sx: 2.6, sz: 4.75, sy: 1.2,
    mcx: 3, mcz: 1.5, my: 1.5, space: 0.17, centre_dz: 0,
    align_horizontal: true,
    yaw_l_deg: -55, yaw_c_deg: 0, yaw_r_deg: 55,
    toe_half_deg: 55
  });
  assert.ok(Math.abs(g.mic_left.x - (3 - 0.085)) < 1e-9);
  assert.ok(Math.abs(g.mic_right.x - (3 + 0.085)) < 1e-9);
  assert.equal(g.mic_left.y, 1.5);
  assert.equal(g.mic_right.y, 1.5);
  assert.equal(g.mic_left.z, 1.5);
  assert.equal(g.mic_right.z, 1.5);
  assert.equal(g.mic_centre.x, 3);
  assert.equal(g.mic_centre.z, 1.5);
  assert.equal(g.toe_l_deg, -55);
  assert.equal(g.toe_r_deg, 55);
});

test("hypercardioid is 1 / 0.25 / 0.5 and supercardioid stays 0.37", () => {
  globalThis.window = globalThis;
  const src = readFileSync(join(here, "../static/js/room_math.js"), "utf8");
  eval(src);
  const RM = globalThis.RoomMath;
  const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, [a, b]);
  near(RM.polarGain(0, "cardioid", 1, "hypercardioid"), 1);
  near(RM.polarGain(Math.PI / 2, "cardioid", 1, "hypercardioid"), 0.25);
  near(Math.abs(RM.polarGain(Math.PI, "cardioid", 1, "hypercardioid")), 0.5);
  near(RM.polarGain(Math.PI / 2, "cardioid", 1), 0.37);
  assert.equal(RM.derivePattern("cardioid", 1, "hypercardioid"), "hypercardioid");
  assert.equal(RM.derivePattern("cardioid", 0.8, "hypercardioid"), "supercardioid");
  assert.equal(RM.polarLabel("cardioid", 1, "hypercardioid"), "Hypercardioid");
});
