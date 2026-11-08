// Room + Source tab. Display readout only. The drag still uses the floor pointer path.
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
const transport = readFileSync(join(software, "static/js/rr_transport.js"), "utf8");
const editor = readFileSync(join(software, "static/js/room_editor.js"), "utf8");
const state = readFileSync(join(software, "static/js/rr_state.js"), "utf8");

test("room size box keeps the source control ids and the room tab", () => {
  assert.match(page, /id="roomBoxToggle"/);
  assert.match(page, /id="roomSizeBox"/);
  assert.match(page, /id="roomSourceBox"/);
  assert.match(page, /id="sourcePreset"/);
  assert.match(page, /id="sourceYaw"/);
  assert.match(page, /id="sourcePitch"/);
  assert.match(page, /id="sourceSize"/);
  assert.doesNotMatch(page, /data-view="source"/);
  assert.match(page, /id="floorFrame"[\s\S]*class="diagram-expand"/);
  assert.match(page, /id="view3dFrame"[\s\S]*class="diagram-expand"/);
  assert.match(state, /var roomBoxMode = "size"/);
});

test("3D readout is distance, angle, height, 1/r level and delay", () => {
  const row = RD.micReadout({ x: 0, y: 1.2, z: 0 }, { x: 0, y: 1.2, z: 3.4 }, 340);
  assert.ok(Math.abs(row.dist_m - 3.4) < 1e-9);
  assert.ok(Math.abs(row.delay_ms - 10) < 1e-9);
  assert.ok(Math.abs(row.height_m - 1.2) < 1e-9);
  assert.ok(Math.abs(row.angle_deg - 0) < 1e-9);
  const db = 20 * Math.log(1 / 3.4) / Math.LN10;
  assert.ok(Math.abs(row.level_db - db) < 1e-9);
  const text = RD.formatMicReadout("C", row);
  assert.match(text, /10\.0 ms/);
  assert.match(text, /dB/);
  assert.match(text, /h 1\.20 m/);
  assert.match(transport, /RoomDraw\.micReadout/);
  assert.match(transport, /window\.RoomDraw/);
  assert.doesNotMatch(transport, /global\.RoomDraw/);
  assert.match(transport, /liveMetres3d\.textContent/);
  assert.doesNotMatch(transport, /state\.readout/);
});

test("badges, arrival gain and the enlarged heat map stay on 1/r", () => {
  assert.equal(RD.sourceBadge(0, 0, true), "");
  assert.equal(RD.sourceBadge(40, -3, false), "off-axis");
  assert.equal(RD.sourceBadge(40, -24, false), "null");
  assert.equal(RD.sourceBadge(0, -3, false), "");
  const rev = RD.reverbDistance([2, 4]);
  assert.ok(Math.abs(rev - (1 / (1 / 2 + 1 / 4))) < 1e-9);
  const drr = RD.drrDb(2, 4);
  assert.ok(Math.abs(drr - (20 * Math.log(4 / 2) / Math.LN10)) < 1e-6);
  assert.ok(RD.arrivalGain(0, 0.5) === 0.5);
  assert.match(editor, /is-enlarged/);
  assert.match(editor, /RoomDraw\.drrDb/);
  assert.doesNotMatch(editor, /drawHeat[\s\S]{0,800}fetch\(/);
});
