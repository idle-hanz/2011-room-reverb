/* Fetch the shared settings table once, before the page state is built. */
"use strict";
(function () {
  var xhr = new XMLHttpRequest();
  xhr.open("GET", "/api/settings", false);
  xhr.send(null);
  if (xhr.status !== 200) {
    throw new Error("settings table HTTP " + xhr.status);
  }
  window.RR_SETTINGS = JSON.parse(xhr.responseText);
})();
