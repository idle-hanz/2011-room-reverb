/* Routing panel keys. Browser: window.RRRouting. Node: module.exports. No DOM.
   Master posts the Bloom keys Play already reads. Array and room are
   Render-only and stay out of the Play body. Off posts nothing. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RRRouting = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var COMP = { natural: 1, glue: 1, room_crush: 1, nuke: 1, swell: 1 };
  var NAMES = ["array", "room", "master"];

  function num(v, d) {
    var n = Number(v);
    return isFinite(n) ? n : d;
  }

  function preName(v) {
    var s = String(v || "none");
    return s === "neve1073" || s === "u610a" ? s : "none";
  }

  function compName(v) {
    var s = String(v || "off");
    return COMP[s] ? s : "off";
  }

  function strip(src, name) {
    return {
      pre: preName(src["route_" + name + "_pre"]),
      drive: num(src["route_" + name + "_drive"], 0),
      comp: compName(src["route_" + name + "_comp"]),
      amount: num(src["route_" + name + "_amount"], 0)
    };
  }

  function live(row) {
    var preOn = row.pre !== "none";
    var compOn = row.comp !== "off" && row.amount > 0;
    return { preOn: preOn, compOn: compOn };
  }

  function migrate(src) {
    if (!src) return src;
    if (src.route_master_pre != null || src.route_master_comp != null) return src;
    var menu = String(src.bloom_menu || "natural");
    var pre = menu === "neve1073" || menu === "u610a";
    if (src.bloom_on && pre) {
      src.route_master_pre = menu;
      src.route_master_drive = num(src.pre_drive_ui, 0);
      src.route_master_comp = "off";
      src.route_master_amount = 0;
    } else if (src.bloom_on) {
      src.route_master_pre = "none";
      src.route_master_drive = 0;
      src.route_master_comp = compName(menu);
      src.route_master_amount = num(src.bloom_amount_ui, 0);
    } else {
      src.route_master_pre = "none";
      src.route_master_drive = 0;
      src.route_master_comp = "off";
      src.route_master_amount = 0;
    }
    NAMES.forEach(function (name) {
      if (name === "master") return;
      if (src["route_" + name + "_pre"] == null) src["route_" + name + "_pre"] = "none";
      if (src["route_" + name + "_drive"] == null) src["route_" + name + "_drive"] = 0;
      if (src["route_" + name + "_comp"] == null) src["route_" + name + "_comp"] = "off";
      if (src["route_" + name + "_amount"] == null) src["route_" + name + "_amount"] = 0;
    });
    return src;
  }

  function masterScene(src) {
    if (!src) return {};
    var row = strip(src, "master");
    var on = live(row);
    if (!on.preOn && !on.compOn) return {};
    return {
      bloom_preset: on.compOn ? row.comp : "natural",
      bloom_amount: on.compOn ? row.amount : 0,
      bloom_colour: false,
      glue_colour: false,
      pre_colour: on.preOn ? row.pre : "off",
      pre_drive_db: on.preOn ? row.drive : 0,
      predelay_ms: 0,
      bloom_attack_scale: 1,
      bloom_release_scale: 1
    };
  }

  function renderScene(src) {
    if (!src) return {};
    var o = {};
    ["array", "room"].forEach(function (name) {
      var row = strip(src, name);
      var on = live(row);
      if (!on.preOn && !on.compOn) return;
      o[name + "_preset"] = on.compOn ? row.comp : "natural";
      o[name + "_amount"] = on.compOn ? row.amount : 0;
      o[name + "_pre"] = on.preOn ? row.pre : "off";
      o[name + "_drive_db"] = on.preOn ? row.drive : 0;
    });
    return o;
  }

  return { migrate: migrate, masterScene: masterScene, renderScene: renderScene };
});
