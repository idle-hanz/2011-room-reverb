// Box Mirror L/R. Off keeps two side cards. On links them. Splay has no toggle.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(here, "../static/index.html"), "utf8");
const app = fs.readFileSync(path.join(here, "../static/js/app.js"), "utf8");

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
    mirror_lr: false,
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
  }));
}

test("toggle off keeps separate L/R cards and toggle on links them", () => {
  const { cs, state, nodes } = boot();
  assert.equal(nodes.mirrorLrRow.hidden, false);
  assert.deepEqual(cards(nodes).map((c) => c.letter), ["A", "C", "B", "D", "E", "F"]);
  cards(nodes).forEach((c) => assert.equal(c.pair, null));

  state.surfaces.A.absorb[0] = 0.91;
  state.surfaces.C.absorb[0] = 0.11;
  state.surfaces.B.absorb[0] = 0.33;
  state.mirror_lr = true;
  cs.syncWallList();

  assert.equal(nodes.mirrorLrRow.hidden, false);
  const linked = cards(nodes);
  assert.deepEqual(linked.map((c) => c.letter), ["A", "B", "D", "E", "F"]);
  assert.equal(linked[0].pair, "C");
  assert.equal(state.surfaces.C.absorb[0], 0.91);
  assert.equal(state.surfaces.A.absorb[0], 0.91);
  assert.equal(state.surfaces.B.absorb[0], 0.33);
  assert.equal(state.surfaces.C.letter, "C");
});

test("splay shows no toggle and stays one pair", () => {
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
  assert.equal(linked.some((c) => c.letter === "C"), false);
  assert.equal(state.surfaces.C.absorb[0], 0.42);
  assert.match(page, /id="mirrorLr"/);
  assert.match(page, />Mirror L\/R</);
  assert.match(app, /o\.mirror_lr = !!state\.mirror_lr/);
  assert.match(app, /mix\.mirror_lr = !!state\.mirror_lr/);
});
