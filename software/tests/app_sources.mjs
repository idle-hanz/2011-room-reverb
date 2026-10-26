// Page scripts in index.html order. Tests slice this text the way they sliced app.js.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const JS = path.join(path.dirname(fileURLToPath(import.meta.url)), "../static/js");
const FILES = [
  "rr_state.js",
  "rr_mic.js",
  "rr_mix.js",
  "rr_room.js",
  "rr_source.js",
  "rr_space.js",
  "rr_polar.js",
  "rr_transport.js",
  "rr_settings.js",
  "app.js",
];

export const appSource = FILES.map((name) => fs.readFileSync(path.join(JS, name), "utf8")).join("\n");
