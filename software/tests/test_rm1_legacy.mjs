// node --test test_rm1_legacy.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");
const mix = fs.readFileSync(path.join(here, "../static/js/rr_mix.js"), "utf8");
const settings = fs.readFileSync(path.join(here, "../static/js/rr_settings.js"), "utf8");

const REQUIRED = [
  "route_array_pre", "route_array_drive", "route_array_comp", "route_array_amount",
  "route_room_pre", "route_room_drive", "route_room_comp", "route_room_amount",
  "route_master_pre", "route_master_drive", "route_master_comp", "route_master_amount",
  "bloom_on", "bloom_menu", "bloom_amount_ui", "bloom_colour_ui", "glue_colour_ui",
  "pre_drive_ui", "predelay_ui", "bloom_attack_ui", "bloom_release_ui",
  "bloom_preset", "bloom_amount", "bloom_colour", "glue_colour",
  "pre_colour", "pre_drive_db", "predelay_ms",
  "bloom_attack_scale", "bloom_release_scale",
  "array_preset", "array_amount", "array_pre", "array_drive_db",
  "room_preset", "room_amount", "room_pre", "room_drive_db",
];

function loadApi() {
  const mixStart = mix.indexOf("var LEGACY_ROUTE_KEYS");
  const heard = mix.indexOf("function heardMix");
  const mixEnd = mix.indexOf("function applyTreatAmount", heard);
  const setupStart = settings.indexOf("function applySetupObject");
  const setupEnd = settings.indexOf("function armSetupSave", setupStart);
  assert.ok(mixStart > 0 && mixEnd > mixStart);
  assert.ok(setupStart > 0 && setupEnd > setupStart);
  return new Function(`
    var state = {};
    var colourSurfaces = null;
    var window = {};
    function migrateRoomState(s) { return s; }
    function syncUI() {}
    var SOLO_BUSES = [];
    function stripLinear() { return 1; }
    function micLinear() { return 1; }
    function splitOn() { return false; }
    function roomSpotOf() { return { x: 0, y: 0, z: 0, yaw: 0 }; }
    function applyTreatAmount(o) { return o; }
    function applyTreatDecay(o) { return o; }
    function applyWetBypass(o) { return o; }
    var wetBypass = false;
    ${mix.slice(mixStart, mixEnd)}
    ${settings.slice(setupStart, setupEnd)}
    return { stripLegacyRoute: stripLegacyRoute, heardMix: heardMix, applySetupObject: applySetupObject, LEGACY_ROUTE_KEYS: LEGACY_ROUTE_KEYS, state: state };
  `)();
}

function armedSetup() {
  const src = { fdn_g: 1, place_c: "room", spare_off: true, W: 12, fdn_wet: 0.5 };
  REQUIRED.forEach(function (key) {
    if (key.indexOf("colour") >= 0 || key === "bloom_on") src[key] = true;
    else if (
      key.indexOf("amount") >= 0 || key.indexOf("drive") >= 0 ||
      key.indexOf("predelay") >= 0 || key.indexOf("scale") >= 0 || key.slice(-3) === "_ui"
    ) src[key] = 100;
    else if (key.indexOf("_pre") >= 0) src[key] = "neve1073";
    else src[key] = "nuke";
  });
  return src;
}

test("the page has no routing panel and no audition strip", () => {
  ["routingPanel", "auditionStrip", "route_array_pre", "route_room_pre", "route_master_pre"].forEach(function (id) {
    assert.equal(page.includes('id="' + id + '"'), false, id);
  });
  assert.doesNotMatch(page, /routing-panel|routing-note|routing_scene\.js/);
});

test("a setup with the old keys loads, posts, and saves without them", () => {
  const api = loadApi();
  REQUIRED.forEach(function (key) {
    assert.ok(api.LEGACY_ROUTE_KEYS.indexOf(key) >= 0, key);
  });
  const src = armedSetup();
  const posted = api.heardMix(src);
  REQUIRED.forEach(function (key) {
    assert.equal(Object.prototype.hasOwnProperty.call(posted, key), false, key);
  });
  assert.equal(posted.place_c, "room");
  assert.equal(posted.fdn_g, 1);
  assert.equal(Object.prototype.hasOwnProperty.call(posted, "spare_off"), false);

  const data = armedSetup();
  api.state.bloom_preset = "glue";
  api.state.route_array_pre = "u610a";
  assert.equal(api.applySetupObject(data), true);
  REQUIRED.forEach(function (key) {
    assert.equal(Object.prototype.hasOwnProperty.call(api.state, key), false, key);
    assert.equal(Object.prototype.hasOwnProperty.call(data, key), false, key);
  });
  assert.equal(api.state.W, 12);
  assert.equal(api.state.fdn_wet, 0.5);
  assert.equal(api.state.place_c, "room");

  const saved = { W: 4, place_l: "array", bloom_preset: "room_crush", route_master_amount: 40 };
  api.stripLegacyRoute(saved);
  const raw = JSON.stringify(saved);
  assert.equal(raw.includes("bloom_preset"), false);
  assert.equal(raw.includes("route_master_amount"), false);
  assert.equal(saved.W, 4);
  assert.equal(saved.place_l, "array");

  const saveSrc = settings.slice(
    settings.indexOf("function scheduleSetupSave"),
    settings.indexOf("function applySetupObject")
  );
  const downloadSrc = settings.slice(
    settings.indexOf("function downloadSetup"),
    settings.indexOf("function loadServerDefaults")
  );
  assert.ok(saveSrc.indexOf("stripLegacyRoute(state)") >= 0);
  assert.ok(saveSrc.indexOf("stripLegacyRoute(state)") < saveSrc.indexOf("JSON.stringify(state)"));
  assert.ok(downloadSrc.indexOf("stripLegacyRoute(state)") >= 0);
  assert.ok(downloadSrc.indexOf("stripLegacyRoute(state)") < downloadSrc.indexOf("JSON.stringify(state"));
  const loadSrc = settings.slice(
    settings.indexOf("function applySetupObject"),
    settings.indexOf("function armSetupSave")
  );
  assert.ok(loadSrc.indexOf("stripLegacyRoute(data)") < loadSrc.indexOf("state[k] = data[k]"));
});
