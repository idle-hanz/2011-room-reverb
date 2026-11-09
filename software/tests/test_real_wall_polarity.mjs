// Real-wall polarity. Unticked posts and saves nothing. Ticked stores true.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");
const mix = fs.readFileSync(path.join(here, "../static/js/rr_mix.js"), "utf8");
const settings = fs.readFileSync(path.join(here, "../static/js/rr_settings.js"), "utf8");
const app = fs.readFileSync(path.join(here, "../static/js/app.js"), "utf8");
const stateJs = fs.readFileSync(path.join(here, "../static/js/rr_state.js"), "utf8");

const TIP = "Off: reflections flip per bounce, which sounds smoother. On: real hard walls, which sounds more resonant.";

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
    return { heardMix: heardMix, applySetupObject: applySetupObject, state: state };
  `)();
}

test("the early-field tick is unticked and explains both sides", () => {
  assert.match(page, /id="real_wall_polarity"(?! checked)/);
  assert.match(page, /Real-wall polarity \(no flip\)/);
  assert.match(page, new RegExp("title=\"" + TIP.replace(/[.]/g, "\\.") + "\""));
  assert.equal(stateJs.includes('S("real_wall_polarity")'), false);
  assert.match(app, /state\.real_wall_polarity = true/);
  assert.match(app, /delete state\.real_wall_polarity/);
  assert.match(settings, /omitRealWall\(state\)/);
});

test("unticked posts and loads nothing, ticked keeps true", () => {
  const api = loadApi();
  const off = api.heardMix({ W: 6 });
  assert.equal(Object.prototype.hasOwnProperty.call(off, "real_wall_polarity"), false);
  const explicit = api.heardMix({ W: 6, real_wall_polarity: false });
  assert.equal(Object.prototype.hasOwnProperty.call(explicit, "real_wall_polarity"), false);
  const on = api.heardMix({ W: 6, real_wall_polarity: true });
  assert.equal(on.real_wall_polarity, true);

  api.state.real_wall_polarity = true;
  api.applySetupObject({ W: 6, room_shape: "box", real_wall_polarity: false });
  assert.equal(Object.prototype.hasOwnProperty.call(api.state, "real_wall_polarity"), false);
  api.applySetupObject({ W: 6, room_shape: "box", real_wall_polarity: true });
  assert.equal(api.state.real_wall_polarity, true);
  api.applySetupObject({ W: 6, room_shape: "box" });
  assert.equal(Object.prototype.hasOwnProperty.call(api.state, "real_wall_polarity"), false);
});
