# The prototype, explained — a snapshot taken 2026-08-19

What Migratlas is today, part by part, written for a reader who does not live in the code.
Every part ends with *where this goes next* — the evolutions already planned or registered.
Counts and results quoted here are this date's snapshot; the live site recomputes its own.

## What this is

Migratlas is an interactive map of animal movement backed by a research pipeline. The map is
the visible half. The half that matters is the attempt to answer, honestly, four questions:
where animals are, how their movements have changed over decades, what is driving the change,
and whether any of it can be predicted. The project's defining habit is that it publishes its
limits with the same prominence as its results — empty map cells, failed predictions and
refused analyses are treated as findings, because for a project whose argument is honesty,
they are.

## 1. The library of sources

Everything the site shows begins as data from someone else: weather radars, fish surveys, GPS
collars, bird atlases, satellites, climate archives. Thirty-one sources are registered today,
and registration is a real door — a source enters only with its licence, its citation, its
known problems and its sensitivity classification written down first, and a credits document
is generated from that registry and tested so it can never drift out of date. Data whose
licence forbids resharing is used for analysis but never redistributed.

*Where this goes next:* the collared animals in the library are resident herds — they stay
home. A genuinely migratory tracked species, with an open licence and enough animals to
protect individual locations, is a standing search (#49). The southern hemisphere remains the
library's largest gap, and the site says so on its own coverage page rather than hiding it.

## 2. The safety gate

Publishing animal locations can get animals killed. Before anything is drawn, an automatic
gate — modelled on the published international standard for sensitive species data, not on
house rules — decides what may be shown and how much it must be blurred, delayed or withheld.
The gate fails closed: a species with no classification cannot be published at all, and a map
layer physically cannot be built without a clearance. A wolf, for example, has a page that
says its locations are held back, and explains why.

*Where this goes next:* a built-but-unused path exists for asking a data owner's permission to
show more than the default policy allows (#50). It matters mainly for one elk dataset.

## 3. The lake and the ledger

All ingested data lands in one structured store — the lake — and every number the site shows
is recomputed from the lake on every build. Nothing is typed in by hand; a guard test even
fails the build if the README's own counts drift from what the pipeline computes. On top of
the lake sits the findings ledger: nine findings today, each carrying a plain-language
sentence, the precise claim, its scope, its caveat, and a structured bias assessment. Null
results are findings too — "fish are not all moving polewards" is published with the same
weight as "autumn migration is earlier".

*Where this goes next:* the newest findings — the predictability results — exist as ledger
entries but not yet as drawn map layers; that drawing is part of the presentation rebuild
(section 7).

## 4. The environmental drivers

To ask *why* movement changes, the lake also holds the environment: temperature and rainfall
from weather archives, snow depth at the herds' ranges, forty-one years of satellite
vegetation greening (the "green wave" of spring), the Arctic ice edge, sea-surface temperature
over each fish survey's fishing grounds, the large-scale climate patterns (El Niño and its
relatives), and — unusually — the actual seasonal *forecasts* that were issued in past years,
kept so predictions can be tested against what was knowable at the time. Every one of these
came through the same registry door with its licence verified first.

*Where this goes next:* a "climate velocity" driver (how fast warm water moves across the map,
rather than how much it warms in place) is the named next candidate for the marine work, and
one climate index the source agency stopped updating will be computed in-house instead.

## 5. The measurements — what has actually been learned

The first research phases measured change with published, pre-registered methods. In plain
terms: autumn bird migration over the United States runs about half a day earlier each decade,
and most of the temperature-linked part of that shift is attributable to human influence.
Fish, measured across two thousand species, are *not* all moving polewards — different seas
are doing different things. Southern African bird ranges showed no net change between two
atlas eras. Two collared herds travel no further between winter and summer than they did
twenty years ago — measured with a method designed so that changing GPS collars cannot fake a
trend. And several things the data cannot measure were established as firmly as the results:
collar records cannot carry timing trends, and the project's own coverage is heavily northern.

*Where this goes next:* write-ups of the two most original pieces (the human-attribution
method and the per-claim bias display) wait deliberately on further literature checks, and a
fourth data type for the cross-realm comparison test is a registered search.

## 6. The models — prediction, tested the hard way

This is the newest arc, and its rule is that every experiment is registered in writing —
question, method, predictions, and conditions for stopping — *before* any result is seen. Five
such experiments have now run, each exactly once:

- **The predictability atlas** asked where next year's migration timing can be predicted from
  the environment at all. Answer: almost nowhere — autumn timing beats chance at 20 of 143
  radar stations, spring nowhere, and the map is published mostly empty, because the empty
  cells are the finding.
- **The marine version** stopped itself twice, exactly as designed: first when most long fish
  surveys turned out to have changed fishing gear mid-record, then when most of the rest
  turned out never to have recorded water temperature. Each stop produced a precise reason and
  a registered successor (the satellite-temperature version is running now).
- **The coupling experiment** — what moves together across realms? — included two calibration
  tests of known signals. One passed, one failed, so by its own rules it drew no conclusions
  from its main questions. The machinery works; the series are short.
- **The dress rehearsal** answered the owner's question "would a public annual prediction have
  worked?" without waiting years: it re-ran the full prediction pipeline on 2017–2024 using
  only the actual forecasts issued each June, blind to the outcomes. The forecasts carry real
  signal; the prediction still failed to beat chance. **The standing public prediction was
  therefore refused a licence** — the site bet against itself and won, and a year of
  publishing noise was saved.

*Where this goes next:* the step-selection study (registered, not yet run) asks what an
individual animal's next two hours cost and buy — terrain, snow, greenness. It is also the
route to a stronger response model; the moment one exists, the dress rehearsal re-runs
unchanged and the public-prediction question reopens on evidence.

## 7. The map and the coming rebuild

Today's frontend is a hand-drawn field notebook over a globe: claim pages with their caveats,
a searchable page per species, layers that move through the year on a shared clock — radar
flow arrows, herd surfaces, fox journeys, the ice edge, the breathing green wave. The rebuild
now planned (its design decision record is written) turns this into a book: an introduction
first, chapters as thumb tabs ordered as the argument — what changed, what did not, what we
cannot see, what can be predicted — and, replacing the globe as the main canvas, a flat
scrollable world map in the style of an old hand-drawn chart, where the coverage gaps are
drawn as the map's own "here be dragons". One technical question — how to treat the polar
regions on a flat map — is deliberately left to a visual test rather than argued in advance.

*Where this goes next:* the projection test, then the book's shell, then the chapters, then
the world. Two long-standing interface defects (a panel covering the map buttons on phones,
and a Play button whose year ran too slowly to see) were fixed this week.

## 8. How the work is done

Three habits explain most of this document. Everything is *pre-registered* — designs are
written and committed before results are seen, and a wrong registration is corrected in
public, never silently edited. Everything *recomputes* — no published number is typed by hand.
And every claim carries *its limits as part of the claim* — scope, caveat, and bias assessment
are required fields the code will not compile without. The practical consequence, visible
throughout this snapshot: most of what this project has proven is where the edges of its own
knowledge are, stated precisely — which is what makes the few positive results worth trusting.
