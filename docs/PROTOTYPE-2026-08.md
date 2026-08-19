# The prototype, explained — a snapshot taken 2026-08-19

What Migratlas is today, part by part, with the datasets named and the choices explained.
Written for a reader who does not live in the code, but who wants the real detail — so
technical ideas are explained rather than avoided. Every part ends with *where this goes
next*. Counts and results are this date's snapshot; the live site recomputes its own.

## What this is, and how it is built

Migratlas is an interactive map of animal movement backed by a research pipeline. It tries to
answer four questions honestly: where animals are, how their movements have changed over
decades, what is driving the change, and whether any of it can be predicted.

One early architectural choice shapes everything: the site is **static**. All heavy
computation happens in advance, producing plain files a browser can download — there is no
application server to run, secure or pay for. A consequence with teeth: every number shown is
recomputed from the raw data on every build. Nothing is typed in by hand, and a guard test
fails the build if even the README's own counts drift from what the pipeline computes (they
drifted twice when typed freehand, which is why the guard exists).

The second defining habit: limits are published with the same weight as results. Empty map
cells, failed predictions and analyses that stopped themselves are treated as findings.

## 1. The library of sources — what is actually in it

Thirty-one sources are registered today. Registration is a real door: a source enters only
with its licence, citation, known problems and sensitivity classification written down first,
and the public credits document is generated from that registry and tested for drift. A tour,
by realm:

**The air.** The backbone is the US weather radar network — about 160 stations whose nightly
echoes, processed by ecologists, measure the sheer mass of animals aloft from 1995 to 2025.
One honest limit shapes every claim built on it: radar sees *biomass*, not species. It cannot
tell a bird from a bat from a moth, so no claim from this data ever quietly says "birds". The
same network also provides the direction and speed of movement each night, which the site
draws as small arrows that turn with the seasons.

**The sea.** FISHGLOB is a harmonisation of 29 bottom-trawl surveys — research ships towing
standardised nets — covering roughly two thousand fish species, some surveys running since the
1960s. A detail that later became decisive: each haul records the temperature of the water it
fished in. When the project needed a "warming" measurement per sea, it chose this in-situ
record over any satellite product, on the principle that *the water the fish were actually in*
beats an estimate — satellites struggle exactly where trawls operate, near coasts. Alongside
it: a global marine species atlas (OBIS), and the newest arrival, the Continuous Plankton
Recorder — a British institution that has towed silk-mesh samplers behind merchant ships since
the 1940s. Its story is a licence story: the famous UK archive is published under a
non-commercial licence that would poison anything derived from it, so the project uses the
same survey's western-Atlantic share, republished in the US under a fully open licence —
90,038 samples, 1958–2022. And a modelling choice: the file names its 413 plankton types by
internal codes that match no reference list the project holds, so rather than guess at names,
each sample enters as *one aggregate plankton measurement*. The analysis that needed it (bloom
timing) needs no species names, and a wrong name would be worse than none.

**The land.** Two southern African bird atlases (SABAP1 and 2) — tens of thousands of citizen
observers, two eras, which allowed a rare before/after comparison across 512 species. The
North American Breeding Bird Survey. And GPS collar studies from the Movebank archive, chosen
for their open licences: the Ya Ha Tinda elk of the Canadian Rockies (206 animals, 2001–2024),
Svalbard's reindeer (116 animals), the Arctic foxes of Bylot Island, plus caribou, bison and
wolves. The wolves illustrate the safety gate below: they are registered, analysed — and
withheld from the map, with a page saying so. An honest limitation, stated in the registry:
these herds are *residents*, collared for other studies. A genuinely migratory tracked species
with an open licence is a standing search.

**One deliberate absence.** eBird's modelled abundance maps are used for analysis but never
shown: their licence forbids redistribution, and the gate enforces licences as strictly as
safety.

**The environment.** To ask *why* movement changes, the lake holds the environment too:
temperature and rainfall from the ERA5 climate archive; snow depth at the herds' ranges from
its land-surface sibling (with a trap documented in code: two products publish under the name
"snow depth", and only one means actual snow thickness); forty-one years of satellite
vegetation greening — the "green wave" of spring — from a Peking University dataset, 2.4 GB of
imagery reduced both to an average year for display and to per-year green-up dates for
modelling; the Arctic ice edge, month by month; sea-surface temperature over each fish
survey's own fishing grounds; the great climate see-saws (El Niño, the North Atlantic
Oscillation and their relatives) as monthly index numbers; and — unusually — the *actual
seasonal forecasts issued in past years* by Europe's weather centre, archived so that
predictions can be tested using only what was knowable at the time. Two climate-model products
provide "worlds without us": one simulates history with human influence removed, the other
statistically strips the warming signal from observations — two different kinds of
counterfactual, kept side by side deliberately, because agreement between them is stronger
evidence than either alone.

*Where this goes next:* the migratory-species search; a "climate velocity" driver (how fast
warm water moves across the map, not just how much it warms in place); and one climate index
whose agency stopped updating it in 2023 will be computed in-house from raw ocean data instead
of quoted stale.

## 2. The safety gate

Publishing animal locations can get animals killed — poachers read maps too. Before anything
is drawn, an automatic gate decides what may be shown. Its design choices:

- It implements a **published international standard** (GBIF's best practices for sensitive
  species data) rather than house rules, for the same reason a bank follows accounting
  standards: credibility that an in-house policy cannot have.
- Sensitivity is judged per **species × environment × data type**, not per species alone — a
  shark sighting and a shark's satellite track are very different disclosures.
- Protection means **aggregation and delay, never random nudging** of points. A study showed
  that naively "jittered" camera-trap locations could be narrowed down to about 13% of the
  claimed area using public satellite imagery; blurring that can be un-blurred is not
  protection. So herd maps show only grid cells backed by at least three different animals,
  fox routes are coarsened so no den resolves to a point, and recent positions are delayed.
- The gate **fails closed**: a species with no classification cannot be published, and a map
  layer physically cannot be built without a clearance object that only the gate can create.

*Where this goes next:* a built-but-unused path for asking a data owner's permission to show
more than default policy allows — in practice relevant to one elk dataset.

## 3. The lake and the findings ledger

All ingested data lands in one structured store — the lake — in a common format with the
species, place, time and provenance columns standardised, so every analysis reads every source
the same way. A hard-won operational rule is enforced in code: a write replaces whole
partitions, so two datasets must never share a partition unless written together (this once
silently deleted five years of one record, twice, before the rule was learned).

On top sits the **findings ledger** — the project's actual product. Nine findings today. Each
carries, as *required* fields the build will not pass without: a plain-language sentence (with
a strict rule — the plain version may drop precision but may never claim more than the precise
one); the precise claim; the number with its uncertainty; the scope (where and when it holds);
the caveat (what would make it wrong); and a structured bias self-assessment answering six
standard questions from a published framework — where the data comes from, when, which
species, which environments, how detection could fool us, and how timing definitions could.
Null results are full findings: "fish are not all moving polewards" is published with the same
weight as "autumn migration is earlier".

*Where this goes next:* the newest findings — the predictability results — exist as ledger
entries but not yet as drawn layers; that drawing belongs to the rebuild in section 7.

## 4. The measurements — what has been learned, and the choice behind each

**Autumn migration is earlier.** Over the mid-latitude United States, nocturnal autumn passage
has advanced by about half a day per decade (−0.56 ± 0.25). The method choice: before claiming
anything new, the pipeline first *reproduced a published study on its own years* — matching a
known result is what makes an extension believable. Spring shows no detectable trend, and a
strange instrument-linked step in the southern stations around 2012 was tested against four
explanations, all of which failed — those stations are excluded from every claim, and the
mystery is published as an open problem rather than smoothed over.

**About half of that shift is attributable to human influence.** Using the "worlds without us"
described above: of the portion of the advance that tracks pre-season temperature, essentially
all is attributable to human forcing (−0.30 of the −0.56 days per decade). Stated that
narrowly on purpose — the other half of the advance does not track temperature at all and
remains unexplained, and the site says so.

**What flies did not change — a control.** The airspeed of whatever the radar sees has been
flat for thirty years. That matters because it rules out the worry that the timing shift is
just the radar seeing *different things* (more insects, say) rather than the same things
earlier.

**Fish are not all moving polewards.** Across ~2,240 species-survey combinations, the average
shift is indistinguishable from zero — because different seas move in *opposite directions*.
The heterogeneity was later promoted from caveat to research question in its own right.

**Southern African bird ranges show no net change** between the two atlas eras (median change
in occupancy essentially zero across 512 species) — with detection-rate corrections chosen *in
advance* to arbitrate if raw and corrected numbers disagreed.

**Two herds travel no further than they used to.** The elk and reindeer cover the same
winter-to-summer distance as twenty years ago. The design choice here is the project in
miniature: GPS collars changed over the years, and a collar that reports more often records a
longer *path* for the same journey — the path length of these elk tracks is 52-fold
contaminated by sampling changes. So the measure chosen was the straight-line distance between
each animal's winter spot and summer spot, which cannot care how often the collar spoke — and
the analysis *proved* that immunity by thinning the data and showing the measure doesn't move.
An earlier phase had already shown the brutal version: changing collar type shifts a measured
migration date by 46.8 days. Timing questions from collars are closed in this project, and
that closure is enforced in every later design.

**The map knows where it is blind.** 35.9% of the animal time-series rows are from the
southern hemisphere — but only about 1% of the environmental driver data is. That asymmetry is
published as a finding (the camera deliberately points at the emptiness), and a
"detectability" wash on the map shows where absence of records means absence of looking.

*Where this goes next:* write-ups of the two most original pieces (the attribution method and
the per-claim bias display) wait deliberately on further literature checks; a fourth data type
for the cross-realm comparison is a registered search.

## 5. The models — prediction, tested the hard way

The newest arc. Its governing rule: every experiment is **pre-registered** — the question, the
exact method, numbered predictions, and stopping conditions are written and committed *before
any result is seen*. If the registration turns out wrong, it is corrected in public, never
edited away. Five experiments have now run, each exactly once:

**The predictability atlas.** For each radar station, a deliberately simple model was trained
on the early years and asked to predict migration timing in the recent years it had never
seen, from temperature, rainfall and the climate see-saws. Fairness devices: the recent "test
years" are touched once, ever; and every station's skill is compared against a "chance bar" —
the same model fed deliberately shuffled years, a thousand times, to measure what luck alone
produces. The result: autumn timing beats chance at 20 of 143 stations; spring, nowhere —
despite spring being the season the scientific literature expected to be predictable. Two of
the experiment's own predictions were thereby graded false, and published as false. A trend
over decades, it turns out, is a different thing from year-to-year predictability — this
design measured the difference.

**The marine version stopped itself twice — as designed.** First attempt: most long fish
surveys changed their fishing gear mid-record, and a gear change shifts what gets caught in
ways that can fake a trend, so those surveys were excluded and too few remained. The salvage
was measured, not guessed: taking each survey's longest *unbroken same-gear stretch* recovers
17 usable series (one survey contributes an unbroken 46-year run that the cruder rule had
discarded). Second attempt, on those stretches: most European surveys, it turned out, never
recorded water temperature — fish without their water — and the count fell below the
registered minimum again. Each stop produced a precise, published reason. The successor —
using satellite sea-surface temperature over each survey's own fishing grounds, gated by a
check that satellite and shipboard thermometers agree where both exist — ran the same day and
delivered the answer: the thermometers agree, the seas genuinely differ (a heterogeneity score
nearly ten times its chance bar across 18 seas), and warming alone does not sort the movers
from the stayers.

**The coupling experiment.** The owner's founding intuition: migrations are connected — birds
follow food, fish follow plankton, everything follows the climate see-saws. The honest way to
test connections in short yearly records (where two series that merely both warm will *look*
connected) was worked out from a literature review first: no fishing expedition through all
possible pairs, but four specific, pre-registered links — two of them *calibration links*,
known from decades of science, included to test whether the method can see anything at all.
One calibration passed cleanly (warmer springs shift the plankton bloom). One failed (a famous
Atlantic climate pattern is invisible in continental-average greening at this length). By its
own registered rule, the experiment then declined to interpret its main questions. Also
recorded there: the project makes **no novelty claims** for this work — the one review that
could adjudicate is paywalled, so the claim was removed rather than gambled on.

**The dress rehearsal — the owner's idea, and the arc's best result.** The plan had been a
standing annual prediction, publicly graded each year. The owner asked: why not first predict
the recent past, blind, and see if it works? So the full pipeline stood at June 1st of each
year 2017–2024, trained only on earlier years, took the seasonal forecast *actually issued
that June* from the archive, predicted that autumn's migration timing, and was graded against
reality — eight verdicts in one afternoon instead of one per year. Fairness device: each
year's prediction was also compared against the same machinery fed the *wrong years'*
forecasts, to measure luck. The verdict: the weather forecasts themselves carry real signal —
but the migration prediction still failed to beat chance. **The standing prediction was
refused its licence.** The site bet against itself, won, and saved a year of publishing noise.
The refusal is re-openable: it re-runs unchanged the day a stronger model exists.

*Where this goes next:* the registered-but-not-yet-run step-selection study asks what an
individual animal's next two hours cost and buy — using terrain, snow depth and greenness at
each step, comparing where the animal went against ten places it could have gone. (One honest
exclusion already made: the foxes' collars record in sub-hourly bursts — a different kind of
movement record — so they wait for a design of their own.) This study is also the route to the
stronger prediction model the rehearsal is waiting for.

## 6. The map today, and the rebuild

What the globe currently draws, all on one shared year-clock: the radar's weekly passage
surface with its turning direction arrows; the elk and reindeer as weekly presence surfaces
(860 and 1,394 protected grid cells); 217 Arctic fox journeys as coarsened lines; the ice edge
as 24 monthly contours; the green wave breathing across 14,308 vegetated cells; a searchable
page for every analysed species, cross-linked to the claims its data feeds; and the
detectability wash showing where the world went unobserved.

The planned rebuild (its design decision record is written) turns the site into a **book**: an
introduction first; chapters as thumb tabs, ordered as the argument — *what changed, what did
not, what we cannot see, what can be predicted, the world*; and, replacing the globe as the
main canvas, a flat scrollable world map in the manner of an old hand-drawn chart, where
coverage gaps are drawn as the map's own *here be dragons*. One question is deliberately
parked behind a visual test rather than argued: how a flat map should treat the poles, where
the reindeer and the ice live — the options (a clamped map, or a small polar inset like a
chart's corner globe) will be decided by looking at rendered pixels, a house rule learned the
expensive way.

*Where this goes next:* the projection test, the book's shell, the chapters, the world — and
the predictability results drawn as the mostly-empty map they honestly are.

## 7. How the work is done

Three habits explain everything above. **Pre-registration**: designs committed before results
are seen; wrong registrations corrected in public. **Recomputation**: no published number
typed by hand, ever. **Limits as part of the claim**: scope, caveat and bias assessment are
required fields, not footnotes. A fourth habit runs quieter but appears throughout this
snapshot: **measure before deciding** — the gear salvage was counted before it was designed
around, the projection question waits on pixels, and one measuring instrument was itself
caught misbehaving only because a measurement was run twice and compared. The practical
consequence: most of what this project has proven is where the edges of its own knowledge are,
stated precisely — which is exactly what makes its positive results worth trusting.
