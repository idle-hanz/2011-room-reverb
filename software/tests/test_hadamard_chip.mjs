// node --test test_hadamard_chip.mjs
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

function hadamardSource() {
  const app = fs.readFileSync(path.join(HERE, "../static/js/app.js"), "utf8");
  const start = app.indexOf("function syncHadamardUI()");
  const end = app.indexOf("function setHadamardN(", start);
  assert.ok(start > 0 && end > start);
  return app.slice(start, end);
}

function chip(n) {
  const el = {
    disabled: false,
    title: "",
    active: false,
    getAttribute(name) {
      return name === "data-n" ? String(n) : null;
    },
    classList: {
      toggle(name, on) {
        if (name === "active") el.active = !!on;
      },
    },
  };
  return el;
}

function paint(stored, running) {
  const state = { hadamard_n: stored };
  const chips = [8, 16, 32, 64, 128].map(chip);
  const readout = { textContent: "" };
  const document = {
    querySelectorAll(sel) {
      assert.equal(sel, ".hadamard-chip");
      return chips;
    },
    getElementById(id) {
      assert.equal(id, "hadamardReadout");
      return readout;
    },
  };
  const LiveFDN = {
    isRunning() {
      return running;
    },
  };
  const context = { state, document, window: { LiveFDN }, LiveFDN };
  vm.createContext(context);
  vm.runInContext(hadamardSource() + "\nsyncHadamardUI();", context);
  return { state, chips, readout };
}

function lit(chips) {
  return chips.filter((c) => c.active).map((c) => c.getAttribute("data-n"));
}

test("the chip shows 32 while Play forces a stored 64 or 128", () => {
  for (const stored of [64, 128]) {
    const live = paint(stored, true);
    assert.equal(live.state.hadamard_n, stored);
    assert.deepEqual(lit(live.chips), ["32"]);
    assert.equal(live.readout.textContent, "32 images · 32 FDN lines");
    assert.equal(live.chips.find((c) => c.getAttribute("data-n") === "64").disabled, true);
    assert.equal(live.chips.find((c) => c.getAttribute("data-n") === "128").disabled, true);
    const stopped = paint(stored, false);
    assert.equal(stopped.state.hadamard_n, stored);
    assert.deepEqual(lit(stopped.chips), [String(stored)]);
    assert.equal(
      stopped.readout.textContent,
      stored + " images · " + stored + " FDN lines"
    );
  }
  const eight = paint(8, true);
  assert.equal(eight.state.hadamard_n, 8);
  assert.deepEqual(lit(eight.chips), ["8"]);
  assert.equal(eight.readout.textContent, "8 images · 8 FDN lines");
});
