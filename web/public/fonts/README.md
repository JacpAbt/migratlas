# Bundled fonts

Self-hosted, not fetched from a CDN. `web/tests/globe.spec.ts` asserts the default build requests
nothing off-origin, and a webfont CDN would break that assertion — correctly, since a font host sees
every visitor's IP.

Only the **latin** subset of each face is here. Google Fonts serves one file per unicode range, and
taking the first one returned gets you cyrillic: a 7 KB "serif" that renders every character used on
this site as a box.

| File | Face | Copyright | Licence |
| --- | --- | --- | --- |
| `ArchitectsDaughter.woff2` | Architects Daughter | 2010, Kimberly Geswein (kimberlygeswein.com) | OFL 1.1 |
| `SourceSerif4-400.woff2`, `SourceSerif4-600.woff2` | Source Serif 4 | 2014, The Source Serif 4 Project Authors | OFL 1.1 |
| `PlexMono-500.woff2` | IBM Plex Mono | © 2017 IBM Corp., reserved font name "Plex" | OFL 1.1 |

Full licence text sits beside each file as `OFL-<family>.txt`, fetched from
`github.com/google/fonts`. The OFL requires the licence to travel with the font, so these are not
optional and must not be pruned as build noise.

## What each one is for

Set by [ADR 0007](../../../docs/adr/0007-field-notebook-shell.md), and the division is load-bearing
rather than stylistic:

- **Architects Daughter** — headings only. Never a label, never a number, never below 20px. It has
  no tabular figures and poor small-size legibility, so a measurement set in it stops reading as a
  measurement.
- **Source Serif 4** — body text, 400 and 600.
- **IBM Plex Mono** — every number and every label. `−0.56 ± 0.25` is mono in all contexts, which is
  what makes it read as a reading off an instrument and aligns decimal points for free.

## Total cost

68 KB across four files, once, cached. For comparison MapLibre is 268 KB gzipped, so the type is
about a fifth of the map library and is the thing a visitor actually looks at.
