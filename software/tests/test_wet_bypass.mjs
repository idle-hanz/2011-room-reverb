// node --test test_wet_bypass.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");
const app = fs.readFileSync(path.join(here, "../static/js/app.js"), "utf8");

function loadApply() {
  const start = app.indexOf("function applyWetBypass");
  const end = app.indexOf("function heardMix", start);
  assert.ok(start > 0 && end > start);
  return new Function(app.slice(start, end) + "\nreturn applyWetBypass;")();
}

test("the mix desk has one Bypass button and no routing or host fader", () => {
  assert.match(page, /id="wetBypass" aria-pressed="false"/);
  assert.doesNotMatch(page, /id="routingPanel"/);
  assert.doesNotMatch(page, /id="fader_dry"/);
  assert.match(page, /<option value="BYPASS">Bypass<\/option>/);
  assert.match(page, /app\.js\?v=90/);
  assert.match(app, /applyWetBypass\(o, wetBypass\)/);
  assert.doesNotMatch(app, /stripLinear\(src, "dry"\)/);
});

test("Bypass off posts dry_gain 0 and on posts dry 1 with the three wet gains at 0", () => {
  const applyWetBypass = loadApply();
  const off = applyWetBypass({
    dry_gain: 0.4, direct_wet: 0.2, fdn_wet: 1, early_wet: 0.5, fader_dry: 1,
  }, false);
  assert.equal(off.dry_gain, 0);
  assert.equal(off.direct_wet, 0.2);
  assert.equal(off.fdn_wet, 1);
  assert.equal(off.early_wet, 0.5);
  const on = applyWetBypass({
    dry_gain: 0, direct_wet: 0.2, fdn_wet: 1, early_wet: 0.5,
  }, true);
  assert.equal(on.dry_gain, 1);
  assert.equal(on.direct_wet, 0);
  assert.equal(on.fdn_wet, 0);
  assert.equal(on.early_wet, 0);
});
