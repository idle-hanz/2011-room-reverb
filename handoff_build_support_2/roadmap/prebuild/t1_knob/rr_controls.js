/* rr_controls.js — T1 prebuild: relative-drag knob + click-to-type for any range input.
   Plain ES5-compatible JS, no dependencies. Works in the browser (window.RRControls)
   and in node (module.exports) so the pure maths is unit-tested with node:test.
   It never owns state: it sets input.value and fires the input's own 'input'/'change'
   events, so app.js handlers, undo and recall keep working unchanged. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RRControls = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /* ---------- pure maths (tested) ---------- */
  function decimals(step) {
    var s = String(step);
    return s.indexOf(".") < 0 ? 0 : s.length - s.indexOf(".") - 1;
  }
  function snap(v, o) {
    var step = o.step || 0;
    if (step > 0) v = o.min + Math.round((v - o.min) / step) * step;
    if (v < o.min) v = o.min;
    if (v > o.max) v = o.max;
    return Number(v.toFixed(Math.min(6, decimals(step || 0.001) + 1)));
  }
  /* Relative drag: dPx > 0 = up/right. pxFull pixels cover the whole range. */
  function dragValue(start, dPx, o, fine) {
    var span = o.max - o.min;
    var k = (fine ? (o.fineFactor || 0.1) : 1) * span / (o.pxFull || 200);
    return start + dPx * k;
  }
  /* Sticky detents: a value within `holdPx` (in pixels of travel) of a detent sticks to it.
     Returns {value, held}. pxPerUnit = pxFull / span (coarse) or /fine. */
  function applyDetent(raw, o, fine) {
    var det = o.detents || [];
    var span = o.max - o.min;
    var pxPerUnit = (o.pxFull || 200) / span / (fine ? (o.fineFactor || 0.1) : 1);
    var hold = o.holdPx == null ? 6 : o.holdPx;
    for (var i = 0; i < det.length; i++) {
      if (Math.abs(raw - det[i]) * pxPerUnit <= hold) return { value: det[i], held: true };
    }
    return { value: raw, held: false };
  }
  function wheelValue(v, deltaY, o, fine) {
    var st = o.wheelStep || o.step || (o.max - o.min) / 100;
    if (fine) st = st * (o.fineFactor || 0.1);
    return v + (deltaY < 0 ? st : -st);
  }
  /* Typed text -> number. Accepts units and words: "3.2 m", "-4 dB", "+1.5", "L30", "R 50",
     "C", "centre", "50%" (of range when o.percent), "−6" (unicode minus). Returns NaN if unreadable. */
  function parseTyped(text, o) {
    var t = String(text == null ? "" : text).trim().replace(/\u2212/g, "-").replace(",", ".").toLowerCase();
    if (!t) return NaN;
    if (o && o.kind === "pan") {
      if (t === "c" || t === "centre" || t === "center" || t === "mid") return 0;
      var m = /^([lr])\s*(\d+(?:\.\d+)?)$/.exec(t);
      if (m) { var a = Math.min(100, Number(m[2])) / 100; return m[1] === "l" ? -a : a; }
    }
    if (o && o.kind === "fader") {
      if (t === "-inf" || t === "-∞" || t === "off") return -Infinity;
    }
    var n = /^([+-]?\d*\.?\d+)\s*(db|m|cm|mm|s|ms|hz|khz|%|°|deg)?$/.exec(t);
    if (!n) return NaN;
    var v = Number(n[1]), u = n[2] || "";
    if (u === "cm") v /= 100;
    if (u === "mm" && !(o && o.unit === "mm")) v /= 1000;
    if (u === "ms" && o && o.unit === "s") v /= 1000;
    if (u === "khz") v *= 1000;
    if (u === "%" && o && o.percentOfRange) v = o.min + (o.max - o.min) * v / 100;
    return v;
  }
  function formatValue(v, o) {
    if (o.format) return o.format(v);
    if (o.kind === "pan") {
      if (Math.abs(v) < 0.005) return "C";
      return (v < 0 ? "L" : "R") + Math.round(Math.abs(v) * 100);
    }
    var d = decimals(o.step || 0.01);
    var s = Number(v).toFixed(d);
    if (o.kind === "db" && v > 0) s = "+" + s;
    return s + (o.unitLabel ? " " + o.unitLabel : "");
  }
  function optsFromInput(input, extra) {
    var o = {
      min: Number(input.min === "" ? 0 : input.min), max: Number(input.max === "" ? 100 : input.max),
      step: Number(input.step || 0) || 0, def: input.hasAttribute && input.hasAttribute("data-default")
        ? Number(input.getAttribute("data-default")) : Number(input.defaultValue)
    };
    for (var k in (extra || {})) o[k] = extra[k];
    return o;
  }

  /* ---------- DOM layer ---------- */
  function fire(input, type) {
    var ev;
    try { ev = new Event(type, { bubbles: true }); } catch (e) { ev = document.createEvent("Event"); ev.initEvent(type, true, true); }
    input.dispatchEvent(ev);
  }
  /* Needle angle for a .knob: -140deg at min, +140deg at max (same scale as app.js paintDesk). */
  function needleDeg(v, o) {
    var f = (v - o.min) / ((o.max - o.min) || 1);
    if (f < 0) f = 0; if (f > 1) f = 1;
    return -140 + f * 280;
  }
  function paintNeedle(input, o) {
    var k = input.parentElement;
    if (k && k.classList && k.classList.contains("knob")) k.style.setProperty("--needle", needleDeg(Number(input.value), o).toFixed(1) + "deg");
  }
  function setValue(input, v, o, commit) {
    var s = snap(v, o);
    if (String(s) !== input.value) { input.value = String(s); fire(input, "input"); }
    if (commit) fire(input, "change");
    if (o._readout) o._readout.textContent = formatValue(Number(input.value), o);
    input.setAttribute("aria-valuetext", formatValue(Number(input.value), o));
    paintNeedle(input, o);
    return s;
  }

  /* Inline text edit on a readout element. Enter applies, Esc/blur cancels (blur applies if changed). */
  function attachTyping(input, readout, o) {
    if (!readout || readout.__rrTyping) return;
    readout.__rrTyping = true;
    readout.classList.add("rr-typable");
    readout.setAttribute("title", (readout.getAttribute("title") || "") + (readout.getAttribute("title") ? " · " : "") + "Click to type a value");
    readout.addEventListener("click", function (e) {
      if (input.disabled) return;
      e.preventDefault(); e.stopPropagation();
      var box = document.createElement("input");
      box.type = "text"; box.className = "rr-type-box"; box.value = formatValue(Number(input.value), o);
      box.setAttribute("aria-label", (input.getAttribute("aria-label") || input.id) + " value");
      var done = false;
      function finish(apply) {
        if (done) return; done = true;
        if (apply) {
          var v = parseTyped(box.value, o);
          if (v === -Infinity) v = o.min;
          if (isFinite(v)) setValue(input, v, o, true);
          else readout.classList.add("rr-type-bad");
          setTimeout(function () { readout.classList.remove("rr-type-bad"); }, 600);
        }
        box.remove(); readout.style.display = "";
        readout.textContent = formatValue(Number(input.value), o);
      }
      box.addEventListener("keydown", function (k) {
        if (k.key === "Enter") { k.preventDefault(); finish(true); }
        else if (k.key === "Escape") { k.preventDefault(); finish(false); }
        k.stopPropagation();
      });
      box.addEventListener("blur", function () { finish(true); });
      readout.style.display = "none";
      readout.parentNode.insertBefore(box, readout.nextSibling);
      box.focus(); box.select();
    });
  }

  /* Knob: the existing transparent range input stays for keyboard + ARIA, but pointer
     input is taken over (relative drag). `knobEl` is the .knob label around the input. */
  function attachKnob(input, opts) {
    if (!input || input.__rrKnob) return null;
    var o = optsFromInput(input, opts);
    input.__rrKnob = o;
    var knobEl = input.closest ? (input.closest(".knob") || input.parentNode) : input.parentNode;
    knobEl.classList.add("rr-knob");
    var readout = document.createElement("output");
    readout.className = "rr-knob-read";
    readout.textContent = formatValue(Number(input.value), o);
    knobEl.parentNode.insertBefore(readout, knobEl.nextSibling);
    o._readout = readout;
    attachTyping(input, readout, o);
    input.setAttribute("aria-valuetext", formatValue(Number(input.value), o));
    var drag = null;
    input.addEventListener("pointerdown", function (e) {
      if (input.disabled || e.button !== 0) return;
      e.preventDefault();
      input.focus();
      drag = { x: e.clientX, y: e.clientY, v0: Number(input.value), fine: e.shiftKey, moved: false };
      try { input.setPointerCapture(e.pointerId); } catch (_) {}
      knobEl.classList.add("rr-dragging");
    });
    input.addEventListener("pointermove", function (e) {
      if (!drag) return;
      if (e.shiftKey !== drag.fine) { /* re-base when Shift changes mid-drag so the value doesn't jump */
        drag.v0 = Number(input.value); drag.x = e.clientX; drag.y = e.clientY; drag.fine = e.shiftKey;
      }
      var d = (drag.y - e.clientY) + (e.clientX - drag.x);
      if (Math.abs(d) >= 1) drag.moved = true;
      var raw = dragValue(drag.v0, d, o, drag.fine);
      var r = applyDetent(raw, o, drag.fine);
      knobEl.classList.toggle("rr-detent", r.held);
      setValue(input, r.value, o, false);
    });
    function end(e) {
      if (!drag) return;
      try { input.releasePointerCapture(e.pointerId); } catch (_) {}
      knobEl.classList.remove("rr-dragging", "rr-detent");
      if (drag.moved) fire(input, "change");
      drag = null;
    }
    input.addEventListener("pointerup", end);
    input.addEventListener("pointercancel", end);
    input.addEventListener("click", function (e) { e.preventDefault(); });
    input.addEventListener("dblclick", function (e) {
      e.preventDefault();
      setValue(input, isFinite(o.def) ? o.def : (o.min + o.max) / 2, o, true);
    });
    input.addEventListener("wheel", function (e) {
      if (input.disabled) return;
      e.preventDefault();
      setValue(input, wheelValue(Number(input.value), e.deltaY, o, e.shiftKey), o, true);
    }, { passive: false });
    input.addEventListener("keydown", function (e) {
      var st = o.step || (o.max - o.min) / 100, v = Number(input.value), nv = null;
      if (e.key === "PageUp") nv = v + 10 * st;
      else if (e.key === "PageDown") nv = v - 10 * st;
      if (nv != null) { e.preventDefault(); setValue(input, nv, o, true); }
    });
    input.addEventListener("input", function () {
      readout.textContent = formatValue(Number(input.value), o);
    });
    knobs.push(input);
    return { opts: o, readout: readout };
  }

  var knobs = [];
  /* Call at the end of app.js paintDesk(): re-reads values set by presets/recall, repaints
     readout + needle (this also fixes audit B2: Width needle never moved). */
  function refreshAll() {
    for (var i = 0; i < knobs.length; i++) {
      var inp = knobs[i], o = inp.__rrKnob;
      if (o._readout && !o._readout.parentNode.querySelector(".rr-type-box")) o._readout.textContent = formatValue(Number(inp.value), o);
      inp.setAttribute("aria-valuetext", formatValue(Number(inp.value), o));
      paintNeedle(inp, o);
    }
    return knobs.length;
  }
  /* Click-to-type for every slider whose readout is <output id="<id>_out"> (the app's pattern). */
  function attachAllTyping(doc) {
    var n = 0;
    var inputs = doc.querySelectorAll('input[type="range"]');
    for (var i = 0; i < inputs.length; i++) {
      var inp = inputs[i];
      if (inp.__rrKnob) continue;
      var out = inp.id ? doc.getElementById(inp.id + "_out") : null;
      if (!out) continue;
      attachTyping(inp, out, optsFromInput(inp, {}));
      n++;
    }
    return n;
  }

  return { snap: snap, dragValue: dragValue, applyDetent: applyDetent, wheelValue: wheelValue,
           parseTyped: parseTyped, formatValue: formatValue, optsFromInput: optsFromInput, needleDeg: needleDeg,
           refreshAll: refreshAll,
           attachKnob: attachKnob, attachTyping: attachTyping, attachAllTyping: attachAllTyping };
});
