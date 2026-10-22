// node --test test_ms_presets.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const R = createRequire(import.meta.url)("./ms_presets.js");
const close = (a, b, e = 0.05) => assert.ok(Math.abs(a - b) <= e, `${a} vs ${b}`);

test("three presets, b is default, ms_classic aliases b", () => {
  assert.deepEqual(Object.keys(R.PRESETS), ["ms_a", "ms_b", "ms_c"]);
  assert.equal(R.PRESETS.ms_b.isDefault, true);
  assert.equal(R.ALIASES.ms_classic, "ms_b");
  assert.equal(R.build("ms_d"), null);   // (d) dropped (D-UI29)
});
test("preset b = U87 Ai Bidirect S + U87 Ai Cardioid M (D-UI29)", () => {
  const b = R.build("ms_b");
  assert.equal(b.mics.l, "NeumannU87AiBidirect");
  assert.equal(b.mics.c, "NeumannU87AiCardioid");
  assert.equal(b.mic.family_l, "bi");
  assert.equal(b.mic.polar_c, 0.5);
  assert.equal(b.desk.mic_route_l, "s");
  assert.equal(b.desk.mic_route_c, "both");
  assert.equal(b.desk.gain_exact_c, 1.5);
  assert.equal(b.desk.mute_r, true);
});
test("preset b matches today's ms_classic fields (no sound change apart from mic models)", () => {
  // app.js MIC_PRESETS.ms_classic (line 46) and loadDeskPreset ms_classic (403-415)
  const today = { space: 0.05, toe_half_deg: 90, pattern_l: "fig8", pattern_c: "cardioid", family_l: "bi",
    family_c: "cardioid", polar_c: 0.5, yaw_l_deg: 90, yaw_c_deg: 0 };
  const b = R.build("ms_b").mic;
  for (const k in today) assert.equal(b[k], today[k], k);
});
test("preset c: two cardioids back to back, R strip in Ø, both on route s", () => {
  const c = R.build("ms_c");
  assert.equal(c.mic.yaw_l_deg, 90); assert.equal(c.mic.yaw_r_deg, -90);
  assert.equal(c.desk.mic_route_r, "s"); assert.equal(c.desk.phase_r, -1);
  assert.equal(c.desk.mute_r, false);
  // cardioid(+90) - cardioid(-90) is a unity fig-8 facing +90 at every angle
  for (let b = -180; b <= 180; b += 15) {
    const cl = R.pat(0.5, b - 90), cr = R.pat(0.5, b + 90);
    close(cl - cr, Math.cos((b - 90) * Math.PI / 180), 1e-12);
  }
});
test("Schoeps virtual-pair numbers", () => {
  // cardioid M, 1:1 -> ~63 deg, gradient ~0.69 (hypercardioid-ish)
  let v = R.virtualPair(0.5, 1);
  close(v.thetaDeg, 63.4, 0.1); close(v.gradient, 0.691, 0.002);
  // today's +3.5 dB Mid (k = 1/1.5) -> ~53 deg, gradient ~0.63
  v = R.virtualPair(0.5, R.kFromDesk(0, 1.5));
  close(v.thetaDeg, 53.1, 0.1); close(v.gradient, 0.625, 0.002);
  // omni M + fig-8 S at 1:1 = two cardioids at +/-90
  v = R.virtualPair(0, 1);
  close(v.thetaDeg, 90, 1e-9); close(v.gradient, 0.5, 1e-9); assert.equal(v.name, "cardioid");
});
test("decode: front source is centred, side source goes to one side", () => {
  const f = R.decode(0.5, 1, 0); close(f.L, f.R, 1e-12);
  const left = R.decode(0.5, 1, 90); assert.ok(left.L > left.R);
  close(left.R, 0.5 - 1, 1e-12);  // M(90)=0.5, S=1
});
test("+3.5 dB is 20log10(1.5)", () => close(R.db(R.M_GAIN), 3.52, 0.01));
test("back-to-back gain mismatch leaks omni: 1 dB -> about -25 dB", () => {
  close(R.b2bLeakDb(1), -24.8, 0.2);
  close(R.b2bLeakDb(0.5), -30.8, 0.2);
  assert.equal(R.b2bLeakDb(0), -Infinity);
});

// D18 (locked 4 Oct 16:43): unity decode with a -3 dB trim on M and S.
test("D18 unity_trim: S:M = 1 -> +-63 deg, both 3 dB down; legacy stays today's values", () => {
  assert.equal(R.MS_LEVEL, "legacy");                  // T3 ships legacy; T3b flips it
  const leg = R.build("ms_b");
  assert.equal(leg.desk.gain_exact_c, 1.5); assert.equal(leg.desk.width_l, 0);
  const u = R.build("ms_b", "unity_trim");
  close(R.db(u.desk.gain_exact_c), -3, 1e-9);
  assert.equal(u.desk.width_l, -3);
  close(R.kFromDesk(u.desk.width_l, u.desk.gain_exact_c), 1, 1e-9);
  close(R.virtualPair(0.5, 1).thetaDeg, 63.4, 0.2);
  const c = R.build("ms_c", "unity_trim");
  assert.equal(c.desk.width_r, -3);                      // both S strips trimmed
  assert.equal(R.build("ms_b", "nope"), null);
  assert.equal(R.build("ms_b", 1.0).desk.gain_exact_c, 1.0); // old numeric API kept
});
