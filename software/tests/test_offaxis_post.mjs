// The Mix live request posts offaxis_tail. The server packs 45 floats when it is on.
import test from "node:test";
import assert from "node:assert/strict";
import { appSource as app } from "./app_sources.mjs";

function liveRequestBodyFrom(state) {
  const start = app.indexOf("function liveRequestBody");
  const end = app.indexOf("function feedbackLawOn", start);
  assert.ok(start > 0 && end > start);
  const src = app.slice(start, end);
  const call = new Function(
    "state",
    "heardMix",
    "window",
    src + "\nreturn liveRequestBody();"
  );
  return call(state, function () { return {}; }, {});
}

test("the Mix live request carries offaxis_tail", () => {
  const off = liveRequestBodyFrom({});
  assert.equal(off.offaxis_tail, false);
  const on = liveRequestBodyFrom({ offaxis_tail: true });
  assert.equal(on.offaxis_tail, true);
});
