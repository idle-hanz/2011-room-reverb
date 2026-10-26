// node --test test_pair_mode.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { appSource as app } from "./app_sources.mjs";

const require = createRequire(import.meta.url);
const Pair = require("../static/js/pair_mode.js");
const MS = require("../static/js/ms_presets.js");

function dbTravelGain(travel) {
  /* Fader 0.5 is 0 dB. The pair test stays on that knot. */
  assert.equal(travel, 0.5);
  return 1;
}

/* Same signs as app.js micLinear + deskWeights, linear law, pan −1 / 0 / +1. */
function weights(src) {
  function mic(key) {
    if (src["mute_" + key]) return 0;
    const route = String(src["mic_route_" + key] || "pan");
    const fader = dbTravelGain(src["fader_" + key]);
    if (route === "s") return Math.pow(10, Number(src["width_" + key] || 0) / 20) * fader;
    if (src["gain_exact_" + key] != null && Number.isFinite(Number(src["gain_exact_" + key]))) {
      return Number(src["gain_exact_" + key]) * fader;
    }
    return fader;
  }
  function pair(route, g, pan) {
    route = String(route || "pan");
    if (route === "centre") return [g * 0.5, g * 0.5];
    if (route === "both") return [g, g];
    if (route === "l") return [g, 0];
    if (route === "r") return [0, g];
    if (route === "s") return [g, -g];
    const t = (Number(pan) + 1) * 0.5;
    return [g * (1 - t), g * t];
  }
  const L = pair(src.mic_route_l, mic("l"), src.pan_l);
  const C = pair(src.mic_route_c, src.third_mic === "off" ? 0 : mic("c"), src.pan_c);
  const R = pair(src.mic_route_r, mic("r"), src.pan_r);
  return [L[0], L[1], C[0], C[1], R[0], R[1]];
}

function xy() {
  return {
    pair_mode: "stereo", stereo_mic: false, ms_decode: false,
    ms_s: "l", ms_m: "c", s_detached: false,
    third_mic: "centre", place_l: "array", place_c: "array", place_r: "array",
    mic_route_l: "pan", mic_route_c: "pan", mic_route_r: "pan",
    width_l: 0, width_c: 0, width_r: 0,
    gain_exact_l: null, gain_exact_c: null, gain_exact_r: null,
    mute_l: false, mute_c: false, mute_r: false,
    phase_l: 1, phase_c: 1, phase_r: 1,
    pan_l: -1, pan_c: 0, pan_r: 1,
    yaw_l_deg: -45, yaw_c_deg: 0, yaw_r_deg: 45,
    pattern_l: "cardioid", pattern_c: "cardioid", pattern_r: "cardioid",
    family_l: "cardioid", family_c: "cardioid", family_r: "cardioid",
    polar_l: 0.5, polar_c: 0.5, polar_r: 0.5,
    mic_preset_l: "NeumannU87AiCardioid",
    mic_preset_c: "NeumannU87AiCardioid",
    mic_preset_r: "NeumannU87AiCardioid",
    fader_l: 0.5, fader_c: 0.5, fader_r: 0.5,
    trim_l: 0, trim_r: 0,
    space: 0.01
  };
}

const G = Math.pow(10, -3 / 20);

test("Stereo gangs aim, pattern, and gain and leaves the routes", () => {
  const s = xy();
  s.yaw_l_deg = -30;
  s.yaw_r_deg = 10;
  s.pattern_r = "omni";
  s.family_r = "cardioid";
  s.polar_r = 0;
  s.fader_l = 0.5;
  s.fader_r = 0.2;
  s.mic_route_c = "centre";
  const before = weights(Object.assign({}, s, { fader_r: 0.5, pattern_r: "cardioid", polar_r: 0.5 }));
  const out = Pair.step(s, "stereo", null, MS.build("ms_b"));
  assert.equal(out.posts, 1);
  assert.equal(s.pair_mode, "stereo");
  assert.equal(s.link_mode, "mirror");
  assert.equal(s.link_lr_yaw, true);
  assert.equal(s.yaw_r_deg, 30);
  assert.equal(s.pattern_r, "cardioid");
  assert.equal(s.family_r, s.family_l);
  assert.equal(s.polar_r, s.polar_l);
  assert.equal(s.fader_r, s.fader_l);
  assert.equal(s.mic_preset_r, s.mic_preset_l);
  assert.equal(s.mic_route_c, "centre");
  assert.equal(s.space, 0.01);
  Pair.follow(s, "l", { fader: 0.5, yaw: -12, family: "bi", polar: 0.5, pattern: "fig8" });
  assert.equal(s.fader_r, 0.5);
  assert.equal(s.yaw_r_deg, 12);
  assert.equal(s.family_r, "bi");
  assert.equal(s.pattern_r, "fig8");
  assert.deepEqual(weights(s).slice(0, 2), before.slice(0, 2));
});

test("Independent does not gang and does not rewrite routes", () => {
  const s = xy();
  s.mic_route_l = "l";
  s.fader_r = 0.2;
  s.yaw_r_deg = 10;
  const out = Pair.step(s, "independent", null, MS.build("ms_b"));
  assert.equal(out.posts, 1);
  assert.equal(s.pair_mode, "independent");
  assert.equal(s.link_mode, "split");
  assert.equal(s.link_lr_yaw, false);
  assert.equal(s.mic_route_l, "l");
  assert.equal(s.fader_r, 0.2);
  assert.equal(s.yaw_r_deg, 10);
  Pair.follow(s, "l", { fader: 0.5, yaw: -5 });
  assert.equal(s.fader_r, 0.2);
  assert.equal(s.yaw_r_deg, 10);
  assert.equal(s.yaw_l_deg, -5);
  const again = Pair.step(s, "independent", out.stash, MS.build("ms_b"));
  assert.equal(again.posts, 0);
});

test("M/S posts the ms_b weights with the side at 90, and Stereo restores the routes", () => {
  const s = xy();
  s.third_mic = "off";
  s.mic_route_c = "centre";
  s.space = 0.17;
  const folded = weights(xy());
  const out = Pair.step(s, "ms", null, MS.build("ms_b"));
  assert.equal(out.posts, 1);
  assert.equal(s.pair_mode, "ms");
  assert.equal(s.mic_route_l, "s");
  assert.equal(s.mic_route_c, "both");
  assert.equal(s.mute_r, true);
  assert.equal(s.yaw_l_deg, 90);
  assert.equal(s.yaw_c_deg, 0);
  assert.equal(s.family_l, "bi");
  assert.equal(s.pattern_c, "cardioid");
  assert.equal(s.third_mic, "centre");
  assert.equal(s.space, 0.17);
  const w = weights(s);
  assert.ok(Math.abs(w[0] - G) < 1e-12);
  assert.ok(Math.abs(w[1] + G) < 1e-12);
  assert.ok(Math.abs(w[2] - G) < 1e-12);
  assert.ok(Math.abs(w[3] - G) < 1e-12);
  assert.equal(w[4], 0);
  assert.equal(w[5], 0);
  assert.notDeepEqual(w.map((n) => Math.round(n * 1e6)), folded.map((n) => Math.round(n * 1e6)));
  const back = Pair.step(s, "stereo", out.stash, MS.build("ms_b"));
  assert.equal(back.posts, 1);
  assert.equal(back.stash, null);
  assert.equal(s.pair_mode, "stereo");
  assert.equal(s.mic_route_l, "pan");
  assert.equal(s.mic_route_c, "centre");
  assert.equal(s.mic_route_r, "pan");
  assert.equal(s.third_mic, "off");
  assert.equal(s.yaw_l_deg, -45);
  assert.equal(s.mute_r, false);
  assert.equal(s.yaw_r_deg, 45);
  assert.equal(weights(Object.assign({}, s, { third_mic: "centre" }))[2], 0.5);
});

test("saved link modes map onto Stereo and Independent and keep the yaws", () => {
  const linked = xy();
  linked.link_mode = "linked";
  linked.pair_mode = "independent";
  linked.yaw_l_deg = -20;
  linked.yaw_r_deg = 40;
  linked.fader_r = 0.2;
  Pair.mapSaved(linked);
  assert.equal(linked.link_mode, "mirror");
  assert.equal(linked.pair_mode, "stereo");
  assert.equal(linked.yaw_l_deg, -20);
  assert.equal(linked.yaw_r_deg, 40);
  assert.equal(linked.fader_r, 0.2);
  const split = xy();
  split.link_mode = "independent";
  split.pair_mode = "stereo";
  split.yaw_r_deg = 10;
  Pair.mapSaved(split);
  assert.equal(split.link_mode, "split");
  assert.equal(split.pair_mode, "independent");
  assert.equal(split.yaw_r_deg, 10);
  const ms = xy();
  ms.pair_mode = "ms";
  ms.link_mode = "linked";
  ms.yaw_l_deg = 90;
  Pair.mapSaved(ms);
  assert.equal(ms.pair_mode, "ms");
  assert.equal(ms.link_mode, "mirror");
  assert.equal(ms.yaw_l_deg, 90);
});

test("the third mic row reads None, Centre, and Room mic", () => {
  const page = fs.readFileSync(
    path.join(path.dirname(fileURLToPath(import.meta.url)), "../static/index.html"),
    "utf8"
  );
  assert.match(page, /aria-label="3rd mic"/);
  assert.match(page, /data-third="off"[^>]*>3rd mic: None</);
  assert.match(page, /data-third="centre"[^>]*>3rd mic: Centre</);
  assert.match(page, /data-third="room"[^>]*>3rd mic: Room mic</);
  assert.doesNotMatch(page, /id="mic_proximity"/);
  assert.match(app, /mic_proximity: 0\.25/);
});
