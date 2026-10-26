// The page keeps a solo make-up until the letter changes.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.join(here, "../static/js/live_fdn.js"), "utf8");
const start = src.indexOf("function soloMatchHold(");
const end = src.indexOf("function formatSoloMatch(", start);
assert.ok(start > 0 && end > start);
const soloMatchHold = new Function(
  "prev",
  "letter",
  "enabled",
  "measured",
  src.slice(start, end) + "\nreturn soloMatchHold(prev, letter, enabled, measured);"
);

test("a solo letter keeps its gain when the measurement moves", () => {
  const first = soloMatchHold(null, "A", true, 2.5);
  assert.equal(first.letter, "A");
  assert.equal(first.gain, 2.5);
  const held = soloMatchHold(first, "A", true, 9);
  assert.equal(held.gain, 2.5);
  const next = soloMatchHold(held, "C", true, 4);
  assert.equal(next.letter, "C");
  assert.equal(next.gain, 4);
});

test("no solo and the switch off are unity", () => {
  assert.deepEqual(soloMatchHold({ letter: "A", gain: 2 }, null, true, 2), { letter: null, gain: 1 });
  assert.deepEqual(soloMatchHold({ letter: "A", gain: 2 }, "A", false, 2), { letter: null, gain: 1 });
});

test("the gain caps at +24 dB", () => {
  const cap = Math.pow(10, 24 / 20);
  const got = soloMatchHold(null, "B", true, 100);
  assert.ok(Math.abs(got.gain - cap) < 1e-9);
});
