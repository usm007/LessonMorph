/* Concatenate tsc-emitted global scripts into a single file://-safe runtime.js.
 * tsc runs with module:none, so every dist file shares one scope; order matters. */
const fs = require("fs");
const path = require("path");

const dist = path.join(__dirname, "..", "dist");
const order = ["types.js", "store.js", "viewport.js", "render.js", "motion.js", "nav.js", "main.js"];

let out = "";
for (const name of order) {
  const p = path.join(dist, name);
  if (!fs.existsSync(p)) {
    console.error("missing compiled file: " + name);
    process.exit(1);
  }
  out += fs.readFileSync(p, "utf8") + "\n";
}
fs.writeFileSync(path.join(dist, "runtime.js"), out);
for (const name of order) fs.unlinkSync(path.join(dist, name));
fs.copyFileSync(path.join(__dirname, "..", "src", "styles.css"), path.join(dist, "styles.css"));
console.log("runtime.js written");
