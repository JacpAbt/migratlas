# Literature and state of the art, checked 2026-07-30

Done before committing to a direction, to answer three questions: is the counterfactual idea novel,
is forecasting as weak as I claimed, and is the evidence-ladder frontend idea idiosyncratic. The
answers changed two of the three recommendations, and one of them substantially.

What was **not** verified is stated at the end. Where a claim rests on a search rather than on
reading the paper, it says so.

## 1. The counterfactual: the framing is standard, the application appears absent

**The framing is not ours and should not be presented as ours.** Impact attribution has a settled
definition — the IPCC AR5 one — which requires quantifying "the difference between the observed state
of the system and a counterfactual baseline that characterizes the system's behavior in the absence
of climate change". That is exactly what `f × S × W` computes, and exactly what a two-trajectory plot
would draw.

**There is dedicated tooling for it, and it is arguably better than what we used.**
[ATTRICI v1.1](https://gmd.copernicus.org/articles/14/5269/2021/) constructs counterfactual climate
by removing the global-mean-temperature-correlated signal from *observational* data, and ISIMIP3a
ships counterfactual forcing built this way from GSWP3-W5E5. Two properties matter for us:

- It is derived from observations, so it carries **no model bias at all** — where our DAMIP route
  needed the ratio construction precisely to cancel model bias.
- It **preserves internal variability by quantile**: a factual and a counterfactual day sit at the
  same quantile of their respective distributions, so individual years remain comparable rather than
  only trends.

**They are different counterfactuals and the difference is not cosmetic.** DAMIP `hist-nat` answers
*what if there had been no human forcing* — solar and volcanic only, a physical experiment. ATTRICI
answers *what if there had been no warming* — a statistical detrending that removes whatever is
correlated with global mean temperature, human or not. Running both and reporting agreement would be
a stronger result than either alone, and disagreement would be informative about how much of the
warming signal at these stations is not anthropogenic.

**On the application to migration.** Three searches found no study attributing migration timing to
anthropogenic forcing via a climate counterfactual. What exists is a well-populated correlational
literature — spring migration advancing ~2.1 days per decade and ~1.2 days per °C across North
America, short-distance migrants advancing more than long-distance ones, a documented and widening
[mismatch with green-up](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5432526/) — plus qualitative
attribution language in reviews ("birds are increasingly exposed to anthropogenic threats"). The
formal step from *correlated with temperature* to *attributable to human forcing* is the gap.

**This is a negative from searching, not from reading.** It is weaker evidence than the Phase 2a
scoop check, and the honest position is "no precedent found" rather than "no precedent exists". The
2026 *Nature Reviews Biodiversity* review of migratory birds (s44358-026-00177-7) is the one document
most likely to cite such work and it is paywalled; reading it is the next step before any novelty
claim is made in public.

## 2. Forecasting: confirmed weaker, and for a concrete reason

Short-horizon nightly forecasting is **occupied by an operational, free, better-resourced system**.
[BirdCast](https://birdcast.org/) runs a three-day migration forecast for the lower 48 with live
radar and eBird, plus per-county traffic, direction and speed. The research frontier is
[FluxRGNN](https://arxiv.org/html/2407.10259) (2024), a hybrid fluid-dynamics-plus-recurrent-GNN
model with mass conservation — and its own stated limitations are instructive: spatial resolution
"constrained by the typically sparse observations obtained from weather radars", and trainable
components that "lack explicit incentives to adequately predict take-off and landing events".

So on nowcasting we would be third, behind an operational service and a named research frontier,
using the same radar network. That is a bad place to spend the project's scarcest resource.

Long-horizon scenario projection remains available and uncontested by BirdCast, but it is the
crowded corner of the wider field and its honest output is bounded by the novelty mask — `S` is
fitted over a thirty-year envelope that SSP5-8.5 leaves entirely.

**Verdict: do the cheap version because ScenarioMIP is one experiment list away, present it with the
mask as an honesty exhibit, and do not make it the centrepiece.**

## 3. The evidence ladder is not idiosyncratic — it has a published spine

This is the finding that changed the frontend plan.
[**ROBITT**](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9541136/) — Boyd, R. J., Powney, G. D.,
Burns, F., Danet, A., Duchenne, F., Grainger, M. J., Jarvis, S. G., Martin, G., Nilsen, E. B.,
Porcher, E., Stewart, G. B., Wilson, O. J., & Pescott, O. L. (2022), *Methods in Ecology and
Evolution* 13(7), 1497–1507 — is a 17-question tool for assessing **risk of bias in studies of
temporal trends in ecology**, explicitly modelled on PRISMA. Its domains, in order:

1. Research statement and pre-bias assessment
2. Geographic bias assessment
3. Environmental bias assessment
4. Taxonomic (or other organismal axis) bias assessment
5. Other potential biases

and the biases it asks about are geographic, temporal, taxonomic, environmental, detectability and
phenological — each with the further question of whether coverage stayed *consistent over time*.

**We have been doing this without knowing the framework existed.** Phase 1a and 1c map onto it
almost line by line: geographic (the claim narrowed to 37–50°N), temporal (the 2012 step, coverage
thresholds), taxonomic (biomass not birds, bounded by the airspeed test), detectability (screening
severity, the speed-weighting control), phenological (the window definition matched to the published
metric). Phase 1b's consistent-footprint rule is ROBITT's "consistent over time" question answered
in code.

Two consequences:

- **The ladder should be ROBITT-shaped rather than invented.** Same move the ethics gate made by
  implementing GBIF's sensitive-species guidance instead of writing a policy: adopt the standard, and
  the artifact inherits its credibility.
- **A visual ROBITT is an opening.** The paper says the assessment "may be answered using text and/or
  figures" and expects it in prose alongside a study. An interactive, per-place, per-claim ROBITT
  rendering is a legitimate and, as far as this search goes, unbuilt thing.

Related and worth citing: [temporal trends in the *spatial* bias of occurrence
records](https://nsojournals.onlinelibrary.wiley.com/doi/10.1111/ecog.06219) — the exact reason the
OBIS latitude metric was refused — and 2026 work showing the Living Planet Index moves with
monitoring-quality thresholds through shifts in *representation* rather than through biased trends,
which is a caution for any index we might publish.

## 4. The coverage map: adjacent literature exists, our axis is different

There is a mature literature on biodiversity knowledge gaps —
[seven shortfalls](https://www.annualreviews.org/content/journals/10.1146/annurev-ecolsys-112414-054400)
(Linnean, Wallacean, Prestonian, Darwinian, Raunkiaeran, Eltonian, and Hutchinsonian), with published
completeness maps for particular taxa such as
[snakes](https://nsojournals.onlinelibrary.wiley.com/doi/10.1002/ecog.08589) and plants.

But those ask **do we know where species are**. Our question is **where could a change ever be
detected** — which needs a time axis, a repeated protocol and effort fixed by design, and is a
different and apparently unnamed axis. The distinction is worth keeping sharp because it is the one
our own audit already measures: `megamove` and `obis_speciesgrids` score well on Wallacean coverage
and cannot support a trend at all.

## 5. Recent work to track, not yet read

- **Plunkett et al. (2026)**, *Global Ecology and Biogeography*, "Novel Estimates of Bird Migration
  Traffic at the Continental Scale Using Participatory Science Data" — continental migration traffic
  from participatory data rather than radar. Directly adjacent to our response variable and to the
  eBird assembly idea. Read before designing anything that estimates traffic.
- **BirdFlow (2026)**, *Movement Ecology*, "Population-level migration modeling of North America's
  birds through data integration" — the routes product the original plan named. Check what the
  current public species coverage is before assuming the four-species beta.
- **Status, threats and conservation of Earth's migratory birds (2026)**, *Nature Reviews
  Biodiversity* — paywalled, unread, and the single most likely place to find a counterfactual
  attribution precedent.
- Dokter and colleagues report a **steep decline in migratory biomass passage** over a recent decade
  from a continent-wide radar network. Our record is timing rather than magnitude, but a
  biomass-magnitude claim from the same data would land in occupied territory.

## What this changes

| Idea | Before | After |
| --- | --- | --- |
| Counterfactual trajectory | "probably novel, cheap" | **Standard framing, apparently unapplied to migration, and improvable by running ATTRICI-style and DAMIP counterfactuals against each other.** Stronger than I thought, and the novelty claim needs the paywalled review read first. |
| Evidence-ladder frontend | "our idea" | **ROBITT-shaped, which makes it standards-based rather than invented, and a visual ROBITT looks unbuilt.** |
| Forecasting | "weakest strong-sounding option" | **Confirmed, with a specific reason: BirdCast is operational and FluxRGNN is the frontier, on our own radar network.** |
| Coverage index | "assembled dataset" | Adjacent literature is mature, but on a different axis; keep it and name the axis as temporal detectability. |
