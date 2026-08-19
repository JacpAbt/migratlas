# Phase 3c — what moves together, and through what?

**Status:** pre-registered 2026-08-19. Written before the plankton fetch (the CPR admission this
note licenses has not run), before any series named below has been paired with any other, and
before any lag has been examined. The literature pass (`literature-2026-08-coupling.md`) and
Phase 3a's prediction 5 precede and constrain everything here.

## On novelty: none is claimed

The literature pass found no causal-discovery work on migration or phenology timing, no
cross-realm directed graph of such series, and no public interactive presentation of one — *as
far as our own search reached*. The one review positioned to adjudicate that (Suzuki et al.
2026, *Biological Reviews*, doi 10.1002/brv.70180) is paywalled and remains unread; the owner
has no access. The stop condition is therefore resolved the simple way: **this work claims no
novelty, on the site or anywhere else.** It is done because the owner wants the information —
what moves together, and through what — not the adjective. If the review is ever read and shows
prior art, nothing published here needs retraction, because nothing published here says "first".

## Why this note exists

The mission sentence of 2026-08-18: not only where animals move, but what is changing it, and
what moves together. The literature pass killed the naive version — a discovered multivariate
graph over 20–45 annual points under shared climate modes fabricates edges — and Phase 3a's
prediction 5 then *measured* the central risk on this project's own data: where the modes alone
predict, local weather's marginal contribution halves. So this design does not discover a
graph. It registers **four specific edges**, two of which exist to calibrate the instrument,
and publishes each one hit or miss, with the modes conditioned on throughout.

## 1. What was looked at before this was written

Nothing new. Series inventories come from the covariate survey and Phase 3a's note (radar
1995–2025; green-up 1982–2022 in the lake; NSIDC ice 1979–present; modes 1950–present). The CPR
product named below is known only by its catalogue metadata (BCO-DMO doi
10.26008/1912/bco-dmo.765141.6, CC BY 4.0, monthly, 1958–2022, western North Atlantic); no row
of it has been seen.

## 2. The nodes, and the fetch this note licenses

- **Spring passage timing**, per year: the radar band's median spring `q50_doy` across
  stations — the same metric every phase uses.
- **Green-up day**, per year: the mean of the lake's green-up series over the radar band's
  vegetated cells (37–50°N, the claim band).
- **Plankton timing**, per year: the spring bloom's midpoint-of-amplitude day per CPR region,
  computed by the same `greenup_day` logic applied to monthly plankton abundance — one metric
  definition, two kingdoms. **This licenses the CPR fetch**: the BCO-DMO product enters through
  `DATASETS.md` as the 29th source before any row is read; if its licence or format fails
  admission, the plankton edges below publish as coverage rows.
- **Fish centroid anomaly**, per survey-year: Phase 3b's units, where their segments overlap
  the CPR window and region.
- **The modes** (ONI, NAO, AO, PDO): conditioning variables in every edge, never nodes.

Herds contribute nothing here — Phase 1d bars their timing, and Phase 3a showed their usable
years cannot clear any floor this design would set.

## 3. The four registered edges

Each edge is a regression of the response anomaly on the driver anomaly with the four modes'
annual means as covariates, both series linearly detrended first (two series sharing a warming
trend would fabricate an edge — the literature pass's bluntest warning). Inference: the driver
is circularly shifted 1,000 times (preserving its autocorrelation, breaking the pairing); the
edge is reported detected only past the 95th percentile of that null. Every coefficient is
published with a bootstrap interval, detected or not.

- **C1 (calibration): winter NAO → green-up day.** The literature guarantees this
  teleconnection. If this machinery cannot see it, the machinery is impeached and no other
  edge is interpreted.
- **C2 (calibration): spring sea-surface temperature (in-situ, CPR-region surveys) → plankton
  bloom day.** The Edwards & Richardson relationship, as the marine calibration.
- **H1 (hypothesis): green-up day → spring passage timing**, lag 0, annual, n ≈ 31. The
  literature's decoupling result (PNAS 2024) says the association is weakening; Phase 3a's
  prediction 5 says the modes may own much of it. Registered expectation: the *conditioned*
  coefficient is positive but smaller than the unconditioned one.
- **H2 (hypothesis): plankton bloom day → fish centroid anomaly**, lag 0 and 1 year, per
  overlapping survey. Registered expectation, from the literature pass's own power analysis:
  **not distinguishable from the null at these lengths** — registered as a null prediction, so
  that a detection would be the surprise it deserves to be, and a non-detection is the honest
  sample-size statement it is.

## 4. Predictions

1. Both calibration edges detect. (Failing either stops the phase; see §5.)
2. H1's conditioned coefficient is positive and smaller than its unconditioned one — the modes
   own part of the green-up/passage association, as prediction 5 of Phase 3a implied.
3. H2 is not distinguishable from its null. A detection grades this false and is published as
   such — the good kind of wrong.
4. Every edge's bootstrap interval is published on the site beside its caveat, including the
   undetected ones, in the same ledger discipline every finding already obeys.

## 5. Stop conditions

- Either calibration edge failing → the phase publishes "the instrument cannot see a known
  signal at these lengths" and no hypothesis edge is interpreted. That page is itself worth
  publishing.
- CPR admission failing on licence or format → C2 and H2 become coverage rows; C1 and H1
  proceed.
- No edge is added, no lag widened, no region redrawn after any result is seen. A wrong
  registration is corrected in this file, not amended silently.

## 6. What this cannot establish

Causality in any strict sense — a registered edge with the modes conditioned out is still a
partial correlation with a story, and the note says "association" wherever the site might be
tempted to say more. Anything discovered — the four edges were chosen by mechanism, and the
space of unchosen edges stays unexplored by design. Anything about realms whose series could
not enter: the herds, the atlases, the Southern Hemisphere — the same emptiness `coverage-bias`
already publishes, now with a coupling shape.

---

## Results — run 2026-08-19

**A calibration edge failed, and the stop condition speaks for the whole phase.**

- **C1, winter NAO → green-up day: not detected** (coefficient −0.05, interval [−3.3, +3.9]
  against a rotation bar of 3.0, 41 years). The teleconnection the literature guarantees is
  invisible to this machinery over this band at this length.
- **C2, spring SST → plankton bloom day: detected** (+9.7 days per °C, interval [+2.9, +17.4]
  against a bar of 8.8, 38 years). The instrument is not blind — it sees a known marine signal
  where the signal is strong.
- **Prediction 1 — GRADED FALSE** (it required both), and §5 does what it was written to do:
  **no hypothesis edge is interpreted.** H1 and all ten H2 lag-variants were printed for the
  record and every one is null; they are observations about nothing until a calibration
  passes on their side of the design.
- **Prediction 2 — GRADED FALSE** mechanically (the conditioned H1 coefficient is not smaller
  than the unconditioned), and uninterpreted for the same reason as everything else.
- **Prediction 3 — GRADED TRUE.** The plankton-to-fish edge was registered as an expected
  null and the null held, ten times over.
- **Prediction 4 — deferred to publication**: the intervals publish beside their caveats when
  the coupling page ships with #52.

**What the split calibration actually says.** The failure is specific: the NAO's strongest
footprint is the North Atlantic's rim, and the response tested here is a continental-interior
band mean — a pairing this registration chose and must own. Any future coupling registration
starts from the C1 failure as a measured fact about band-mean green-up, not from a hope that a
different test would have passed. The page this phase publishes is the one §5 promised: at
these lengths, over these regions, the instrument saw one known signal out of two, and
therefore claims nothing it cannot see.
