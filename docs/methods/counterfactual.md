# The counterfactual ribbons

`phase2a-attribution.md` reduced a causal chain to one number: `f = 0.98`, the human share of the
warming the animals tracked. `phase2a-attrici.md` then asked the same question of different evidence
and got a number **2.4× smaller**. This note records how two numbers became two pictures, what each
is drawn to, and why the distance between them is shown rather than resolved.

No new estimate. Every quantity is recomputed from the functions the two attributions publish —
`attribution.chosen`, `attribution.observed`, `phase2a_attrici.attributed` — so the charts cannot
drift from the ledger by being edited.

## Two ribbons, one question each, two lines each

| ribbon | question | how it answers | counterfactual slope |
| --- | --- | --- | --- |
| DAMIP | no human *forcing*? | 15 CMIP6 models run with and without it | −0.264 d/decade |
| ATTRICI | no *warming*? | the observations, detrended against global mean temperature | −0.438 d/decade |

Both draw the same observed line, −0.559 d/decade, because there is one record and one fit. Within a
ribbon both lines pass through the window mean at the midpoint: the attribution constrains **slopes**
and says nothing about levels, so anchoring at one end would open a gap a reader would read as a
difference between scenarios rather than as a drawing choice.

### Why not one chart with four lines

Schema 1 drew three lines in one chart, and two of them came from the same DAMIP ensemble —
`observed − f·S×W` against `observed − S×W`, with `f` at 0.98. They sat **0.006 days apart**: one
piece of evidence drawn twice, which a reader takes for corroboration. The near-coincidence was
described at the time as `f = 0.98` rendered, which it was — but a second line that *cannot* disagree
with the first is not evidence.

So the third line was dropped and replaced by a real independent counterfactual. And that one is
drawn in **its own chart**, not as a fourth line, because four lines where two nearly coincide and two
sit far apart invites a reader to average them — and averaging is the single thing that must not happen
here. These are different quantities, not two estimates of one.

`tests/test_counterfactual.py::test_no_ribbon_restates_another` holds the door shut: two
counterfactual slopes within 0.05 d/decade of each other fail the suite.

## What the axes are scaled to

**The observed points, not the gap between the lines** — and **one frame for both charts, not one
each.**

DAMIP's lines part by **0.89 days** and ATTRICI's by **0.29**, inside a year-to-year scatter of
several days. Two things follow:

- Scaled to its own gap, either panel would fill with a dramatic diverging wedge and teach a reader to
  expect one from every attributed signal. Scaled to the scatter, the reader sees what a real
  attributed trend looks like: a fraction of a small signal sitting inside large natural variability.
  It is still a signal.
- Scaled to *its own* extents, each chart would render its gap at the same height as the other's. The
  reader would see two counterfactuals agreeing, where the whole finding is that they do not.

The horizontal axis is shared for the same reason. DAMIP runs to 2025 and ATTRICI's counterfactual
ends in 2019, so fitting each chart to its own window would stretch the shorter one and make a
shallower slope look steeper. Sharing the axis costs ATTRICI's chart an empty right-hand quarter,
which is the point: the reader watches the evidence run out six years early instead of reading about
it in a caption.

### Each chart shades where its own attribution stops

And it is *not* the same year as the drawing window, which is the correction that turned one shaded
chart into two. The first version shaded only ATTRICI — the chart whose counterfactual visibly ran
out — and left DAMIP's running clean to 2025. But `f` is a **scalar fitted to 1995–2014**, because
CMIP6's `historical` runs stop there, and it is then applied to the whole observed trend. DAMIP's
counterfactual line runs eleven years past anything that constrained it, and nothing about a drawn
line distinguishes fitted from carried-on.

So `Ribbon.attributed_through` is a field, both charts shade from it, and the labels distinguish the
two kinds of limit:

| ribbon | attributed through | label | what the line does in the band |
| --- | --- | --- | --- |
| DAMIP | 2014 | *share fitted only to 2014* | continues, on an extrapolated ratio |
| ATTRICI | 2019 | *no counterfactual after 2019* | stops, because the series does |

The observed points still show inside the band and sit on top of the tint: the observations exist
there, and it is the attribution that does not reach.

`globe.spec.ts` measures all of this on the rendered SVG — each drawn gap under 35% of the drawn
scatter, identical tick heights across charts, the two gaps rendering at *different* pixel heights,
both charts carrying a band, the bands starting at *different* years, no label printing past the
chart's own box, and both of a ribbon's lines ending at the same x. Every one of those is a property
of the picture rather than of the data, and three of them were bugs found by looking at a screenshot,
which is not a thing that runs in CI.

One correction inside that decision. The first version set the range from the points **plus their
intervals**, and those reach ±3.1 days on the sparsest years. But that interval is a 95% interval on a
mean across stations: a wide one says few stations reported, not that the animals were erratic.
Letting it set the frame widened the axis to about fifteen days and squeezed the entire 1.7-day
observed trend into seven pixels — hiding a real result to make room for an artefact of sampling. The
frame is the points; the bars are clamped into it; and the years whose intervals overflow are named in
a line under the chart rather than left as a visual oddity.

## Neither counterfactual is flat, and that is a decision

Each removes only what its own method attributes. About half the observed advance does not track
temperature at all and was never attributed to anything, so it survives into both counterfactuals and
both lines still advance.

Flattening either would be the easier picture and a false one: it would claim the unexplained half is
natural, and nothing in the analysis establishes that. The suite asserts each counterfactual keeps at
least a quarter of the observed advance, so a later change in service of a cleaner-looking chart fails
the tests rather than the reader.

## The disagreement is the payload

Two attributions of one advance that differ by a factor of 2.4, shipped without an explanation, would
be worse than shipping either alone. So the explanation is a field of the document
(`Comparison.disagreement`), it renders at body size in a bordered block *after* both charts, and a
test asserts it is set larger than the footnotes around it. It also has to quote magnitudes: a
"disagreement" described without a number explains nothing, and the suite checks for digits.

What it says, in the shape the data puts it:

- `f` is a ratio of **ensemble-mean forced** signals. Averaging 15 models cancels the year-to-year
  weather, so what the ratio divides into is close to a pure forced response.
- ATTRICI detrends **one 0.5° cell's actual daily series**, where a 25-year trend is largely weather
  that happened to lean one way. Only ~38% of it moves with the global mean.
- So the distance between the ribbons says roughly **59% of the warming at these stations does not
  follow the global mean at all**. Over 25 years at one cell that is mostly variability — but it also
  holds any forcing that does not scale with the global average, so **it is an upper bound on the
  chance part, not a measurement of it.** Stated that way because the looser reading is the one that
  would get repeated.

The same comparison is computed into the `anthropogenic-share` caveat in `reports/findings.py`, so a
reader who never opens the figure still meets it beside the number it qualifies.

### If the second ribbon is not there

ATTRICI's factual half has to reproduce the ERA5 warming already in the lake before its counterfactual
half may be read — pre-registered as a stop condition, and it passes at −0.033 °C/decade against a
combined interval of 0.097. If it ever stops passing, `collect()` publishes DAMIP alone and the
`disagreement` field says so in words. A run that lost a ribbon to its own control reads as a result,
not as a shorter list.

## What the ribbons must not be read as

- **Not a statement about any single year.** The attribution is of the trend. No year's passage date
  can be called human-caused, and the shared caveat on the panel says so.
- **Not a claim about the animals.** Both response functions are observational: they attribute the
  warming the animals tracked, not the animals. A confounder common to both temperature and passage
  date survives either counterfactual, and a second climate counterfactual does not touch that.
- **Not the whole advance.** Half of it remains unexplained, and both charts show that half surviving
  into the counterfactual instead of quietly folding it into the attributed share.
- **Not two estimates of one number.** They are not averaged, and they do not adjudicate each other.

## Still owed

Before any public novelty claim about applying impact attribution to movement timing: read the 2026
*Nature Reviews Biodiversity* migratory-species review, which is paywalled and is the likeliest place
a precedent is cited.
