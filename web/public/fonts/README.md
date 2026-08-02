# Bundled fonts

**The woff2 files are in `web/src/assets/fonts/`, not here.** Vite rewrites and hashes URLs it
can see, and an absolute `/fonts/...` reference 404s under the GitHub Pages subpath where `base`
is `/migratlas/`. Only the licence text stays in `public/`, so it is served verbatim at a stable
URL. `web/src/styles/fonts.css` is the only place the files are named.

Self-hosted, not fetched from a CDN. `web/tests/globe.spec.ts` asserts the default build requests
nothing off-origin, and a webfont CDN would break that assertion — correctly, since a font host sees
every visitor's IP.

Only the **latin** subset of each face is here, and getting that wrong is the single most common
way one of these lands broken. Google's `css2` endpoint returns one `@font-face` per unicode range
ordered with **latin last**, so taking the first URL gets cyrillic: a file that downloads fine,
reports as loaded, and renders every character on this site through the fallback. Seven of these
were fetched that way on the first pass. Excalifont has the same trap for a different reason — it
ships seven hashed subsets inside `@excalidraw/excalidraw` and exactly one carries latin.

If a face ever looks like it is not applying, test it before believing the CSS: render a string in
`"Family", monospace` and again in `"Family", sans-serif`. If the two widths differ, the family is
not resolving and both are fallbacks.

| File | Face | Copyright | Licence |
| --- | --- | --- | --- |
| `Virgil.woff2` | Virgil | 2021–, Ellinor Rapp | OFL 1.1 |
| `Excalifont.woff2` | Excalifont | 2024, Excalidraw | OFL 1.1 |
| `ShantellSans.woff2` | Shantell Sans | 2022, Shantell Martin and Anya Danilova | OFL 1.1 |
| `AtkinsonHyperlegible.woff2` | Atkinson Hyperlegible | 2020, Braille Institute of America | OFL 1.1 |
| `OpenDyslexic.woff2` | OpenDyslexic | 2019, Abbie Gonzalez | OFL 1.1 |
| `PlexMono-500.woff2` | IBM Plex Mono | © 2017 IBM Corp., reserved font name "Plex" | OFL 1.1 |
| `SourceSerif4-400.woff2`, `SourceSerif4-600.woff2` | Source Serif 4 | 2014, The Source Serif 4 Project Authors | OFL 1.1 |
| `ArchitectsDaughter.woff2` | Architects Daughter | 2010, Kimberly Geswein | OFL 1.1 |

Full licence text sits beside each file as `OFL-<family>.txt`. The OFL requires the licence to
travel with the font, so these are not optional and must not be pruned as build noise.
`OFL-excalifont.txt` is the one assembled here rather than fetched: Excalidraw publishes Excalifont
under OFL 1.1 but does not ship a licence file beside the font, so the body is the OFL text from
their own Virgil repository with Excalifont's copyright line, and the note at the top says so.

## What each one is for

Set by [ADR 0008](../../../docs/adr/0008-the-sketchbook-rebuild.md), which replaces ADR 0007's
single hand-face rule with three presets. Two of the three are accessibility provisions rather than
preferences, which is why the type is a setting a reader can reach and not a decision taken for
them.

| Preset | Headings | Everything else |
| --- | --- | --- |
| **Hand throughout** (default) | Virgil | Shantell Sans |
| **Hand for headings only** | Excalifont | Atkinson Hyperlegible |
| **Made for dyslexia** | OpenDyslexic | OpenDyslexic |

- **Virgil** — the original Excalidraw hand. Looser and more written than its successor, which is
  why it heads the all-hand preset rather than the legible one.
- **Excalifont** — Virgil's successor, drawn to keep the hand and fix the legibility.
- **Shantell Sans** — a marker face drawn for interfaces. This is the one that lets the small parts
  stop being typed: it survives 13px where a looser hand becomes texture.
- **Atkinson Hyperlegible** — drawn by the Braille Institute, with letterforms separated on the
  features that blur first at low vision.
- **OpenDyslexic** — weighted bottoms, wide apertures, and no two letters that are each other
  mirrored: b/d and p/q are drawn as different shapes rather than one shape flipped.
- **IBM Plex Mono** — every figure, and the one face no preset replaces. A column has to line up
  and no handwriting face has tabular digits; Virgil's widest digit is half again its narrowest,
  which turns the per-survey table on a species page into a stack of ragged numbers.
- **Source Serif 4** and **Architects Daughter** — kept, because removing the shape the site had
  would make one of the choices unavailable.

Each preset carries its own scale and leading in `tokens.css`, because the faces do not share an
x-height: dropping one in at the same pixel size makes it look a size larger or smaller than the
last. That is the whole of what "optimised" means here — switching changes the letterforms and
nothing else.

## Total cost

Eight faces. The three presets never load more than three of them at once, and `font-display: swap`
means none of them blocks paint. For comparison MapLibre is 268 KB gzipped, so the type is a
fraction of the map library and is the thing a visitor actually looks at.
