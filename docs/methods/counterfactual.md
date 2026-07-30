# The counterfactual ribbon

`phase2a-attribution.md` reduced a causal chain to one number: `f = 0.98`, the human share of the
warming the animals tracked. This note records how that number became a picture, and what the picture
is drawn to.

No new estimate. Every quantity is recomputed from the same functions the attribution published —
`chosen`, `observed`, `Fraction.difference` — so the chart cannot drift from the ledger by being
edited.

## Three lines

| line | slope | what it is |
| --- | --- | --- |
| what happened | −0.559 d/decade | the fitted trend at the claim-band stations, and the number the ledger publishes |
| without human forcing | −0.264 d/decade | observed minus `f × S × W`, the attributed human share |
| with no warming at all | −0.258 d/decade | observed minus `S × W`, the whole thermal response |

All three pass through the window mean at the midpoint. The attribution constrains **slopes** and says
nothing about levels, so anchoring at one end would open a gap that a reader would read as a
difference between scenarios rather than as a drawing choice.

The two counterfactuals sit almost on top of each other, and that near-coincidence *is* `f = 0.98`
rendered: almost none of the warming the animals tracked was natural. It also gives the chart a free
internal check — if the ordering ever inverted, the arithmetic would be claiming natural forcing
warmed the world more than all forcing did.

## The counterfactual is not flat, and that is a decision

It removes only what was attributed. About half the observed advance does not track temperature at
all and was never attributed to anything, so it survives into the counterfactual and the line still
advances at −0.26 d/decade.

Flattening it would be the easier picture and a false one: it would claim the unexplained half is
natural. Nothing in the analysis establishes that. `tests/test_counterfactual.py` asserts the line
keeps at least a quarter of the observed advance, so a later change in service of a cleaner-looking
chart fails the suite rather than the reader.

## What the axis is scaled to

**The observed points, not the gap between the lines.** Over the 30-year window the two lines part by
**0.89 days**, inside a year-to-year scatter of several days. Scaled to the gap, the panel would fill
with a dramatic diverging wedge and teach a reader to expect one from every attributed signal. Scaled
to the scatter, the reader sees what a real attributed trend looks like: a fraction of a small signal
sitting inside large natural variability. It is still a signal.

A browser test measures this on the rendered SVG — the drawn gap must stay under 35% of the drawn
scatter — because it is a property of the picture, not of the data, and only the picture can be
checked for it.

One correction inside that decision. The first version set the range from the points **plus their
intervals**, and those reach ±3.1 days on the sparsest years. But that interval is a 95% interval on
a mean across stations: a wide one says few stations reported, not that the animals were erratic.
Letting it set the frame widened the axis to about fifteen days and squeezed the entire 1.7-day
observed trend into seven pixels — hiding a real result to make room for an artefact of sampling. The
frame is now the points; the bars are clamped into it; and the three years whose intervals overflow
(1995, 1998, 2021) are named in a line under the chart rather than left as a visual oddity.

## What the ribbon must not be read as

- **Not a statement about any single year.** The attribution is of the trend. No year's passage date
  can be called human-caused, and the caveat on the panel says so.
- **Not a claim about the animals.** The response function is observational: it attributes the warming
  the animals tracked, not the animals. A confounder common to both temperature and passage date
  would survive this entirely.
- **Not the whole advance.** Half of it remains unexplained, and the chart shows that half surviving
  into the counterfactual instead of quietly folding it into the human share.

## Still owed

A second, independent counterfactual. ATTRICI/ISIMIP3a removes the warming-correlated signal from
*observations*, so it carries no model bias and preserves internal variability by quantile. DAMIP asks
*what if there had been no human forcing*; ATTRICI asks *what if there had been no warming*. Reporting
both, and any disagreement between them, would be stronger than either — and the third line here is
only a within-DAMIP stand-in for the second question.

Before any public novelty claim about applying impact attribution to movement timing: read the 2026
*Nature Reviews Biodiversity* migratory-species review, which is paywalled and is the likeliest place
a precedent is cited.
