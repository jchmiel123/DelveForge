/* Version + cache stamp, one step.  Run before every ship:
     node tools/stamp.js

   Ported from Slotto v1.4.0 (the reference for the all-projects rule:
   every web page visibly shows "v<version> - updated <date time>").

   DelveForge is a single self-contained file (web/index.html - also the
   source of the hosted artifact fragment), so the stamp rewrites the
   inline <script id="version-stamp"> block IN PLACE: the
   window.DELVEFORGE_VERSION line, which fills every .version-tag
   element (the footer line under the game).

   Reads the VERSION file at the repo root (SemVer).
*/
const fs = require("fs");
const path = require("path");
const root = path.join(__dirname, "..");

const version = fs.readFileSync(path.join(root, "VERSION"), "utf8").trim();
const now = new Date();
const p2 = n => String(n).padStart(2, "0");
const builtHuman = now.getFullYear() + "-" + p2(now.getMonth() + 1) + "-" +
  p2(now.getDate()) + " " + p2(now.getHours()) + ":" + p2(now.getMinutes());

const htmlPath = path.join(root, "web", "index.html");
let html = fs.readFileSync(htmlPath, "utf8");
const lineRe = /window\.DELVEFORGE_VERSION = \{ version: "[^"]*", built: "[^"]*" \};/;
if (!lineRe.test(html)) {
  console.error("web/index.html: version-stamp block not found - refusing");
  process.exit(1);
}
html = html.replace(lineRe,
  `window.DELVEFORGE_VERSION = { version: "${version}", built: "${builtHuman}" };`);
fs.writeFileSync(htmlPath, html);
console.log(`web/index.html: v${version} built ${builtHuman}`);
