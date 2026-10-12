# ADR 0005 — Bundle the coastlines; make the detailed basemap opt-in

**Status:** accepted · 2026-07-28

## Context

The globe shipped with Protomaps' public demo tileset as its default basemap
(`demo-bucket.protomaps.com/v4.pmtiles`). It never worked in a browser, and the failure was
not obvious because the app looked plausible: panels, sliders and data layers all rendered on
an empty sphere.

PMTiles reads a tileset with HTTP range requests, which makes the `Range` header non-simple
and so requires a CORS preflight. The demo bucket refuses it:

```
$ curl -i -X OPTIONS -H "Origin: http://localhost:4188" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: range" \
    https://demo-bucket.protomaps.com/v4.pmtiles
HTTP/2 403
<Error><Code>AccessForbidden</Code><Message>CORSResponse: This CORS request is not
allowed...</Message></Error>
```

A plain ranged `GET` succeeds — 206, `content-range: bytes 0-16383/137064143631` — so the
tileset is readable server-to-server and unreadable from any page, from any origin. It is also
a 137 GB planet build, which is a clue that it was never meant to back a web app.

Two consequences worth separating. The first is a bug: a default that cannot work. The second
is structural: a third-party host was deciding whether the map drew at all, and the answer
arrived as an error event rather than as a build failure.

An earlier attempt at this went the wrong way. Believing MapLibre awaited the sprite before
firing `style.load`, a watchdog swapped the whole style for a bare sphere after 8 seconds. The
browser test written to prove it disproved it instead: with every Protomaps request stalled,
`style.load` fired in 1.1 s, because a failed sprite only logs. The watchdog was defending
against a failure mode that does not exist, while introducing a real one — an eight-second
threshold that a slow mobile connection would trip, destroying a basemap that was merely late.
It was removed.

## Decision

**Coastlines and borders are bundled with the app.** Natural Earth 1:110m land polygons and
national boundary lines, attributes stripped and coordinates rounded to four decimals: 127 and
331 features, ~210 KiB of GeoJSON. Public domain, so it can simply be committed. It is the
right resolution for a globe, where a 1:10m coastline would be thrown away by the rasteriser.

**The detailed basemap is opt-in via `VITE_BASEMAP_PMTILES`, with no default.** When set, the
Protomaps vector layers are drawn above the outline; when unset, no request leaves the origin.
Self-hosting is what ADR 0001 already assumed for production, so this only removes a default
that pretended otherwise.

**A test pins it.** `the default build requests nothing off-origin` fails if any request in a
default run has a non-origin URL.

## Consequences

- The globe always has coastlines, offline included, and cannot be broken by someone else's CDN.
- ~210 KiB of committed geometry, against a 150 MB heap budget — immaterial.
- No place labels or roads until a tileset is configured. Acceptable: at globe zoom the labels
  were POI-scale detail nobody reads, and the data layers carry their own meaning.
- Two basemaps must stay visually consistent. Both palettes live in `web/src/globe/flavor.ts`
  for that reason, with `LAND` matching the detailed flavour's `earth`.
- Anyone deploying with detail must build the tileset themselves. Documented where the variable
  is read.

## Amendment, 2026-10-12, regional detail for the atlas's plates

[ADR 0021](0021-the-globe-becomes-a-moving-atlas.md) replaces the globe with a drawn atlas whose
plates come down to twenty kilometres across, where this ADR's reason for 1:110m -- a globe's
rasteriser throws finer detail away -- no longer holds: at a plate's scale the 1:110m outline is a
few straight lines, and it drew a false coast through the Svalbard herd.

**The world view keeps the 1:110m outline above. Each plate gets its own detail**, cut to its box
and thinned to about a pixel at that plate's size: Natural Earth 1:10m land, coast and rivers for
the night sky over North America and for Bylot Island (public domain, like the outline); the
Norwegian Polar Institute's *Annual coastlines for Svalbard*, 2022 (CC BY 4.0,
doi:10.21334/npolar.2021.21565514) for the Svalbard plate; and Natural Resources Canada's National
Hydro Network, work units 05BA, 05BB, 05CA, 05DA and 05DB (Open Government Licence – Canada), for
the Ya Ha Tinda, whose rivers Natural Earth either lacks or names by their system.

The same rules hold: committed, served from the origin, nothing requested elsewhere at run time.
What changes is that two of the sources ask for attribution, so their licence texts sit beside the
files and each plate's caption names its map. The files are built by a step in the Python package,
not by hand, so they can be rebuilt from the sources and checked against what is committed.
