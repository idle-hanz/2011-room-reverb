// node --test test_pair_room.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const Drag = require("../static/js/drag_model.js");
const app = fs.readFileSync(path.join(here, "../static/js/app.js"), "utf8");
const plan = fs.readFileSync(path.join(here, "../static/js/room_editor.js"), "utf8");
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");

const start = app.indexOf("function pairRoomMic(");
const end = app.indexOf("function loadDeskPreset(", start);
const pairRoomMic = new Function(
  "id",
  "room",
  "drag",
  app.slice(start, end) + "\nreturn pairRoomMic(id, room, drag);"
);

const boot = { W: 6, H: 3, L: 8 };
const PAIRS = ["ab_omni", "ab_card", "xy_90", "xy_120", "nos", "din"];
const LEFT = ["ortf", "ortf_c", "mono_c", "binaural", "ms", "ms_a", "ms_b", "ms_c", "ms_classic", "ms_2", "custom"];

test("the six pair setups place the centre strip at the room spot", () => {
  PAIRS.forEach((id) => {
    const patch = pairRoomMic(id, boot, Drag);
    assert.equal(patch.third_mic, "room", id);
    assert.equal(patch.place_c, "room", id);
    assert.equal(patch.room_c_x, 4, id);
    assert.equal(patch.room_c_y, 1.5, id);
    assert.equal(patch.room_c_z, 2, id);
    assert.equal(patch.room_c_yaw, 0, id);
    assert.equal(patch.fader_c, 0.5, id);
    assert.equal(patch.mute_c, false, id);
    assert.equal(patch.gain_exact_c, null, id);
  });
});

test("a room smaller than the spot keeps the mic 0.10 m inside the walls", () => {
  const patch = pairRoomMic("xy_90", { W: 2, H: 1.2, L: 3 }, Drag);
  assert.equal(patch.room_c_x, 1.9);
  assert.equal(patch.room_c_y, 1.1);
  assert.equal(patch.room_c_z, 2);
  assert.ok(patch.room_c_x >= 0.1 && patch.room_c_x <= 1.9);
  assert.ok(patch.room_c_y >= 0.1 && patch.room_c_y <= 1.1);
  assert.ok(patch.room_c_z >= 0.1 && patch.room_c_z <= 2.9);
});

test("ORTF stays centre off and the MS presets are not moved", () => {
  LEFT.forEach((id) => {
    assert.equal(pairRoomMic(id, boot, Drag), null, id);
  });
});

test("preset load writes the room patch and does not copy the stand", () => {
  const load = app.slice(app.indexOf("function loadDeskPreset("), app.indexOf("function deskWeights("));
  assert.match(load, /pairRoomMic\(id, state, window\.RRDrag\)/);
  assert.doesNotMatch(load, /snapRoomSpotToStand/);
  assert.doesNotMatch(load, /syncUI\(/);
  assert.doesNotMatch(load, /scheduleLiveParams\(/);
  const paint = app.slice(app.indexOf("function paintDesk("), app.indexOf("function bindDesk("));
  assert.match(paint, /stripIsRoom\("c"\) \? "Room mic" : "Centre"/);
});

test("the plan draws a room centre mic at its room spot and labels it Room mic", () => {
  assert.match(plan, /st\["place_" \+ cap\] === "room"/);
  assert.match(plan, /cap === "c" && st\.third_mic === "room"/);
  assert.match(plan, /roomSpotOf\(geo\.state, cap\)/);
  assert.match(plan, /cap === "c" \? "Room mic" : cap\.toUpperCase\(\)/);
});
