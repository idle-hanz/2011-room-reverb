// PREAMP-AU2. Audition strip is a Play flag. It is off by default and is not a preset key.
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
const work = readFileSync(join(here, "../static/js/fdn_worklet.js"), "utf8");

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

function makeEl(id, value) {
  return {
    id: id,
    value: String(value),
    checked: false,
    disabled: false,
    textContent: "",
    _ls: {},
    addEventListener: function (type, fn) {
      (this._ls[type] = this._ls[type] || []).push(fn);
    }
  };
}

function desk() {
  const els = {};
  function add(id, value) {
    els[id] = makeEl(id, value);
    return els[id];
  }
  const panel = add("routingPanel", "");
  add("auditionStrip", "");
  ["array", "room", "master"].forEach(function (name) {
    add("route_" + name + "_pre", "none");
    add("route_" + name + "_drive", "0");
    add("route_" + name + "_drive_out", "");
    add("route_" + name + "_comp", "off");
    add("route_" + name + "_amount", "0");
    add("route_" + name + "_amount_out", "");
  });
  const document = {
    activeElement: null,
    getElementById: function (id) { return els[id] || null; }
  };
  return {
    els: els,
    document: document,
    fire: function (child, type) {
      (panel._ls[type] || []).forEach(function (fn) { fn({ target: child }); });
    }
  };
}

function loadAud(state, document) {
  const start = app.indexOf("var auditionOn = false");
  const end = app.indexOf("function paintDesk", start);
  assert.ok(start > 0 && end > start);
  const posts = { n: 0 };
  const fn = new Function(
    "state", "document", "window", "RRRouting", "syncUI", "scheduleLiveParams",
    app.slice(start, end) + "\nreturn { clearPreamp: clearPreamp, paintRouting: paintRouting, bindRouting: bindRouting, on: function () { return auditionOn; } };"
  );
  const out = fn(
    state,
    document,
    { RRRouting: R },
    R,
    function () {},
    function () { posts.n += 1; }
  );
  out.posts = posts;
  return out;
}

test("the audition toggle defaults off and the default scene posts the same keys", () => {
  assert.match(page, /<input type="checkbox" id="auditionStrip" \/> Audition strip/);
  assert.equal(page.includes('id="auditionStrip" checked'), false);
  assert.match(app, /var auditionOn = false/);
  assert.match(app, /auditionOn = false/);
  assert.match(live, /var WORKLET_VER = 64/);
  assert.match(live, /if \(typeof auditionOn !== "undefined" && auditionOn\) msg\.audition = 1;/);
  assert.equal(live.includes("msg.audition = 0"), false);
  assert.match(work, /if \(this\.audition && api\.live_audition\) api\.live_audition\(st, ptrL, ptrR, ptrOL, ptrOR, k\);\r?\n\s*else api\.live_stereo\(st, ptrL, ptrR, ptrOL, ptrOR, k\);/);
  const body = posted(freshState());
  assert.equal(body.audition_strip, undefined);
  assert.equal(body.audition, undefined);
  ENGINE_KEYS.forEach(function (k) {
    assert.equal(Object.prototype.hasOwnProperty.call(body, k), false, k);
  });
  assert.deepEqual(R.masterScene(freshState()), {});
  assert.deepEqual(R.renderScene(freshState()), {});

  const state = freshState();
  const before = JSON.stringify(state);
  const keys = posted(state);
  const ui = desk();
  const api = loadAud(state, ui.document);
  api.bindRouting();
  api.paintRouting();
  assert.equal(ui.els.auditionStrip.checked, false);
  assert.equal(api.on(), false);
  ui.els.auditionStrip.checked = true;
  ui.fire(ui.els.auditionStrip, "change");
  assert.equal(api.on(), true);
  assert.equal(JSON.stringify(state), before);
  assert.equal(JSON.stringify(state).includes("audition"), false);
  assert.deepEqual(posted(state), keys);
  assert.ok(api.posts.n > 0);
  ui.els.auditionStrip.checked = false;
  ui.fire(ui.els.auditionStrip, "change");
  api.clearPreamp();
  assert.equal(api.on(), false);
  assert.equal(ui.els.auditionStrip.checked, false);
  assert.deepEqual(posted(state), keys);
  assert.equal(JSON.stringify(state), before);
});
