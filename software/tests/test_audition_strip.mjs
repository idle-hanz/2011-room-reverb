// PREAMP-AU1. The live audition needs the worklet, so there is no toggle.
// The default scene posts the same keys as HEAD. WORKLET_VER stays 63.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { appSource as app } from "./app_sources.mjs";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const R = require("../static/js/routing_scene.js");
const page = readFileSync(join(here, "../static/index.html"), "utf8");
const live = readFileSync(join(here, "../static/js/live_fdn.js"), "utf8");

const ENGINE_KEYS = [
  "bloom_preset", "bloom_amount", "bloom_colour", "glue_colour",
  "pre_colour", "pre_drive_db", "predelay_ms",
  "bloom_attack_scale", "bloom_release_scale",
  "array_preset", "array_amount", "array_pre", "array_drive_db",
  "room_preset", "room_amount", "room_pre", "room_drive_db"
];

function freshState() {
  const state = {};
  ["array", "room", "master"].forEach(function (name) {
    state["route_" + name + "_pre"] = "none";
    state["route_" + name + "_drive"] = 0;
    state["route_" + name + "_comp"] = "off";
    state["route_" + name + "_amount"] = 0;
  });
  return state;
}

function posted(src) {
  const start = app.indexOf("/* Play posts the master strip");
  const end = app.indexOf("applyTreatAmount(o);", start);
  assert.ok(start > 0 && end > start);
  const call = new Function("o", "src", "window", "RRRouting", app.slice(start, end) + "\nreturn o;");
  return call(Object.assign({}, src), src, { RRRouting: R }, R);
}

test("the audition toggle defaults off and the default scene posts the same keys", () => {
  assert.equal(page.includes("Audition strip"), false);
  assert.equal(page.includes('id="auditionStrip"'), false);
  assert.match(live, /var WORKLET_VER = 63/);
  const body = posted(freshState());
  assert.equal(body.audition_strip, undefined);
  assert.equal(body.audition, undefined);
  ENGINE_KEYS.forEach(function (k) {
    assert.equal(Object.prototype.hasOwnProperty.call(body, k), false, k);
  });
  assert.deepEqual(R.masterScene(freshState()), {});
  assert.deepEqual(R.renderScene(freshState()), {});
});
