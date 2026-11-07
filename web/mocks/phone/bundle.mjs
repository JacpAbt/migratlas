// Bundle the phone desk and three.js into one classic script the page can load beside itself.
// Usage: node bundle.mjs <web dir>
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const web = path.resolve(process.argv[2]);
const here = path.dirname(fileURLToPath(import.meta.url));
const { build } = await import(pathToFileURL(path.join(web, "node_modules/rolldown/dist/index.mjs")).href);

await build({
  input: path.join(here, "entry.ts"),
  resolve: {
    alias: { "desk-props": path.join(web, "src/lib/desk/props.ts") },
    modules: [path.join(web, "node_modules"), "node_modules"],
  },
  output: {
    file: path.join(here, "assets", "desk.js"),
    format: "iife",
    minify: true,
  },
});
console.log("assets/desk.js written");
