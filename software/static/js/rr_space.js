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
  var mode = spaceMode === "legs" ? "legs" : (spaceMode === "paths" ? "paths" : "lattice");
  try {
    imageView.setMode(mode);
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

function syncSpaceModeUI() {
  document.querySelectorAll(".space-mode-chip").forEach(function (btn) {
    var on = btn.getAttribute("data-space-mode") === spaceMode;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
  var camHint = "Drag to orbit · right-drag or Shift to pan · scroll to zoom · double-click to reset";
  if (spaceMode === "legs") {
    if (imageViewTitle) imageViewTitle.textContent = "Last legs into the mic";
  } else if (spaceMode === "paths") {
    if (imageViewTitle) imageViewTitle.textContent = "In-room specular paths";
  } else {
    if (imageViewTitle) imageViewTitle.textContent = "Mirrored-room lattice";
  }
  if (imageViewHint) imageViewHint.textContent = camHint;
}

function withImageView(fn) {
  ensureImageView();
  if (imageView) fn(imageView);
}