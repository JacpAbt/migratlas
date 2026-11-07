# The phone mock

The last of the four mocks [ADR 0020](../../../docs/adr/0020-the-phone-is-a-pad-on-the-desk.md) was
decided on: the pad on the desktop's 3D table, its pages composed at the phone's size and written on
as they are read, the candle, the pencil and the pad's flags as the settings. Kept so the decisions
have something to point at, as `web/mocks/book.html` was kept for ADR 0015; deleted at ADR 0020's
step E1. Not type-checked, not built by Vite, not in either gate.

It is a mock and does things the build must not: it shrinks type to fit a page (the book adds a leaf
instead), carries a second copy of the desk scene (`phone-desk.ts`; the build gives `desk/scene.ts` a
layout), embeds the models as base64 and decodes them out of meshopt so a single published page could
carry them, and cuts each chapter after its opening page.

## Rebuilding it

From this directory, with `web/` as `$WEB`:

```bash
mkdir -p assets
for m in brass_candleholders seadogs_compass magnifying_glass_01; do node decode-glb.mjs "$WEB/node_modules/meshoptimizer/meshopt_decoder.mjs" "$WEB/public/desk/$m.glb" "assets/$m.glb"; done
cp "$WEB/public/desk/wood_diff.webp" "$WEB/public/desk/wood_nor.webp" assets/
node bundle.mjs "$WEB"
python build.py "$WEB"
```

`assets/phone-desk.html` is the single page that was published; `assets/phone-desk-local.html` is the
same wrapped in a document, for a local static server.
