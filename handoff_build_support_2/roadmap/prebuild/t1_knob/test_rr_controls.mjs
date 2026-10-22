// node --test test_rr_controls.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const C = createRequire(import.meta.url)("./rr_controls.js");
const trim = { min: -12, max: 12, step: 0.5, pxFull: 180, detents: [0], kind: "db" };
const pan = { min: -1, max: 1, step: 0.01, pxFull: 200, detents: [0], kind: "pan" };
const width = { min: -24, max: 24, step: 0.1, pxFull: 240, detents: [0], kind: "db" };

test("full range = pxFull pixels (coarse)", () => {
  assert.equal(C.dragValue(-12, 180, trim, false), 12);
  assert.equal(C.dragValue(0, -90, trim, false), -12 + 0);
});
test("Shift = 10x finer", () => {
  assert.ok(Math.abs(C.dragValue(0, 180, trim, true) - 2.4) < 1e-9);
});
test("snap respects step and clamps", () => {
  assert.equal(C.snap(3.26, trim), 3.5);
  assert.equal(C.snap(99, trim), 12);
  assert.equal(C.snap(-0.333, pan), -0.33);
  assert.equal(C.snap(1.23456, width), 1.2);
});
test("detent at 0 holds within 6 px and releases after", () => {
  // trim: 180 px / 24 dB = 7.5 px per dB; 6 px = 0.8 dB
  assert.deepEqual(C.applyDetent(0.7, trim, false), { value: 0, held: true });
  assert.equal(C.applyDetent(0.9, trim, false).held, false);
  // fine mode: 75 px per dB, so hold zone shrinks to 0.08 dB
  assert.equal(C.applyDetent(0.1, trim, true).held, false);
  assert.equal(C.applyDetent(0.05, trim, true).held, true);
});
test("wheel steps one step, Shift a tenth", () => {
  assert.equal(C.wheelValue(0, -1, trim, false), 0.5);
  assert.equal(C.wheelValue(0, 1, trim, false), -0.5);
  assert.ok(Math.abs(C.wheelValue(0, -1, trim, true) - 0.05) < 1e-12);
});
test("typing: numbers, units, unicode minus, pan words", () => {
  assert.equal(C.parseTyped("-4 dB", trim), -4);
  assert.equal(C.parseTyped("\u22126", trim), -6);
  assert.equal(C.parseTyped("+1,5", trim), 1.5);
  assert.equal(C.parseTyped("C", pan), 0);
  assert.equal(C.parseTyped("L30", pan), -0.3);
  assert.equal(C.parseTyped("r 100", pan), 1);
  assert.equal(C.parseTyped("50 cm", { min: 0, max: 10 }), 0.5);
  assert.equal(C.parseTyped("120 ms", { min: 0, max: 8, unit: "s" }), 0.12);
  assert.ok(Number.isNaN(C.parseTyped("abc", trim)));
  assert.ok(Number.isNaN(C.parseTyped("", trim)));
});
test("format: dB sign, pan L/C/R", () => {
  assert.equal(C.formatValue(3, trim), "+3.0");
  assert.equal(C.formatValue(-0.001, pan), "C");
  assert.equal(C.formatValue(-0.3, pan), "L30");
  assert.equal(C.formatValue(1, pan), "R100");
});
test("needle covers -140..+140 deg (fixes B2 for width)", () => {
  assert.equal(C.needleDeg(-24, width), -140);
  assert.equal(C.needleDeg(0, width), 0);
  assert.equal(C.needleDeg(24, width), 140);
});
