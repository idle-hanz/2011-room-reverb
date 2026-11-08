/* Space tab: image lattice and the mic ticks on that view. */
"use strict";


function ensureImageView() {
  if (imageView || imageViewInitFailed) return imageView;
  if (!window.ImageViews) {
    imageViewInitFailed = true;
    if (statusEl) statusEl.textContent = "Images: ImageViews module missing";
    return null;
  }
  var canvas = document.getElementById("imageCanvas");
  if (!canvas) {
    imageViewInitFailed = true;
    if (statusEl) statusEl.textContent = "Images: #imageCanvas missing";
    return null;
  }
  /* Do not create WebGL while layout is still 0×0 (hidden/settling). */
  var rect = canvas.getBoundingClientRect();
  if (rect.width < 2 || rect.height < 2) return null;
  try {
    imageView = ImageViews.create({
      canvas: canvas,
      getState: function () { return state; }
    });
    if (!imageView) {
      imageViewInitFailed = true;
      if (statusEl) statusEl.textContent = "Images: WebGL init failed (Three.js / GPU)";
      return null;
    }
  } catch (err) {
    imageViewInitFailed = true;
    imageView = null;
    if (statusEl) {
      statusEl.textContent = "Images WebGL: " + String(err && err.message ? err.message : err);
    }
    return null;
  }
  return imageView;
}

/** After #imageViews is unhidden: double-rAF → init → resize; optional size retry. */
function paintImageViewsSoon() {
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      if (currentView !== "space") return;
      ensureImageView();
      if (imageView) {
        imageView.resize();
        if (imagesCache) applyImageView();
      }
      var canvas = document.getElementById("imageCanvas");
      if (!canvas) return;
      var rect = canvas.getBoundingClientRect();
      if (rect.width >= 2 && rect.height >= 2) return;
      /* Optional: layout still settling — one short retry */
      setTimeout(function () {
        if (currentView !== "space") return;
        ensureImageView();
        if (imageView) {
          imageView.resize();
          if (imagesCache) applyImageView();
        }
      }, 80);
    });
  });
}


function fmt(n, d) {
  if (d === undefined) d = 2;
  return Number(n).toFixed(d);
}

/* Picture ticks only. Does not write third_mic, mic_gain_c, or place_*. */
function imageMicDefaults() {
  var id = state.mic_setup || "ortf";
  if (id === "ortf") return ["L", "R"];
  if (id === "mono_c") return ["C"];
  if (id === "binaural") return ["L", "R"];
  if (state.third_mic === "off") return ["L", "R"];
  return ["L", "C", "R"];
}

function applyImageMicTicks() {
  var want = {};
  var ids = imageMicDefaults();
  ids.forEach(function (id) { want[id] = true; });
  document.querySelectorAll("#micToggles input[data-mic]").forEach(function (box) {
    box.checked = !!want[box.getAttribute("data-mic")];
  });
  selectedMics = ids.slice();
}

function selectedMicsFromUI() {
  var boxes = document.querySelectorAll("#micToggles input[data-mic]");
  var out = [];
  boxes.forEach(function (b) {
    if (b.checked) out.push(b.getAttribute("data-mic"));
  });
  if (!out.length) {
    applyImageMicTicks();
    return imageMicDefaults().slice();
  }
  return out;
}

function scheduleImagesFetch(delayMs) {
  if (currentView !== "space") return;
  if (imagesFetchTimer) clearTimeout(imagesFetchTimer);
  var ms = delayMs == null ? imagesFetchDelayMs : delayMs;
  imagesFetchTimer = setTimeout(fetchImages, ms);
}
async function fetchImages() {
  selectedMics = selectedMicsFromUI();
  /* Room spots become mic_x_* the same way Play does. Stand scenes omit those keys. */
  var body = Object.assign({}, heardMix(state), { mics: selectedMics });
  var req = ++imagesReq;
  try {
    var res = await fetch("/api/params/images", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (req !== imagesReq) return;
    noteHttp(res);
    if (!res.ok) throw new Error("HTTP " + res.status);
    imagesCache = await res.json();
    toastWarnings(imagesCache);
    if (req !== imagesReq) return;
    ensureImageView();
    applyImageView();
    /* Layout may still settle after fetch — resize+apply again next frames */
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        if (currentView !== "space") return;
        if (imageView) {
          imageView.resize();
          applyImageView();
        }
      });
    });
    if (statusEl && (statusEl.textContent.indexOf("Images:") === 0 || statusEl.textContent.indexOf("Images WebGL:") === 0)) {
      statusEl.textContent = "";
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = "Images: " + String(err && err.message ? err.message : err);
  }
}

function applyImageView() {
  if (!imagesCache) return;
  if (currentView !== "space") return;
  var n = imagesCache.count || (imagesCache.lattice && imagesCache.lattice.length) || 0;
  var mics = (imagesCache.selected_mics || []).join("+") || "C";
  if (liveMetresImg) {
    var hn = imagesCache.hadamard_n || n;
    liveMetresImg.textContent =
      n + " images · " + hn + " FDN lines · mics " + mics +
      " · c=" + (imagesCache.c || 340) + " m/s" +
      (imagesCache.source_b ? " · two clouds" : "");
  }
  if (!imageView) ensureImageView();
  if (!imageView) return;
  syncOrderSlider(imagesCache);
  try {
    imageView.setSpace({
      lattice: spaceLattice,
      paths: spacePaths,
      order: spaceOrder,
      mic: spacePathMic
    });
    imageView.setData(imagesCache);
    var heard = imageView.drawnCount && imageView.drawnCount();
    var taps = imageView.tapCount && imageView.tapCount();
    if (heard != null && liveMetresImg) {
      liveMetresImg.textContent =
        heard + " images · " + (taps != null ? taps : (imagesCache.hadamard_n || heard)) + " FDN lines · mics " + mics +
        " · c=" + (imagesCache.c || 340) + " m/s" +
        (imagesCache.source_b ? " · two clouds" : "");
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = "Images rebuild: " + String(err && err.message ? err.message : err);
    }
  }
}

function ordinal(n) {
  var v = n % 100;
  if (v >= 11 && v <= 13) return n + "th";
  var s = n % 10;
  if (s === 1) return n + "st";
  if (s === 2) return n + "nd";
  if (s === 3) return n + "rd";
  return n + "th";
}

function maxImageOrder(data) {
  var m = 1;
  function scan(list) {
    (list || []).forEach(function (t) {
      var n = Number(t && t.order);
      if (n > m) m = n;
    });
  }
  if (!data) return 8;
  scan(data.lattice);
  scan(data.lattice_b);
  var pm = data.per_mic || {};
  Object.keys(pm).forEach(function (k) { scan(pm[k]); });
  if (data.per_mic_b) Object.keys(data.per_mic_b).forEach(function (k) { scan(data.per_mic_b[k]); });
  if (m > 12) m = 12;
  return m;
}

function syncOrderSlider(data) {
  var btn = document.getElementById("spaceOrderBtn");
  if (!btn) return;
  var max = maxImageOrder(data);
  if (spaceOrder > max) spaceOrder = 0;
  var on = spaceOrder > 0;
  btn.textContent = on ? ("1st–" + ordinal(spaceOrder)) : "1st–all";
  btn.classList.toggle("active", on);
  btn.setAttribute("aria-pressed", on ? "true" : "false");
}

function syncSpaceModeUI() {
  var latticeBtn = document.getElementById("spaceLatticeBtn");
  var pathsBtn = document.getElementById("spacePathsBtn");
  if (latticeBtn) {
    latticeBtn.classList.toggle("active", !!spaceLattice);
    latticeBtn.setAttribute("aria-pressed", spaceLattice ? "true" : "false");
  }
  if (pathsBtn) {
    var on = spacePaths > 0;
    pathsBtn.classList.toggle("active", on);
    pathsBtn.setAttribute("aria-pressed", on ? "true" : "false");
    pathsBtn.textContent = spacePaths === 1 ? "Paths: lattice" : (spacePaths === 2 ? "Paths: in room" : "Paths");
  }
  document.querySelectorAll(".space-path-mic").forEach(function (btn) {
    var pick = btn.getAttribute("data-path-mic");
    var hit = pick === spacePathMic;
    btn.classList.toggle("active", hit);
    btn.setAttribute("aria-pressed", hit ? "true" : "false");
  });
  syncOrderSlider(imagesCache);
  var camHint = "Drag to orbit · right-drag or Shift to pan · scroll to zoom · double-click to reset";
  if (spacePaths === 2) {
    if (imageViewTitle) imageViewTitle.textContent = "In-room reflections";
  } else if (spacePaths === 1) {
    if (imageViewTitle) imageViewTitle.textContent = "Paths from the image sources";
  } else if (imageViewTitle) {
    imageViewTitle.textContent = spaceLattice ? "Mirrored-room lattice" : "Home room";
  }
  if (imageViewHint) imageViewHint.textContent = camHint;
}

function applySpaceView() {
  syncSpaceModeUI();
  if (currentView !== "space") return;
  if (!imagesCache) {
    scheduleImagesFetch(80);
    return;
  }
  applyImageView();
}

function withImageView(fn) {
  ensureImageView();
  if (imageView) fn(imageView);
}