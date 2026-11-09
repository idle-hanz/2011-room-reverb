// Space tab: lattice toggle and path cycle. Display rules only.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const software = join(here, "..");
const RD = require("../static/js/room_draw.js");
const page = readFileSync(join(software, "static/index.html"), "utf8");
const views = readFileSync(join(software, "static/js/image_views.js"), "utf8");
const space = readFileSync(join(software, "static/js/rr_space.js"), "utf8");
const state = readFileSync(join(software, "static/js/rr_state.js"), "utf8");

test("lattice stays a toggle and last legs is not a separate chip", () => {
  assert.match(page, /id="spaceLatticeBtn"/);
  assert.match(page, /id="spacePathsBtn"/);
  assert.match(page, /id="spaceOrderBtn"/);
  assert.match(page, /data-path-mic="L"/);
  assert.match(page, /data-path-mic="R"/);
  assert.match(page, /data-path-mic="C"/);
  assert.match(page, /data-path-mic="all"/);
  assert.doesNotMatch(page, /data-space-mode="legs"/);
  assert.doesNotMatch(page, /Last legs/);
  assert.match(state, /var spaceLattice = true/);
  assert.match(state, /var spacePaths = 0/);
  assert.match(state, /var spaceOrder = 0/);
  assert.match(state, /var spacePathMic = "all"/);
  assert.doesNotMatch(state, /spaceMode/);
});

test("the view posts no new audio keys", () => {
  assert.match(space, /imageView\.setSpace\(/);
  assert.match(space, /paths: spacePaths/);
  assert.doesNotMatch(space, /paths: roomDiagram === "paths" \? spacePaths : 0/);
  assert.match(space, /heardMix\(state\)/);
  assert.doesNotMatch(space, /WORKLET_VER/);
  assert.match(views, /setSpace: function/);
  assert.match(views, /RoomDraw\.pathHover/);
  assert.match(views, /RoomDraw\.latticeKeys\(env\.mode/);
  assert.match(views, /mode !== "lattice" && key !== "a:home"/);
});

test("path filters keep the default picture and follow solo and mute", () => {
  assert.deepEqual(RD.pathMics(["L", "R"], "all"), ["L", "R"]);
  assert.deepEqual(RD.pathMics(["L", "R"], "L"), ["L"]);
  assert.deepEqual(RD.pathMics(["L", "R"], "C"), []);
  assert.deepEqual(RD.pathMics(["L", "C", "R"], "centre"), ["C"]);
  assert.equal(RD.orderShown(0, 1, true), true);
  assert.equal(RD.orderShown(1, 1, false), true);
  assert.equal(RD.orderShown(2, 1, false), false);
  assert.equal(RD.orderShown(4, 0, false), true);
  assert.equal(RD.surfaceShown([], "A", { B: true }), true);
  assert.equal(RD.surfaceShown(["A", "F"], "A", { F: true }), true);
  assert.equal(RD.surfaceShown(["B"], "A", {}), false);
  assert.equal(RD.surfaceShown(["A", "B"], null, { B: true }), false);
  assert.equal(RD.surfaceShown(["A"], null, { B: true }), true);
  assert.equal(RD.pathOpacity(2, true), 0.95);
  const near = RD.pathOpacity(2, false);
  const far = RD.pathOpacity(20, false);
  assert.ok(near > far);
  assert.ok(far >= 0.12 && near <= 0.9);
  const tip = RD.pathHover({
    order: 1, is_direct: false, delay_ms: 12.34, dist_m: 2, hit_surfaces: ["A", "F"], mic: "L"
  });
  assert.match(tip, /12\.3 ms/);
  assert.match(tip, /A F/);
  assert.match(tip, /dB/);
  assert.match(tip, /mic L/);
});

test("hiding the lattice still keeps only the home shell", () => {
  assert.deepEqual(
    RD.latticeKeys("lattice", ["a:home", "a:1", "b:home"]),
    ["a:home", "a:1", "b:home"]
  );
  assert.deepEqual(
    RD.latticeKeys("paths", ["a:home", "a:1", "b:2.3", "b:home"]),
    ["a:home", "b:home"]
  );
});
