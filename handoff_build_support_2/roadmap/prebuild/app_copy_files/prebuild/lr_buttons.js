/* lr_buttons.js — T2 prebuild (D-UI31): per-strip L and R buttons with phase, mapped onto
   the routes app.js pair() already has (centre/both/l/r/s/pan). No engine change.
   Each button has three states: 0 = off, 1 = on, -1 = on + phase inverted (Ø).
   Click cycles off -> on -> Ø -> off. Browser: window.RRLR; node: module.exports. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RRLR = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var CAPS = ["l", "c", "r"];

  function cycle(v) { return v === 0 ? 1 : (v === 1 ? -1 : 0); }

  /* Is this strip the Mid of an MS pair? (app.js state: pair_mode "ms", ms_m = "l"|"c"|"r") */
  function isMsMid(state, cap) {
    return String(state.pair_mode || "") === "ms" && String(state.ms_m || "c") === cap;
  }

  /* Buttons -> engine fields. btn = {l, r} in {-1,0,1}. ctx = {msMid: bool, legacyBoth: bool}.
     Returns {route, phase, mute, pot} where pot is "balance" | "width" | "none". */
  function toRoute(btn, ctx) {
    var l = btn.l | 0, r = btn.r | 0;
    ctx = ctx || {};
    if (l === 0 && r === 0) return { route: null, phase: 1, mute: true, pot: "none" };
    if (l !== 0 && r === 0) return { route: "l", phase: l, mute: false, pot: "none" };
    if (l === 0 && r !== 0) return { route: "r", phase: r, mute: false, pot: "none" };
    if (l === r) {
      var both = !ctx.forcePan && !!(ctx.msMid || ctx.legacyBoth);
      return { route: both ? "both" : "pan", phase: l, mute: false, pot: both ? "none" : "balance" };
    }
    /* l and r have opposite signs: the side signal. (+L, -R) = s; (-L, +R) = s with Ø. */
    return { route: "s", phase: l, mute: false, pot: "width" };
  }

  /* Existing scene fields -> buttons (migration / paint). Never changes the sound:
     the returned patch only resets pan to 0 when "centre" becomes pan-at-centre. */
  function fromRoute(route, phase, mute, ctx) {
    var p = Number(phase) < 0 ? -1 : 1;
    route = String(route || "pan");
    ctx = ctx || {};
    var out = { btn: { l: 0, r: 0 }, patch: {}, legacyBoth: false, forcePan: false, muted: !!mute };
    if (route === "l") out.btn = { l: p, r: 0 };
    else if (route === "r") out.btn = { l: 0, r: p };
    else if (route === "s") out.btn = { l: p, r: -p };
    else if (route === "both") { out.btn = { l: p, r: p }; out.legacyBoth = !ctx.msMid; }
    else if (route === "centre") { out.btn = { l: p, r: p }; out.patch = { pan: 0, route: "pan" }; out.forcePan = !!ctx.msMid; }
    else if (ctx.pan != null && Number(ctx.pan) <= -1) { out.btn = { l: p, r: 0 }; out.panEnd = true; }  /* pan hard left == l */
    else if (ctx.pan != null && Number(ctx.pan) >= 1) { out.btn = { l: 0, r: p }; out.panEnd = true; }   /* pan hard right == r */
    else { out.btn = { l: p, r: p }; out.forcePan = !!ctx.msMid; }  /* pan */
    /* forcePan: a Mid strip that is on pan/centre today must stay pan (else L+R = both = +6 dB). */
    if (mute) out.shownBtn = { l: 0, r: 0 };   /* a muted strip shows both buttons dark */
    return out;
  }

  /* The state patch for app.js when the user clicks a button on strip `cap`.
     state = app state; side = "l" | "r". Returns an object to Object.assign onto state. */
  function clickPatch(state, cap, side) {
    var f = fromRoute(state["mic_route_" + cap], state["phase_" + cap], state["mute_" + cap],
                      { msMid: isMsMid(state, cap), pan: state["pan_" + cap] });
    var btn = state["mute_" + cap] ? { l: 0, r: 0 } : { l: f.btn.l, r: f.btn.r };
    btn[side] = cycle(btn[side]);
    var t = toRoute(btn, { msMid: isMsMid(state, cap), legacyBoth: f.legacyBoth, forcePan: f.forcePan });
    var patch = {};
    if (t.mute) { patch["mute_" + cap] = true; return { patch: patch, btn: btn, pot: t.pot }; }
    patch["mute_" + cap] = false;
    patch["mic_route_" + cap] = t.route;
    patch["phase_" + cap] = t.phase;
    if (t.route === "pan" && (f.patch.pan === 0 || f.panEnd || f.btn.l === 0 || f.btn.r === 0)) patch["pan_" + cap] = 0;
    /* one side -> both sides lands on the centre detent, so the click is always audible */
    return { patch: patch, btn: btn, pot: t.pot };
  }

  /* Same maths as app.js deskWeights().pair() (linear law), used by the tests to prove
     every legacy route maps to identical L/R weights. */
  function weights(route, a, pan, phase) {
    a = a * (Number(phase) < 0 ? -1 : 1);
    if (route === "centre") return [a * 0.5, a * 0.5];
    if (route === "both") return [a, a];
    if (route === "l") return [a, 0];
    if (route === "r") return [0, a];
    if (route === "s") return [a, -a];
    var t = Math.max(0, Math.min(1, (Number(pan) + 1) * 0.5));
    return [a * (1 - t), a * t];
  }

  /* Label + tooltip for a button state (plain words, P5). */
  function buttonLabel(side, v) {
    var S = side.toUpperCase();
    if (v === 0) return { text: S, title: "Not sent to the " + (side === "l" ? "left" : "right") + " speaker. Click: send." };
    if (v === 1) return { text: S, title: "Sent to the " + (side === "l" ? "left" : "right") + " speaker. Click: flip polarity (Ø)." };
    return { text: S + "\u00d8", title: "Sent to the " + (side === "l" ? "left" : "right") + " speaker with polarity flipped. Click: off." };
  }
  function potLabel(pot) {
    return pot === "balance" ? "Pan" : (pot === "width" ? "Width" : "\u2014");
  }

  return { CAPS: CAPS, cycle: cycle, isMsMid: isMsMid, toRoute: toRoute, fromRoute: fromRoute,
           clickPatch: clickPatch, weights: weights, buttonLabel: buttonLabel, potLabel: potLabel };
});
