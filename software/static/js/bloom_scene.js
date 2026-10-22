/* Bloom panel keys. Browser: window.RRBloom. Node: module.exports. No DOM.
   Off returns nothing, so Play and Render stay on the bit-exact path.
   Neve and 610-A are pre_colour. The other five are bloom_preset. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RRBloom = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var COMP = { natural: 1, glue: 1, room_crush: 1, nuke: 1, swell: 1 };

  function num(v, d) {
    var n = Number(v);
    return isFinite(n) ? n : d;
  }

  function scene(src) {
    if (!src || !src.bloom_on) return {};
    var menu = String(src.bloom_menu || "natural");
    var pre = menu === "neve1073" || menu === "u610a";
    var o = {
      predelay_ms: num(src.predelay_ui, 0),
      bloom_attack_scale: num(src.bloom_attack_ui, 1),
      bloom_release_scale: num(src.bloom_release_ui, 1)
    };
    if (pre) {
      o.bloom_preset = "natural";
      o.bloom_amount = 0;
      o.bloom_colour = false;
      o.glue_colour = false;
      o.pre_colour = menu;
      o.pre_drive_db = num(src.pre_drive_ui, 0);
    } else {
      o.bloom_preset = COMP[menu] ? menu : "natural";
      o.bloom_amount = num(src.bloom_amount_ui, 0);
      o.bloom_colour = !!src.bloom_colour_ui;
      o.glue_colour = menu === "glue" && !!src.glue_colour_ui;
      o.pre_colour = "off";
      o.pre_drive_db = 0;
    }
    return o;
  }

  return { scene: scene };
});
