// node --test test_mix_labels.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");
const app = fs.readFileSync(path.join(here, "../static/js/app.js"), "utf8");

test("the three Mix checks keep their names and carry the short labels", () => {
  assert.match(page, /id="phys_ceiling" checked/);
  assert.match(page, /id="sub_hp" checked/);
  assert.match(page, /id="offaxis_tail"(?! checked)/);
  assert.match(page, /Physical ceiling<\/span>\s*<span>Room limits the tail<\/span>/);
  assert.match(page, /Rumble filter<\/span>\s*<span>15 Hz rumble cut<\/span>/);
  assert.match(page, /Off-axis tail<\/span>\s*<span>Darken the tail<\/span>/);
  assert.match(page, /title="Caps the tail at what a real room with these materials could produce\."/);
  assert.match(page, /title="A 15 Hz high-pass on the tail only\. The direct sound and the early reflections stay as they are\."/);
  assert.match(page, /title="Darkens the 8–16 kHz part of the tail\. The direct sound and the early reflections stay untouched\. Starts off\."/);
  assert.match(page, /app\.js\?v=93/);
});

test("the physical readout no longer says off with two sources", () => {
  assert.doesNotMatch(app, /off with two sources/);
});
