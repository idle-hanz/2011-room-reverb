/* Source count, balance, and the air readout. */
"use strict";


function paintSourceSplit() {
  var oneBtn = document.getElementById("oneSourceBtn");
  var twoBtn = document.getElementById("twoSourceBtn");
  var extra = document.getElementById("twoSourceExtra");
  var can = wavChannels >= 2;
  if (oneBtn) {
    oneBtn.classList.toggle("active", !state.two_sources);
    oneBtn.setAttribute("aria-pressed", state.two_sources ? "false" : "true");
  }
  if (twoBtn) {
    twoBtn.disabled = !can;
    twoBtn.classList.toggle("active", !!state.two_sources && can);
    twoBtn.setAttribute("aria-pressed", state.two_sources && can ? "true" : "false");
  }
  if (extra) extra.hidden = !state.two_sources;
  var mir = document.getElementById("mirrorB");
  if (mir) mir.checked = !!state.mirror_b;
  var bal = document.getElementById("sourceBalance");
  var balOut = document.getElementById("sourceBalanceOut");
  if (bal && document.activeElement !== bal) bal.value = String(state.source_balance || 0);
  if (balOut) balOut.textContent = balanceLabel(state.source_balance || 0);
}

function wavChannelCount(file) {
  return file.slice(0, 128).arrayBuffer().then(function (ab) {
    var u = new Uint8Array(ab);
    if (u.length < 24) return 1;
    if (u[0] !== 82 || u[1] !== 73 || u[2] !== 70 || u[3] !== 70) return 1;
    if (u[12] === 102 && u[13] === 109 && u[14] === 116 && u[15] === 32) {
      return u[22] | (u[23] << 8);
    }
    var i = 12;
    while (i + 8 <= u.length) {
      var id = String.fromCharCode(u[i], u[i + 1], u[i + 2], u[i + 3]);
      var sz = u[i + 4] | (u[i + 5] << 8) | (u[i + 6] << 16) | (u[i + 7] << 24);
      if (id === "fmt ") {
        var chOff = i + 10;
        if (chOff + 1 < u.length) return u[chOff] | (u[chOff + 1] << 8);
      }
      if (sz <= 0 || i + 8 + sz > u.length) break;
      i += 8 + sz + (sz & 1);
    }
    return 1;
  });
}
function airPeakRh(climate) {
  var t = AIR_PRESET_T[climate];
  if (t == null) t = 20;
  var peak = AIR_RH_PEAK[t];
  return peak == null ? AIR_RH_PEAK[20] : peak;
}
function airRhPct(humidity, climate) {
  var h = Number(humidity);
  if (!(h > 0)) return null;
  if (h > 1) h = 1;
  var preset = AIR_PRESET_RH[climate];
  if (preset == null) preset = AIR_PRESET_RH.studio_20C_50RH;
  var peak = airPeakRh(climate);
  var anchor = Math.max(preset, peak);
  if (h <= AIR_RH_NOMINAL) {
    return AIR_RH_WET + (h / AIR_RH_NOMINAL) * (anchor - AIR_RH_WET);
  }
  return anchor + ((h - AIR_RH_NOMINAL) / (1 - AIR_RH_NOMINAL)) * (peak - anchor);
}
function fmtRh(rh) {
  var r = Math.round(rh * 10) / 10;
  if (Math.abs(r - Math.round(r)) < 0.05) return String(Math.round(r));
  return r.toFixed(1);
}
function paintHumidityReadout(el, out) {
  var rh = airRhPct(state.humidity, state.air_climate);
  var tip = rh == null ? "Air off" : ("Relative humidity " + fmtRh(rh) + "%");
  if (out) out.textContent = rh == null ? "off" : (fmtRh(rh) + "% RH");
  if (el) el.title = tip;
  var label = document.getElementById("humidity_label");
  if (label) label.title = tip;
}