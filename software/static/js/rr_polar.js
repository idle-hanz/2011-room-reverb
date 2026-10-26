/* Polar tab pages, the speaker plot, and the catalogue fetch. */
"use strict";


function paintPolarBandKey(labels) {
  var host = document.getElementById("polarBandKey");
  if (!host) return;
  var labs = (labels && labels.length) ? labels : ["20", "63", "125", "250", "1k", "4k", "8k", "16k"];
  var sig = labs.join("|") + ":" + (polarSolo == null ? "" : String(polarSolo));
  if (host.getAttribute("data-key") === sig) return;
  host.setAttribute("data-key", sig);
  host.innerHTML = "";
  labs.forEach(function (lab, i) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "polar-band";
    btn.setAttribute("data-band", String(i));
    if (polarSolo === i) btn.classList.add("is-solo");
    else if (polarSolo != null) btn.classList.add("is-dim");
    var sw = document.createElement("i");
    sw.className = "mic-ring-swatch";
    sw.style.background = window.FreqPalette
      ? FreqPalette.cssAt(i, labs.length)
      : "#e11d48";
    btn.appendChild(sw);
    btn.appendChild(document.createTextNode(" " + lab));
    btn.addEventListener("click", function () {
      polarSolo = (polarSolo === i) ? null : i;
      host.removeAttribute("data-key");
      paintPolarBandKey(labs);
      if (micDesk && micDesk.setSoloBand) micDesk.setSoloBand(polarSolo);
      if (polarView && polarView.setSoloBand) polarView.setSoloBand(polarSolo);
      if (polarPage === "speakers" && polarCache) drawSpeakerPolar(polarCache);
    });
    host.appendChild(btn);
  });
}

function polarBannerText() {
  var mode = state.colour_mode || "MEASURED_SHELF";
  if (mode === "MEASURED_SHELF") return "Measured: real mic response, relative to on-axis";
  return "Ideal pattern";
}

function paintPolarBanner() {
  var banner = document.getElementById("polarBanner");
  if (banner) banner.textContent = polarBannerText();
}

function syncPolarPageUI() {
  document.querySelectorAll("[data-polar-page]").forEach(function (btn) {
    var on = btn.getAttribute("data-polar-page") === polarPage;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
  var combined = document.getElementById("polarCombined");
  var host = document.getElementById("polarEachHost");
  var speakers = document.getElementById("polarSpeakers");
  if (combined) combined.hidden = polarPage !== "combined";
  if (host) host.hidden = polarPage !== "each";
  if (speakers) speakers.hidden = polarPage !== "speakers";
  paintPolarBandKey(polarCache && polarCache.ring_labels);
  placePolarTrio();
  if (polarPage === "speakers") drawSpeakerPolar(polarCache);
}
function drawSpeakerPolar(data) {
  var canvas = document.getElementById("polarSpeakerCanvas");
  if (!canvas || !data || !data.speaker_l || !data.speaker_r) return;
  if (!data.speaker_l.length || !data.speaker_r.length) return;
  var ratio = Math.min(window.devicePixelRatio || 1, 2);
  var rect = canvas.getBoundingClientRect();
  var cssW = rect.width > 2 ? rect.width : 900;
  var cssH = rect.height > 2 ? rect.height : 420;
  var w = Math.max(2, Math.floor(cssW * ratio));
  var h = Math.max(2, Math.floor(cssH * ratio));
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
  var ctx = canvas.getContext("2d");
  ctx.fillStyle = "#0c0e14";
  ctx.fillRect(0, 0, w, h);
  var grids = [data.speaker_l, data.speaker_r];
  var names = ["Speaker L", "Speaker R"];
  var peak = 1e-12;
  grids.forEach(function (grid) {
    grid.forEach(function (row) {
      row.forEach(function (v) {
        if (v > peak) peak = v;
      });
    });
  });
  grids.forEach(function (grid, side) {
    var nB = grid.length;
    var nAz = grid[0].length;
    var cx = w * (side === 0 ? 0.27 : 0.73);
    var cy = h * 0.54;
    var R = Math.min(w * 0.18, h * 0.32);
    if (window.MicDesk && MicDesk.drawPolarChartFrame) {
      MicDesk.drawPolarChartFrame(ctx, cx, cy, R, 0, {
        useDb: false,
        fontPx: Math.max(11 * ratio, Math.min(14 * ratio, R * 0.1)),
        lineWidth: Math.max(1, ratio)
      });
    }
    var bi, ai, k, theta, g, sx, sy;
    for (bi = 0; bi < nB; bi++) {
      if (polarSolo != null && bi !== polarSolo) continue;
      ctx.beginPath();
      for (ai = 0; ai <= nAz; ai++) {
        k = ai % nAz;
        theta = (k / nAz) * Math.PI * 2;
        g = Math.max(0, Number(grid[bi][k]) / peak);
        sx = cx + R * g * Math.sin(theta);
        sy = cy - R * g * Math.cos(theta);
        if (ai === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      }
      if (window.FreqPalette) ctx.strokeStyle = FreqPalette.cssAt(bi, nB);
      else if (window.SpectrumColors) ctx.strokeStyle = SpectrumColors.forIndex(bi, nB).css;
      else ctx.strokeStyle = "hsl(" + Math.round(255 * bi / Math.max(1, nB - 1)) + ",78%,58%)";
      ctx.lineWidth = bi === nB - 1 ? 2 : 1.25;
      ctx.stroke();
    }
    ctx.fillStyle = "#e8e6df";
    ctx.font = Math.round(13 * ratio) + "px Segoe UI, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(names[side], cx, Math.round(22 * ratio));
  });
}

function placePolarTrio() {
  var trio = document.getElementById("micPolarTrio");
  if (!trio) return;
  var each = document.getElementById("micEach");
  var host = document.getElementById("polarEachHost");
  if (currentView === "polar" && polarPage === "each" && host) {
    if (trio.parentElement !== host) host.appendChild(trio);
  } else if (each) {
    var foot = document.getElementById("micEachFoot");
    if (foot && foot.parentElement === each) {
      if (trio.parentElement !== each || trio.nextElementSibling !== foot) {
        each.insertBefore(trio, foot);
      }
    } else if (trio.parentElement !== each) {
      each.appendChild(trio);
    }
  }
}
function schedulePolar() {
  if (currentView !== "mic" && currentView !== "polar") return;
  if (polarTimer) clearTimeout(polarTimer);
  polarTimer = setTimeout(refreshPolar, 120);
}
async function refreshPolar() {
  polarTimer = null;
  var seq = ++polarReq;
  if (micDesk && micDesk.setPolarStatus) micDesk.setPolarStatus("pending");
  try {
    var body = Object.assign({}, state);
    body.n_az = 72;
    if (body.sy == null && body.my != null) body.sy = body.my;
    var res = await fetch("/api/display/polar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    noteHttp(res);
    if (!res.ok) throw new Error("HTTP " + res.status);
    var data = await res.json();
    toastWarnings(data);
    if (seq !== polarReq) return;
    if (!data.ok) throw new Error(data.error || "polar failed");
    polarCache = data;
    if (micDesk && micDesk.setPolar) micDesk.setPolar(data, "ok");
    if (polarPage === "speakers") drawSpeakerPolar(data);
    if (polarView && polarView.setData) polarView.setData(data);
    paintPolarBandKey(data.ring_labels);
    paintPolarBanner();
  } catch (err) {
    if (seq === polarReq && micDesk && micDesk.setPolarStatus) micDesk.setPolarStatus("fail");
    var meta = document.getElementById("polarMeta");
    if (meta) meta.textContent = "Polar: " + String(err);
  }
}

function loadMicCatalogue() {
  fetch("/api/catalogue/mics").then(function (res) {
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }).then(function (data) {
    var groups = { MEASURED: [], ASSUMED: [] };
    micCatalogue = {};
    (data.presets || []).forEach(function (row) {
      if (!row || !row.mic_id) return;
      micCatalogue[row.mic_id] = row;
      var key = String(row.honesty || "").toUpperCase() === "MEASURED" ? "MEASURED" : "ASSUMED";
      groups[key].push(row);
    });
    function fill(sel, id) {
      if (!sel) return;
      sel.innerHTML = "";
      [["MEASURED", "Measured"], ["ASSUMED", "Assumed"]].forEach(function (pair) {
        if (!groups[pair[0]].length) return;
        var og = document.createElement("optgroup");
        og.label = pair[1];
        groups[pair[0]].forEach(function (row) {
          var opt = document.createElement("option");
          opt.value = row.mic_id;
          opt.textContent = row.display_name || row.mic_id;
          og.appendChild(opt);
        });
        sel.appendChild(og);
      });
      if (id && micCatalogue[id]) sel.value = id;
    }
    fill(document.getElementById("mic_preset_side"), state.mic_preset_l || DEFAULT_MIC);
    fill(document.getElementById("mic_preset_l"), state.mic_preset_l || DEFAULT_MIC);
    fill(document.getElementById("mic_preset_r"), state.mic_preset_r || state.mic_preset_l || DEFAULT_MIC);
    fill(document.getElementById("mic_preset_centre"), state.mic_preset_c || DEFAULT_MIC);
    if (patternFromPreset()) applyPresetLaw();
    paintMicModel();
    syncPatternChrome();
  }).catch(function () {
    showToast("Mic presets failed");
  });
}