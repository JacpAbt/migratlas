# ADR 0021 — The globe becomes a moving atlas

**Status:** accepted · 2026-10-12, when the owner judged the last prototype and asked for it to be
built where the globe is, having answered the two questions it raised (the last section). Replaces
[ADR 0002](0002-maplibre-globe.md) for the world chapter, settles the projection question
[ADR 0013](0013-the-scroll-and-the-chapters.md) decision 2 left open, and amends
[ADR 0005](0005-bundled-outline-basemap.md) with regional detail. The book, the desk and the phone's
container ([ADR 0020](0020-the-phone-is-a-pad-on-the-desk.md)) are untouched.

## Context

On 2026-10-09 the owner called the globe's interaction sub-par and its use unclear. Looked at with
them, the chapter opened on a bare earth with all ten layers off, named each layer after its
dataset, did not turn to a layer when one was switched on, and said its clock moved one layer when
it moved five. Its documents disagreed about its purpose: [ADR 0007](0007-field-notebook-shell.md)
calls the globe the index to a set of arguments, the page itself said "every published layer, and
no argument on top of it".

Two corrections followed a first brainstorm: the chapter should look like the book, and *"what we
would like to show is not the position of the animals but the migration, how they move"*. An audit
of the published layers found what can honestly move: the radar's weekly traffic with a heading and
a ground speed at 161 stations, 170 Arctic foxes at one position a day, two herds' weekly presence
per 0.01° cell, the sea ice's monthly median edge and the half-monthly green wave. The marine grids,
the two atlases' change, the detectability map and the 1,121 searchable taxa have no time in them.

Prototypes were built outside the app on the real layers, each judged by the owner in a browser:

| Prototype | What it tried | Owner's verdict |
| --- | --- | --- |
| Night sky, A and B | The radar as pen strokes flowing along each station's heading; or as watercolour washes with a pencil arrow | A, *"way better"* |
| The atlas | The whole world moving first, a filter zooming into a regional plate; single-animal toggles | Kept — start from the whole world |
| Coast and rivers | Natural Earth 10m, then national surveys for the two herd plates | Kept |
| Herds | Dots per cell, then an inked range with the past weeks trailing and pen flicks for each shift | Kept, *"more like a pen stroke than lines with dots"* |
| Transitions | Morph between projections; a fade; a flight between plates; a turning globe; a spot | The spot, after *"the resize of the globe ... jarring"* |

## Decisions

1. **The world chapter is a drawn atlas.** Canvas 2D in the book's ink, on the book's paper: coast
   gone over twice, land hatched by hand, a pencil graticule. No WebGL and no tiles, so the chapter
   draws in every browser the book does, and MapLibre leaves the build once nothing imports it.

2. **It opens on the whole world, moving.** Every system that moves plays at once through its own
   year on an equal-area world map, with a handwritten callout at each. Choosing one — a callout or
   the list — takes the camera to that system's plate; "the whole world" brings it back. Between two
   plates the camera flies directly, easing out only as far as a frame holding both.

3. **Every map is equal-area, so a reader's eye can compare sizes.** Equal Earth for the world, a
   Lambert azimuthal equal-area plate centred on each system. This settles ADR 0013 decision 2: the
   herd that Mercator inflated 23 times and the ice it inflated 42 times are drawn at their size.

4. **A move never shows one map becoming another.** Every move between places is made in one
   projection, the plates' Lambert with its centre travelling the great circle. The flat world
   appears only at the ends: going in it closes to a spot round the place, the projection changes
   inside that spot where the two differ by a pixel, and the spot opens as the camera dives; coming
   back is the reverse. The spot never opens past 60° of arc from the camera's centre, so the
   globe's horizon is never on the sheet. Morphing, fading and turning a globe were each tried and
   each showed the land change shape.

5. **What a mark means is stated beside it, and nothing is drawn that the data cannot carry.**

   | System | Mark | What it is | What it is not |
   | --- | --- | --- | --- |
   | The night sky | A pen stroke | One night's flight of what a radar saw: starting within 50 km of it (the profile's footprint, `docs/PLAN.md`), running 8 hours at its measured heading and ground speed; more strokes, more traffic | One night, one kind of animal, or a route between radars. The 8 hours is an assumption, and the caption says so |
   | The foxes | A line drawn a day at a time, a red nib at its head | Each fox's daily median position, all started together on day 1 | A season: the published tracks carry no dates |
   | The herds | An inked, hatched range; the past five weeks in dashed pencil; pen flicks | Where collared animals were recorded in the typical week; each flick joins a newly reached cell to the nearest cell held the week before | An animal's path. Cells, not animals, are counted, since one animal crossing three cells is in all three |
   | The sea ice | A dotted edge | The 1981–2010 monthly median | Any one year |
   | The green wave | A faint moving wash under the rest | Half-monthly greenness | A response to anything |

6. **Plates are places, not species.** A plate is named for where it is — the night sky over North
   America, Bylot Island, Svalbard, the Ya Ha Tinda — so the code stays taxon-agnostic and a plate
   promises only what its source resolves. The radar's toggle says it is not one species. The three
   tracked animals are the single-species toggles because they are the only species-resolved
   sources that move.

7. **What does not move stays, as still maps.** The two marine grids, the two atlases' change and
   the detectability map are drawn on the world view in the same ink when switched on, and their
   captions say they hold one value for their whole period. The search across the taxa stays, and
   with it a claim's road to its specimen.

8. **Regional detail comes from the regions' own surveys.** At a plate's scale the 1:110m outline is
   a few straight lines. Natural Earth 1:10m serves the night sky and Bylot; the Svalbard plate takes
   the Norwegian Polar Institute's surveyed coast (CC BY 4.0); the Ya Ha Tinda takes Natural
   Resources Canada's National Hydro Network (Open Government Licence – Canada), the Red Deer River
   among it, which Natural Earth does not carry. A Python step fetches, clips and thins them; the
   outputs are committed beside the 1:110m world as ADR 0005 committed it, with each licence and
   attribution beside them and in the plate's caption. The world view keeps 1:110m.

9. **Nothing new about any animal is published.** The ranges and the shifts are computed in the
   browser from layers already cleared by `redact.py`; a range is drawn coarser than the cells it is
   made from, and a shift joins cells, not animals. Putting dates on the fox tracks would publish
   something new and would need its own `PublicationClearance`, so they stay undated.

10. **The words are authored in Python.** Titles, callouts, captions and button labels are a report
    (`reports/atlas.py` → `web/public/atlas.json`), rendered verbatim, so a sentence changes in one
    place and the browser assertions quote the build.

## On the spread, on the phone

On the spread the plate crosses the fold, as an atlas plate does: one drawing over both pages, the
caption and the controls on pasted slips. A turning page carries a still of the half it covers, so
no second atlas runs during a turn. On the phone the atlas fills the world leaf with its controls in
the flap, until ADR 0020's step B2 gives the world leaf its place in the pad.

## Build order

One change at a time, each gated and committed before the next, on its own branch until the last.

| Step | What lands | Kill condition |
| --- | --- | --- |
| 1 | This ADR; ADR 0005's amendment | — |
| 2 | The plates' basemap: the fetch-and-clip step, its outputs, their licences | A plate's files exceed 600 KB: thin harder or split by zoom |
| 3 | The words: `reports/atlas.py` and `atlas.json` | — |
| 4 | The engine: projections, camera, drawing and the moving layers, as modules with no page yet | — |
| 5 | The atlas in the world chapter, replacing the globe on the spread and the phone; the tests asking what it drew | A transition cannot hold 30 frames a second on the owner's laptop: fewer strokes and a lower pixel ratio, then shorter flights |
| 6 | The still maps, the search and the specimen's road | The JSON fetched on arrival passes the 3,000,000-byte budget: fetch a still map when it is switched on |
| 7 | The green wave on the world view | It makes the world view read as imagery rather than ink: draw it only on its own toggle |
| 8 | MapLibre and the old globe removed; `check-build.mjs`, `CLAUDE.md` and ADR 0002 updated | — |

**For the whole direction:** if after step 5 the owner cannot tell at a glance that the chapter
shows movement, the plates stop and the design goes back to the prototype.

## What does not change

The layers and their clearances, the payload, heap and off-origin budgets, the clock's address in
the URL, reduced motion landing in its final state on the first frame, and the rule that frontend
prose is authored in Python.

## Settled with the owner, 2026-10-12

- **What does not move:** still maps in the atlas, not dropped and not deferred.
- **The green wave:** on the world view, under the rest, with no plate of its own.

## Amended 2026-10-12: a regional still map has a plate

Decision 7 put every still map on the world view, and southern Africa's two atlases do not fit it.
Their 496 quarter-degree cells span about 60 by 45 pixels of the spread's world map, and the one
empty ocean beside them takes an inset of about three times, where a cell is three pixels, a ring
cannot be told from a dot, and the coast is the 1:110m outline decision 8 refused at a plate's
scale. So a still map whose data cover one region is drawn on a plate of its own, named for the
place as the others are -- southern Africa, on Natural Earth 1:10m -- and choosing it moves the
camera there as choosing a system does. The two marine grids and the detectability map cover the
world and stay on it.

Kill condition: the plate's map passes `MAX_BYTES`, or a ring cannot be told from a dot at the
phone's size -- then it goes back to the world view, as an inset.
