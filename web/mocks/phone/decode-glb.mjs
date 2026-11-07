// Undo EXT_meshopt_compression in a GLB, so a page can load it without a WebAssembly decoder.
// Usage: node decode-glb.mjs <path to meshoptimizer/meshopt_decoder.mjs> <in.glb> <out.glb>
import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const [decoderPath, input, output] = process.argv.slice(2);
const { MeshoptDecoder } = await import(pathToFileURL(decoderPath).href);
await MeshoptDecoder.ready;

const glb = readFileSync(input);
if (glb.toString("ascii", 0, 4) !== "glTF") throw new Error(`${input}: not a GLB`);
let offset = 12;
let json;
let bin = Buffer.alloc(0);
while (offset < glb.length) {
  const length = glb.readUInt32LE(offset);
  const type = glb.toString("ascii", offset + 4, offset + 8);
  const body = glb.subarray(offset + 8, offset + 8 + length);
  if (type === "JSON") json = JSON.parse(body.toString("utf8"));
  else if (type === "BIN\0") bin = body;
  offset += 8 + length;
}

const EXT = "EXT_meshopt_compression";
const align4 = (n) => (n + 3) & ~3;
const parts = [];
let cursor = 0;
for (const view of json.bufferViews) {
  const ext = view.extensions?.[EXT];
  let data;
  if (ext) {
    const source = bin.subarray(ext.byteOffset ?? 0, (ext.byteOffset ?? 0) + ext.byteLength);
    const target = new Uint8Array(ext.count * ext.byteStride);
    MeshoptDecoder.decodeGltfBuffer(target, ext.count, ext.byteStride, new Uint8Array(source), ext.mode, ext.filter ?? "NONE");
    data = Buffer.from(target);
    delete view.extensions[EXT];
    if (!Object.keys(view.extensions).length) delete view.extensions;
  } else {
    if (view.buffer !== 0) throw new Error(`bufferView on buffer ${view.buffer} without ${EXT}`);
    data = bin.subarray(view.byteOffset ?? 0, (view.byteOffset ?? 0) + view.byteLength);
  }
  const start = align4(cursor);
  if (start > cursor) parts.push(Buffer.alloc(start - cursor));
  parts.push(data);
  view.buffer = 0;
  view.byteOffset = start;
  view.byteLength = data.length;
  cursor = start + data.length;
}
const total = align4(cursor);
if (total > cursor) parts.push(Buffer.alloc(total - cursor));
const newBin = Buffer.concat(parts);
json.buffers = [{ byteLength: newBin.length }];
for (const key of ["extensionsUsed", "extensionsRequired"]) {
  if (json[key]) {
    json[key] = json[key].filter((name) => name !== EXT);
    if (!json[key].length) delete json[key];
  }
}

let text = Buffer.from(JSON.stringify(json), "utf8");
text = Buffer.concat([text, Buffer.alloc(align4(text.length) - text.length, 0x20)]);
const header = Buffer.alloc(12);
header.write("glTF", 0, "ascii");
header.writeUInt32LE(2, 4);
const chunk = (type, body) => {
  const head = Buffer.alloc(8);
  head.writeUInt32LE(body.length, 0);
  head.write(type, 4, "ascii");
  return Buffer.concat([head, body]);
};
const out = Buffer.concat([header, chunk("JSON", text), chunk("BIN\0", newBin)]);
out.writeUInt32LE(out.length, 8);
writeFileSync(output, out);
console.log(`${input} -> ${output}: ${glb.length} -> ${out.length} bytes; extensions ${JSON.stringify(json.extensionsUsed ?? [])}`);
