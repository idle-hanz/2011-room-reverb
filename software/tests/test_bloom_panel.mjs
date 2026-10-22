// node --test test_bloom_panel.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const B = createRequire(import.meta.url)("../static/js/bloom_scene.js");

const roomCrush = {
  bloom_on: true,
  bloom_menu: "room_crush",
  bloom_amount_ui: 100,
  bloom_colour_ui: false,
  glue_colour_ui: false,
  pre_drive_ui: 0,
  predelay_ui: 0,
  bloom_attack_ui: 1,
  bloom_release_ui: 1,
};

test("off posts no bloom keys", () => {
  assert.deepEqual(B.scene({ ...roomCrush, bloom_on: false }), {});
});

test("room crush matches the bloom_listen settings", () => {
  // listen_report.json room_crush: amount 100, glue_colour false.
  // Colour, pre, predelay, and the scales are the engine defaults.
  assert.deepEqual(B.scene(roomCrush), {
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
});

test("neve and 610-A are pre colour, amount is drive", () => {
  const neve = B.scene({ bloom_on: true, bloom_menu: "neve1073", bloom_amount_ui: 80, pre_drive_ui: 6 });
  assert.equal(neve.pre_colour, "neve1073");
  assert.equal(neve.bloom_amount, 0);
  assert.equal(neve.pre_drive_db, 6);
  const a = B.scene({ bloom_on: true, bloom_menu: "u610a", pre_drive_ui: 0 });
  assert.equal(a.pre_colour, "u610a");
  assert.equal(a.bloom_amount, 0);
  assert.equal(a.pre_drive_db, 0);
});

test("glue colour posts only on Glue", () => {
  const glue = B.scene({ bloom_on: true, bloom_menu: "glue", bloom_amount_ui: 40, glue_colour_ui: true });
  assert.equal(glue.glue_colour, true);
  assert.equal(glue.bloom_colour, false);
  const crush = B.scene({ ...roomCrush, glue_colour_ui: true });
  assert.equal(crush.glue_colour, false);
});
