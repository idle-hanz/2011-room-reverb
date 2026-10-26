// Box mirror defaults on: one linked card. Off splits Left and Right. Splay has no switch.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { appSource as app } from "./app_sources.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");

function makeEl() {
  const el = {
    hidden: false,
    className: "",
    textContent: "",
    value: "",
    checked: false,
    disabled: false,
    style: {},
    dataset: {},
    attrs: {},
    children: [],
    _html: "",
  };
  el.classList = {
    toggle(name, on) {
      const parts = el.className.split(/\s+/).filter((p) => p && p !== name);
      const has = el.className.split(/\s+/).includes(name);
      const next = on === undefined ? !has : !!on;
      if (next) parts.push(name);
      el.className = parts.join(" ");
    },
    add(name) { this.toggle(name, true); },
    remove(name) { this.toggle(name, false); },
  };
  el.setAttribute = (k, v) => { el.attrs[k] = String(v); };
  el.getAttribute = (k) => (Object.prototype.hasOwnProperty.call(el.attrs, k) ? el.attrs[k] : null);
  el.appendChild = (child) => { el.children.push(child); return child; };
  el.addEventListener = () => {};
  el.remove = () => {};
  el.closest = () => null;
  el.querySelector = (sel) => {
    if (sel === "[data-solo]" || sel === "[data-mute]") return makeEl();
    return null;
  };
  el.querySelectorAll = (sel) => {
    if (sel === ".surface-card") {
      return el.children.filter((c) => c.className.split(/\s+/).includes("surface-card"));
    }
    return [];
  };
  Object.defineProperty(el, "innerHTML", {
    get() { return el._html; },
    set(v) { el._html = String(v); el.children = []; },
  });
  return el;
}

function boot() {
  const nodes = {
    surfaceCards: makeEl(),
    mirrorLrRow: makeEl(),
    mirrorLr: makeEl(),
  };
  const document = {
    getElementById(id) { return nodes[id] || null; },
    createElement() { return makeEl(); },
    querySelectorAll() { return []; },
  };
  const state = {
    room_shape: "box",
    mirror_lr: true,
    surfaces_solo: null,
    surfaces_mute: null,
  };
  const context = {
    window: {},
    document,
    fetch() {
      return Promise.resolve({ json() { return Promise.resolve({}); } });
    },
    console,
  };
  context.window.document = document;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(here, "../static/js/room_shape.js"), "utf8"), context);
  context.RoomShape = context.window.RoomShape;
  vm.runInContext(fs.readFileSync(path.join(here, "../static/js/colour_surfaces.js"), "utf8"), context);
  const cs = new context.window.ColourSurfaces({
    getState() { return state; },
    onChange() {},
  });
  return { cs, state, nodes };
}

function cards(nodes) {
  return nodes.surfaceCards.querySelectorAll(".surface-card").map((c) => ({
    letter: c.getAttribute("data-letter"),
    pair: c.getAttribute("data-pair"),
    html: c._html,
  }));
}

test("box default is mirrored and the switch splits the cards", () => {
  const { cs, state, nodes } = boot();
  assert.match(app, /mirror_lr:\s*true/);
  assert.equal(nodes.mirrorLrRow.hidden, false);
  assert.equal(nodes.mirrorLr.checked, true);
  const linked = cards(nodes);
  assert.deepEqual(linked.map((c) => c.letter), ["A", "B", "D", "E", "F"]);
  assert.equal(linked[0].pair, "C");
  assert.match(linked[0].html, /Left \+ Right \(mirrored\)/);
  assert.match(linked[0].html, /class="sc-link"/);
  assert.equal(linked.some((c) => c.letter === "C"), false);

  state.surfaces.A.absorb[0] = 0.91;
  state.surfaces.C.absorb[0] = 0.11;
  state.surfaces.B.absorb[0] = 0.33;
  cs.syncWallList();
  assert.equal(state.surfaces.C.absorb[0], 0.91);
  state.mirror_lr = false;
  cs.syncWallList();

  assert.equal(nodes.mirrorLrRow.hidden, false);
  assert.equal(nodes.mirrorLr.checked, false);
  const split = cards(nodes);
  assert.deepEqual(split.map((c) => c.letter), ["A", "C", "B", "D", "E", "F"]);
  split.forEach((c) => assert.equal(c.pair, null));
  assert.match(split[0].html, />Left</);
  assert.match(split[1].html, />Right</);
  assert.equal(split[0].html.includes("sc-link"), false);
  assert.equal(split[1].html.includes("sc-link"), false);
  assert.equal(state.surfaces.C.absorb[0], 0.91);
  assert.equal(state.surfaces.A.absorb[0], 0.91);
  assert.equal(state.surfaces.B.absorb[0], 0.33);
  assert.equal(state.surfaces.C.letter, "C");
});

test("splay shows no switch and stays one linked card", () => {
  const { cs, state, nodes } = boot();
  state.room_shape = "splay";
  state.mirror_lr = false;
  state.surfaces.A.absorb[0] = 0.42;
  state.surfaces.C.absorb[0] = 0.07;
  cs.syncWallList();
  assert.equal(nodes.mirrorLrRow.hidden, true);
  assert.equal(nodes.mirrorLr.disabled, true);
  const linked = cards(nodes);
  assert.equal(linked[0].letter, "A");
  assert.equal(linked[0].pair, "C");
  assert.match(linked[0].html, /Left \+ Right \(mirrored\)/);
  assert.match(linked[0].html, /class="sc-link"/);
  assert.equal(linked.some((c) => c.letter === "C"), false);
  assert.equal(state.surfaces.C.absorb[0], 0.42);
  const wall = page.indexOf('id="surfaceCards"');
  const sw = page.indexOf('id="mirrorLrRow"');
  assert.ok(sw > page.indexOf('id="surfAudition"') && sw < wall);
  assert.match(page, /id="mirrorLr"[^>]*checked/);
  assert.match(page, />Mirror left\/right walls</);
  assert.match(app, /o\.mirror_lr = !!state\.mirror_lr/);
  assert.match(app, /mix\.mirror_lr = !!state\.mirror_lr/);
});

test("lede and live hide the switch and keep the mirrored card", () => {
  ["lede", "live"].forEach((shape) => {
    const { cs, state, nodes } = boot();
    state.room_shape = shape;
    state.mirror_lr = false;
    state.surfaces.A.absorb[0] = 0.42;
    state.surfaces.C.absorb[0] = 0.07;
    cs.syncWallList();
    assert.equal(nodes.mirrorLrRow.hidden, true, shape);
    assert.equal(nodes.mirrorLr.disabled, true, shape);
    const linked = cards(nodes);
    const sides = linked.filter((c) => c.pair === "C");
    assert.equal(sides.length, shape === "lede" ? 2 : 1, shape);
    sides.forEach((c) => {
      assert.equal(c.letter, "A");
      assert.match(c.html, /Left \+ Right \(mirrored\)/);
    });
    assert.equal(linked.some((c) => c.letter === "C"), false);
    assert.equal(state.surfaces.C.absorb[0], 0.42);
  });
});

test("gable hides the switch and lists both roofs and both gable ends", () => {
  const { cs, state, nodes } = boot();
  state.room_shape = "gable";
  state.mirror_lr = false;
  state.surfaces.A.absorb[0] = 0.42;
  state.surfaces.C.absorb[0] = 0.07;
  cs.syncWallList();
  assert.equal(nodes.mirrorLrRow.hidden, true);
  assert.equal(nodes.mirrorLr.disabled, true);
  const linked = cards(nodes);
  assert.deepEqual(linked.map((c) => c.letter), ["A", "D", "B", "E", "F", "F"]);
  assert.equal(linked[0].pair, "C");
  assert.match(linked[0].html, /Left \+ Right \(mirrored\)/);
  assert.match(linked[0].html, /class="sc-link"/);
  assert.equal(linked.filter((c) => c.html.includes("Gable end")).length, 2);
  assert.match(linked[4].html, /Left roof/);
  assert.match(linked[4].html, /#e2e8f0/);
  assert.match(linked[5].html, /Right roof/);
  assert.match(linked[5].html, /#e2e8f0/);
  assert.match(linked[1].html, /#cbd5e1/);
  assert.match(linked[2].html, /#2dd4bf/);
  assert.equal(linked.some((c) => c.letter === "C"), false);
  assert.equal(state.surfaces.C.absorb[0], 0.42);
});

test("hex hides the switch and links both angled side pairs", () => {
  const { cs, state, nodes } = boot();
  state.room_shape = "hex";
  state.mirror_lr = false;
  state.surfaces.A.absorb[0] = 0.42;
  state.surfaces.C.absorb[0] = 0.07;
  state.surfaces.A.material = "plaster_smooth";
  state.surfaces.B.material = "brick_unglazed";
  state.surfaces.D.material = "concrete_painted";
  state.surfaces.E.material = "wood_parquet";
  state.surfaces.F.material = "acoustic_ceiling_tile";
  cs.syncWallList();
  assert.equal(nodes.mirrorLrRow.hidden, true);
  assert.equal(nodes.mirrorLr.disabled, true);
  const linked = cards(nodes);
  assert.deepEqual(linked.map((c) => c.letter), ["A", "A", "B", "D", "E", "F"]);
  assert.equal(linked[0].pair, "C");
  assert.equal(linked[1].pair, "C");
  assert.match(linked[0].html, /Left \+ Right \(mirrored\)/);
  assert.match(linked[1].html, /Left \+ Right \(mirrored\)/);
  assert.match(linked[0].html, /class="sc-link"/);
  assert.match(linked[1].html, /class="sc-link"/);
  assert.match(linked[0].html, /#38bdf8/);
  assert.match(linked[1].html, /#38bdf8/);
  assert.match(linked[2].html, /Front/);
  assert.match(linked[2].html, /#2dd4bf/);
  assert.match(linked[3].html, /Back/);
  assert.match(linked[3].html, /#cbd5e1/);
  assert.match(linked[4].html, /Floor/);
  assert.match(linked[4].html, /#78716c/);
  assert.match(linked[5].html, /Ceiling/);
  assert.match(linked[5].html, /#e2e8f0/);
  assert.equal(linked[2].pair, null);
  assert.equal(linked[3].pair, null);
  assert.equal(linked.some((c) => c.letter === "C"), false);
  assert.equal(state.surfaces.C.absorb[0], 0.42);
});
