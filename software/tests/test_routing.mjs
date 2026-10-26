// node --test test_routing.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { appSource as app } from "./app_sources.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));

const R = createRequire(import.meta.url)("../static/js/routing_scene.js");

const off = {
  route_array_pre: "none", route_array_drive: 0, route_array_comp: "off", route_array_amount: 0,
  route_room_pre: "none", route_room_drive: 0, route_room_comp: "off", route_room_amount: 0,
  route_master_pre: "none", route_master_drive: 0, route_master_comp: "off", route_master_amount: 0,
};

test("off posts nothing", () => {
  assert.deepEqual(R.masterScene(off), {});
  assert.deepEqual(R.renderScene(off), {});
});

test("old room crush lands on the master strip", () => {
  const src = {
    bloom_on: true,
    bloom_menu: "room_crush",
    bloom_amount_ui: 100,
    glue_colour_ui: false,
  };
  R.migrate(src);
  assert.equal(src.route_master_comp, "room_crush");
  assert.equal(src.route_master_amount, 100);
  assert.equal(src.route_master_pre, "none");
  assert.deepEqual(R.masterScene(src), {
    bloom_preset: "room_crush",
    bloom_amount: 100,
    bloom_colour: false,
    glue_colour: false,
    pre_colour: "off",
    pre_drive_db: 0,
    predelay_ms: 0,
    bloom_attack_scale: 1,
    bloom_release_scale: 1,
  });
  assert.deepEqual(R.renderScene(src), {});
});

test("old neve lands on the master preamp", () => {
  const src = { bloom_on: true, bloom_menu: "neve1073", pre_drive_ui: 6, bloom_amount_ui: 80 };
  R.migrate(src);
  assert.equal(src.route_master_pre, "neve1073");
  assert.equal(src.route_master_drive, 6);
  assert.equal(src.route_master_comp, "off");
  const scene = R.masterScene(src);
  assert.equal(scene.pre_colour, "neve1073");
  assert.equal(scene.pre_drive_db, 6);
  assert.equal(scene.bloom_amount, 0);
});

test("render posts array and room and leaves master out", () => {
  const src = {
    ...off,
    route_array_pre: "neve1073",
    route_array_drive: 6,
    route_array_comp: "glue",
    route_array_amount: 100,
    route_room_pre: "u610a",
    route_room_drive: 6,
    route_room_comp: "room_crush",
    route_room_amount: 100,
    route_master_comp: "nuke",
    route_master_amount: 40,
  };
  assert.deepEqual(R.renderScene(src), {
    array_preset: "glue",
    array_amount: 100,
    array_pre: "neve1073",
    array_drive_db: 6,
    room_preset: "room_crush",
    room_amount: 100,
    room_pre: "u610a",
    room_drive_db: 6,
  });
  assert.equal(R.masterScene(src).bloom_preset, "nuke");
});

test("a comp at amount 0 stays off", () => {
  const src = { ...off, route_master_comp: "glue", route_master_amount: 0 };
  assert.deepEqual(R.masterScene(src), {});
});

test("master menu from off to room crush arms amount 100", () => {
  const src = { ...off, route_master_comp: "room_crush", route_master_amount: 0 };
  R.armMaster(src, "off");
  assert.equal(src.route_master_amount, 100);
  const scene = R.masterScene(src);
  assert.equal(scene.bloom_preset, "room_crush");
  assert.equal(scene.bloom_amount, 100);
  const stored = { ...off, route_master_comp: "room_crush", route_master_amount: 0 };
  assert.deepEqual(R.masterScene(stored), {});
  const array = { ...off, route_array_comp: "glue", route_array_amount: 0 };
  R.armStrip(array, "array", "off");
  assert.equal(array.route_array_amount, 100);
  const arrayScene = R.renderScene(array);
  assert.equal(arrayScene.array_preset, "glue");
  assert.equal(arrayScene.array_amount, 100);
  const storedArray = { ...off, route_array_comp: "glue", route_array_amount: 0 };
  R.armStrip(storedArray, "array", "glue");
  assert.equal(storedArray.route_array_amount, 0);
  assert.deepEqual(R.renderScene(storedArray), {});
  const room = { ...off, route_room_comp: "room_crush", route_room_amount: 0 };
  R.armStrip(room, "room", "off");
  assert.equal(room.route_room_amount, 100);
  const roomScene = R.renderScene(room);
  assert.equal(roomScene.room_preset, "room_crush");
  assert.equal(roomScene.room_amount, 100);
  const storedRoom = { ...off, route_room_comp: "room_crush", route_room_amount: 0 };
  R.armStrip(storedRoom, "room", "room_crush");
  assert.equal(storedRoom.route_room_amount, 0);
  assert.deepEqual(R.renderScene(storedRoom), {});
  const pre = { ...off, route_master_pre: "neve1073", route_master_drive: 6, route_master_comp: "off" };
  R.armMaster(pre, "off");
  assert.equal(pre.route_master_amount, 0);
  assert.equal(R.masterScene(pre).pre_colour, "neve1073");
  assert.equal(R.masterScene(pre).bloom_amount, 0);
});

function loadPackRoom() {
  const code = fs.readFileSync(path.join(HERE, "../static/js/pack_room.js"), "utf8");
  const sandbox = {};
  vm.runInNewContext(code, sandbox);
  return sandbox.packRoom;
}

function pushMessage(params) {
  const live = fs.readFileSync(path.join(HERE, "../static/js/live_fdn.js"), "utf8");
  const start = live.indexOf("msg = {");
  const end = live.indexOf("if (colour.route)", start);
  assert.ok(start > 0 && end > start);
  return new Function(
    "params", "colour", "monoFile", "snapRoom",
    live.slice(start, end) + "\nreturn msg;"
  )(params, { on: false }, false, false);
}

function section(blob, id) {
  const n = blob[3];
  for (let s = 0; s < n; s++) {
    if (blob[5 + s * 4] !== id) continue;
    const off = blob[6 + s * 4];
    const len = blob[7 + s * 4];
    return Array.from(blob.slice(off, off + len));
  }
  return null;
}

test("master room crush reaches the worklet as section 10", () => {
  const packRoom = loadPackRoom();
  const bloom = Array(40).fill(0);
  bloom[0] = 2;
  bloom[1] = 12;
  const on = pushMessage({ ok: true, g: 0.5, bloom: bloom, predelay_n: 0, pre_colour: null });
  const packed = section(packRoom(on), 10);
  assert.ok(packed);
  assert.equal(packed.length, 40);
  assert.equal(packed[0], 2);
  assert.equal(packed[1], 12);
  const off = pushMessage({ ok: true, g: 0.5 });
  assert.equal(section(packRoom(off), 10), null);
  assert.equal(section(packRoom(off), 12), null);
});

test("an on array strip reaches the worklet as section 13", () => {
  const packRoom = loadPackRoom();
  const side = Array(217).fill(0);
  side[3] = 1;
  side[85] = 2;
  side[86] = 1;
  const on = pushMessage({ ok: true, g: 0.5, side: side });
  const packed = section(packRoom(on), 13);
  assert.ok(packed);
  assert.equal(packed.length, 217);
  assert.equal(packed[85], 2);
  assert.equal(packed[86], 1);
  const off = pushMessage({ ok: true, g: 0.5 });
  assert.equal(section(packRoom(off), 13), null);
  const start = app.indexOf("function heardMix");
  const end = app.indexOf("function liveRequestBody", start);
  const body = app.slice(start, end);
  assert.match(body, /RRRouting\.renderScene/);
});
