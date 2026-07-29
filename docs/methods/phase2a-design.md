# Phase 2a design — species by species, and drivers that act through other species

**Status:** design, fixed before any model is fitted. Recorded 2026-07-29.

Two requirements shape everything below, and both were stated as requirements rather than
discovered:

1. **A species is the unit.** Migrations differ enormously between species, and a result that is
   only a pooled median hides exactly the variation worth predicting. The low level is one species'
   movement; the high level is which drivers recur across species. Both are deliverables, and the
   second is meaningless without the first.
2. **The driver need not touch the animal.** A seabird's movement can change because warmer water
   pushed plankton deeper, so forage fish left, so there was nothing to eat. The cause is a water
   temperature acting through two intermediate populations, and a model offered only variables that
   touch the bird directly cannot find it.

Phase 1b is already the evidence for the first: 2,240 species-survey pairs whose pooled median is
−0.011 °lat/decade and indistinguishable from zero, while individual surveys reach −0.22 and +0.26
in opposite directions. Pooling destroyed the finding. Every model here reports per species first.

## Model shape: per species, with shared structure

Not one pooled regression, and not thousands of independent ones.

```
response(species s, site i, year t)
    ~ sum_k  beta[k, s] * driver[k, i, t - lag_k]   +  b[s] + b[site] + e
    beta[k, s] ~ Normal(mu_k, tau_k)
```

Each species gets its own coefficient on each driver. The *population* of those coefficients answers
the high-level question: `mu_k` is how much driver `k` matters on average and `tau_k` is how much
species disagree about it. A driver with a large `mu` and small `tau` acts on everything; one with
`mu` near zero and large `tau` acts strongly but in opposite directions on different species — which
is a real and interesting answer, and one a pooled model reports as "no effect".

Partial pooling is what makes a species with twelve usable years estimable at all. Independent
per-species fits would give it a wild coefficient and equal weight; a single pooled fit would give
it no voice. This is the same argument that made the Phase 1a hierarchical model worth building, and
`models/trends.py` already has the machinery.

## Driver catalogue

Three kinds, distinguished in the driver table by `kind` so they can never be mixed silently.

**Measured** — recorded by the same instrument that observed the animal. Already in the lake:
FISHGLOB's per-haul sea-surface and bottom temperature, 240,325 samples. The best kind, because
there is no interpolation between the reading and the animal.

**Gridded** — sampled out of a reanalysis or satellite product at the observation's position and
time, which is what `features/annotate.py` is for. Planned, in rough order of expected value:

| Driver | Product | Why |
| --- | --- | --- |
| air temperature, 2 m | ERA5 | the direct thermal cue for aerial migration timing |
| wind at 850 hPa | ERA5 | a night's passage is largely wind support |
| precipitation | ERA5 | rainfall gates insect emergence and grassland green-up |
| surface pressure | ERA5 | migrants depart on pressure changes, not on absolute pressure |
| vegetation green-up (NDVI/EVI) | MODIS/Sentinel | the terrestrial food supply, and the classic mismatch axis |
| chlorophyll-a | ocean colour | **the plankton term in the seabird pathway above** |
| sea ice concentration | passive microwave | the Arctic constraint |
| sea-surface temperature | OSTIA/CMEMS | marine thermal, where in-situ is absent |

**Derived** — an index computed from this lake's own evidence, which is how an indirect pathway is
expressed at all. "Abundance of this forage fish, in this cell, this year" becomes a driver of a
seabird's movement, with `derived_from` recording the source and taxon so the pathway can be traced
to observations rather than asserted. This is the mechanism that makes cross-taxon questions
possible, and it is why the driver table is long-format and open-ended rather than a column per
variable.

## Lags, because a trophic pathway is not instantaneous

Warmer water this spring moves plankton within weeks, forage fish within a season, and a seabird's
breeding-season distribution possibly a year later. A model with only same-period drivers cannot
find a chain it takes a year to propagate, and will instead report the direct term that happens to
be correlated.

So each driver enters at a pre-registered set of lags, and the lag structure is stated per pathway
rather than searched. Searching lags across drivers and species is a multiple-comparison machine
that will always find something.

## The part that needs discipline: identifiability

Being able to add every driver in the world is not the same as being able to tell which one acts.
Temperature, pressure, rainfall and chlorophyll are mutually correlated, often strongly, and with
thousands of species the number of coefficients is large. A regression on correlated predictors
distributes credit between them arbitrarily; running it across many species and reporting the
largest coefficients would produce confident nonsense, reliably.

Three commitments, fixed here:

1. **A DAG before a regression.** The pathway is stated first — *sea temperature → chlorophyll →
   forage fish → seabird distribution* — and then the links that are observable are each tested.
   That is mediation, not a horse race between predictors, and it makes "which driver matters" a
   question about a stated pathway rather than about coefficient magnitudes.
2. **Report what is not identifiable.** Where two drivers are collinear beyond separating, the
   honest output is that the pair matters and which one cannot be said. A variance-inflation
   threshold and the correlation matrix are published with every fit.
3. **The counterfactual carries the causal claim, not the regression.** CMIP6 DAMIP `hist-nat`
   against `historical`, pushed through the fitted driver response, is what turns an association
   into an anthropogenic fraction. The regression's job is the response function; the attribution
   comes from the experiment.

## What is testable now, and what is not

**Now, with data in hand.** The fish-and-temperature link: FISHGLOB gives per-species distribution
centroids and per-haul temperature over decades. Does a species' occupied temperature stay constant
while its latitude and depth move, or does it stay put and warm? That is thermal tracking, it is the
first link of the pathway above, and it needs no new source.

**Now, with one gridded source.** The aerial timing response — passage date against pre-season
warming, wind support and green-up — needs ERA5 and nothing else.

**Not yet.** The seabird end of the trophic example. Seabirds are in OBIS and MegaMove, and neither
has a time axis (`phase1b-marine.md`), so there is currently nothing to regress. The pathway's
first two links are testable and its last is not, and saying so beats fitting the part that is easy
and implying the chain.

**Never from this data alone.** That a change in one population *caused* a change in another.
Co-movement of two indices over thirty years, with a shared climate driver, is the textbook
confounded case. The DAG and the counterfactual are what make a causal statement possible; a
correlation between two taxa is a hypothesis about a pathway, and gets reported as one.

## Geographic scope

Every commitment in `geographic-coverage.md` applies here: skill under leave-one-region-out splits
on the held-out region, and a geographic novelty mask on anything predicted outside the training
regions. Phase 1b's surveys disagree in the sign of shift, so a driver response fitted in one region
is not assumed to hold in another — `beta[k, s]` may need a region index as well as a species one,
and whether it does is an empirical question to report rather than to assume either way.
