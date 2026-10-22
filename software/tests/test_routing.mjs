// node --test test_routing.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

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
