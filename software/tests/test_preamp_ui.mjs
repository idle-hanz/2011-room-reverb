// PREAMP-UI1. Routing strips, defaults off, and the engine param each control posts.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { appSource as app } from "./app_sources.mjs";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const R = require("../static/js/routing_scene.js");
const page = readFileSync(join(here, "../static/index.html"), "utf8");
const settings = JSON.parse(readFileSync(join(here, "../static/settings.json"), "utf8"));

const STRIPS = ["array", "room", "master"];
const PRE = ["none", "u610a", "neve1073"];
const PRE_LABEL = ["Off", "610-A", "Neve"];
const COMP = ["off", "natural", "glue", "room_crush", "nuke", "swell"];
const COMP_LABEL = ["Off", "Natural", "Glue", "Room Crush", "Nuke", "Swell"];
const ENGINE = {
  array: { pre: "array_pre", drive: "array_drive_db", comp: "array_preset", amount: "array_amount" },
  room: { pre: "room_pre", drive: "room_drive_db", comp: "room_preset", amount: "room_amount" },
  master: { pre: "pre_colour", drive: "pre_drive_db", comp: "bloom_preset", amount: "bloom_amount" }
};
const ENGINE_KEYS = [
  "bloom_preset", "bloom_amount", "bloom_colour", "glue_colour",
  "pre_colour", "pre_drive_db", "predelay_ms",
  "bloom_attack_scale", "bloom_release_scale",
  "array_preset", "array_amount", "array_pre", "array_drive_db",
  "room_preset", "room_amount", "room_pre", "room_drive_db"
];

function freshState() {
  const state = {};
  STRIPS.forEach(function (name) {
    state["route_" + name + "_pre"] = "none";
    state["route_" + name + "_drive"] = 0;
    state["route_" + name + "_comp"] = "off";
    state["route_" + name + "_amount"] = 0;
  });
  return state;
}

function makeEl(id, value) {
  return {
    id: id,
    value: String(value),
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
  STRIPS.forEach(function (name) {
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

function loadUi(state, document) {
  const start = app.indexOf("function clearPreamp");
  const end = app.indexOf("function paintDesk", start);
  assert.ok(start > 0 && end > start);
  const posts = { n: 0 };
  const api = {};
  const fn = new Function(
    "state", "document", "window", "RRRouting", "syncUI", "scheduleLiveParams",
    app.slice(start, end) + "\nreturn { clearPreamp: clearPreamp, paintRouting: paintRouting, bindRouting: bindRouting };"
  );
  const out = fn(
    state,
    document,
    { RRRouting: R },
    R,
    function () { api.paintRouting(); },
    function () { posts.n += 1; }
  );
  api.paintRouting = out.paintRouting;
  api.bindRouting = out.bindRouting;
  api.clearPreamp = out.clearPreamp;
  api.posts = posts;
  return api;
}

function posted(src) {
  const start = app.indexOf("/* Play posts the master strip");
  const end = app.indexOf("applyTreatAmount(o);", start);
  assert.ok(start > 0 && end > start);
  const call = new Function("o", "src", "window", "RRRouting", app.slice(start, end) + "\nreturn o;");
  return call(Object.assign({}, src), src, { RRRouting: R }, R);
}

function engineOf(body) {
  const out = {};
  ENGINE_KEYS.forEach(function (k) {
    if (Object.prototype.hasOwnProperty.call(body, k)) out[k] = body[k];
  });
  return out;
}

function stripChunk(name) {
  const id = 'id="route_' + name + '_pre"';
  const at = page.indexOf(id);
  assert.ok(at > 0, name);
  return page.slice(at, at + 1600);
}

test("each routing control defaults off and posts its engine param", () => {
  STRIPS.forEach(function (name) {
    const row = settings.by_name;
    assert.equal(row["route_" + name + "_pre"].default, "none");
    assert.equal(row["route_" + name + "_drive"].default, 0);
    assert.equal(row["route_" + name + "_comp"].default, "off");
    assert.equal(row["route_" + name + "_amount"].default, 0);
    const chunk = stripChunk(name);
    PRE.forEach(function (value, i) {
      assert.match(chunk, new RegExp('<option value="' + value + '"' + (i === 0 ? " selected" : "") + ">" + PRE_LABEL[i] + "</option>"));
    });
    COMP.forEach(function (value, i) {
      assert.match(chunk, new RegExp('<option value="' + value + '"' + (i === 0 ? " selected" : "") + ">" + COMP_LABEL[i] + "</option>"));
    });
    assert.match(chunk, new RegExp('id="route_' + name + '_drive" min="0" max="12" step="0.5" value="0"'));
    assert.match(chunk, new RegExp('id="route_' + name + '_amount" min="0" max="100" step="1" value="0"'));
    assert.doesNotMatch(chunk, /talkback/);
  });
  assert.doesNotMatch(page, /value="talkback"/);

  const state = freshState();
  const ui = desk();
  const api = loadUi(state, ui.document);
  api.bindRouting();
  api.paintRouting();
  assert.equal(ui.els.route_master_drive.disabled, true);
  assert.equal(ui.els.route_master_amount.disabled, true);
  assert.equal(ui.els.route_master_drive_out.textContent, "0.0");
  assert.deepEqual(engineOf(posted(state)), {});

  function move(id, value) {
    const el = ui.els[id];
    el.value = String(value);
    ui.fire(el, "change");
  }

  STRIPS.forEach(function (name) {
    const eng = ENGINE[name];
    move("route_" + name + "_pre", "u610a");
    move("route_" + name + "_drive", "6");
    let scene = name === "master" ? R.masterScene(state) : R.renderScene(state);
    assert.equal(scene[eng.pre], "u610a", name);
    assert.equal(scene[eng.drive], 6, name);
    move("route_" + name + "_comp", "glue");
    scene = name === "master" ? R.masterScene(state) : R.renderScene(state);
    assert.equal(state["route_" + name + "_comp"], "glue");
    assert.equal(state["route_" + name + "_amount"], 100);
    assert.equal(scene[eng.comp], "glue", name);
    assert.equal(scene[eng.amount], 100, name);
    assert.ok(api.posts.n > 0);
    move("route_" + name + "_pre", "none");
    move("route_" + name + "_comp", "off");
  });
  assert.deepEqual(R.masterScene(state), {});
  assert.deepEqual(R.renderScene(state), {});
  assert.equal(ui.els.route_array_pre.value, "none");
  assert.equal(ui.els.route_room_comp.value, "off");
});

test("the default scene posts no preamp or compressor keys", () => {
  const before = posted(freshState());
  assert.deepEqual(engineOf(before), {});
  STRIPS.forEach(function (name) {
    assert.equal(before["route_" + name + "_pre"], undefined);
    assert.equal(before["route_" + name + "_comp"], undefined);
  });
  assert.deepEqual(R.masterScene(freshState()), {});
  assert.deepEqual(R.renderScene(freshState()), {});
});

test("preamp and compressor on then off posts the untouched scene", () => {
  const state = freshState();
  const ui = desk();
  const api = loadUi(state, ui.document);
  api.bindRouting();
  const before = posted(freshState());
  STRIPS.forEach(function (name) {
    ui.els["route_" + name + "_pre"].value = "neve1073";
    ui.fire(ui.els["route_" + name + "_pre"], "change");
    ui.els["route_" + name + "_drive"].value = "3";
    ui.fire(ui.els["route_" + name + "_drive"], "input");
    ui.els["route_" + name + "_comp"].value = "room_crush";
    ui.fire(ui.els["route_" + name + "_comp"], "change");
    ui.els["route_" + name + "_pre"].value = "none";
    ui.fire(ui.els["route_" + name + "_pre"], "change");
    ui.els["route_" + name + "_comp"].value = "off";
    ui.fire(ui.els["route_" + name + "_comp"], "change");
  });
  assert.deepEqual(posted(state), before);
  assert.deepEqual(engineOf(posted(state)), {});
});

test("reset and shipped presets load with preamp and compressor off", () => {
  const state = freshState();
  const c0 = app.indexOf("function clearPreamp");
  const c1 = app.indexOf("function paintRouting", c0);
  const r0 = app.indexOf("function resetToFresh");
  const r1 = app.indexOf("function applyDefaultsObject", r0);
  assert.ok(c0 > 0 && r0 > 0 && r1 > r0);
  assert.match(app.slice(r0, r1), /clearPreamp\(\)/);
  const hall0 = app.indexOf("function applyReaktorSnapshot");
  const hall1 = app.indexOf("function snapshotBoot", hall0);
  assert.match(app.slice(hall0, hall1), /clearPreamp\(\)/);
  const load0 = app.indexOf("function loadDeskPreset");
  const load1 = app.indexOf("function deskWeights", load0);
  assert.match(app.slice(load0, load1), /clearPreamp\(\)/);

  const ran = new Function("state", "RRRouting", `
    var bootState = null;
    var hallSnapshot = false;
    var decayFromUser = false;
    var colourSurfaces = null;
    function snapshotBoot() { bootState = JSON.parse(JSON.stringify(state)); }
    function migrateRoomState(s) { if (RRRouting && RRRouting.migrate) RRRouting.migrate(s); return s; }
    ${app.slice(c0, c1)}
    ${app.slice(r0, r1)}
    snapshotBoot();
    state.route_master_pre = "u610a";
    state.route_master_drive = 6;
    state.route_master_comp = "glue";
    state.route_master_amount = 100;
    state.route_array_pre = "neve1073";
    state.route_room_comp = "swell";
    state.route_room_amount = 40;
    resetToFresh();
    return state;
  `)(state, R);
  STRIPS.forEach(function (name) {
    assert.equal(ran["route_" + name + "_pre"], "none");
    assert.equal(ran["route_" + name + "_drive"], 0);
    assert.equal(ran["route_" + name + "_comp"], "off");
    assert.equal(ran["route_" + name + "_amount"], 0);
  });

  const mic = app.slice(app.indexOf("var MIC_PRESETS = {"), app.indexOf("}; /* 2011 / Hall snapshot"));
  assert.doesNotMatch(mic, /pre_colour|bloom_amount|route_master_|route_array_|route_room_|u610a|neve1073/);
  const places = app.slice(app.indexOf("var PLACES = {"), app.indexOf("var bootState"));
  assert.doesNotMatch(places, /pre_colour|bloom_amount|route_master_|route_array_pre|route_room_pre|u610a|neve1073/);
  const ms = readFileSync(join(here, "../static/js/ms_presets.js"), "utf8");
  assert.doesNotMatch(ms, /pre_colour|bloom_amount|route_master_|route_array_|route_room_|u610a|neve1073/);

  const talk = JSON.parse(readFileSync(join(here, "../../handoff_build_support_2/roadmap/bloom/compressor_presets.json"), "utf8"));
  const ids = (talk.bloom_presets || []).map(function (row) { return row.id; });
  assert.ok(ids.indexOf("talkback") >= 0);

  function walk(dir, out) {
    readdirSync(dir).forEach(function (name) {
      const p = join(dir, name);
      if (statSync(p).isDirectory()) walk(p, out);
      else if (name.endsWith(".json")) out.push(p);
    });
  }
  const files = [];
  walk(join(here, "../presets"), files);
  walk(join(here, "../engine/presets"), files);
  const preOn = { u610a: 1, neve1073: 1 };
  files.forEach(function (file) {
    const data = JSON.parse(readFileSync(file, "utf8"));
    function see(obj) {
      if (!obj || typeof obj !== "object") return;
      if (Array.isArray(obj)) {
        obj.forEach(see);
        return;
      }
      Object.keys(obj).forEach(function (k) {
        const v = obj[k];
        if (/^(pre_colour|array_pre|room_pre|route_(array|room|master)_pre)$/.test(k) && preOn[String(v)]) {
          assert.fail(file + " " + k);
        }
        if (/^route_(array|room|master)_comp$/.test(k) && String(v || "off") !== "off") {
          assert.fail(file + " " + k);
        }
        if (/^(bloom_amount|array_amount|room_amount|route_(array|room|master)_amount)$/.test(k) && Number(v) > 0) {
          assert.fail(file + " " + k);
        }
        if (v && typeof v === "object") see(v);
      });
    }
    see(data);
  });
  assert.ok(files.length > 0);
});
