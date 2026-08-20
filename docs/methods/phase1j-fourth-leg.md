# Phase 1j — is the odd leg odd because it is radar, or because it is a date?

**Status, 2026-08-20, written before any download.** Nothing from the UK Butterfly Monitoring
Scheme has been fetched, read or sampled. No insect timing series exists in this lake, no ERA5
sample exists at any UK coordinate, and no fourth thermal-tracking ratio has been computed in any
form. What has been read is the scheme's own catalogue metadata — licence, span, fields, site count
— quoted in §3, and nothing else.

## Why this note exists

`transfer-fails` is the project's most-qualified published finding, and its caveat says exactly
what is wrong with it:

> the aerial leg is the only one with a clear signal in it and the only one that failed, and it is
> also the only phenological leg, the only radar leg and the only one needing a seasonal temperature
> slope to reach common units

Three legs. Two agree — northern marine and southern terrestrial, both at a thermal tracking
indistinguishable from zero. The third, aerial radar over CONUS, differs from both. The
pre-registration listed realm, hemisphere, instrument and decade as inseparable, and the result fell
on an axis it had not listed at all: **response type**, dates against places. That omission is
already recorded as a correction in `phase1i-transfer.md` rather than edited away, and `TASKS.md`
#47 has been holding the remedy since: *a non-radar timing record — constant-effort ringing, or a
phenology network — separates "timing responds differently" from "the radar is different".*

This is that fourth leg. It changes exactly one axis and deliberately changes no other: it is
phenological like the aerial leg, and it is not radar. It is northern and terrestrial, which adds no
hemisphere contrast and no realm contrast, on purpose — a leg that moved three axes at once would
reproduce the defect this note exists to fix.

It also happens to be the breadth the project has owed itself since ADR 0010: the first insect
series in the lake, the first response outside North America and southern Africa, and the first
thing here that is neither a vertebrate nor a radar echo.

## 1. The dataset, and the reason it clears the door

`docs/DATASETS.md` asks for a role, fifteen years per unit, and effort fixed by design.

**Role: response.** Mean flight date per species per site per year is a timing series, the same kind
of quantity as radar passage date.

**Years per unit: 1976 to 2021 in the release read, forty-six.** The floor is fifteen.

**Effort fixed by design, and this is the strongest case in the lake.** A UKBMS transect is a
Pollard walk: a fixed route, walked weekly through the season, under stated temperature, wind and
sunshine criteria, recording within a fixed box around the recorder. That is a *protocol*, not a
convenience sample. It is the bar OBIS failed and FISHGLOB passed, and this passes it by design
rather than by luck — which matters here because the leg it is joining is a transect-free radar
record and the comparison must not be a comparison of effort models.

## 2. Estimand and unit, with the known problems first

**The unit is a site-species-generation.** The quantity is the **thermal tracking ratio** —
`phase1i`'s own currency, unchanged: the observed timing shift over the shift that following the
local thermal calendar would have required. One is perfect tracking, zero is no response, negative
is movement against the warming. Nothing about the common currency is redefined here, because a leg
computed in a different currency would not be a fourth leg.

Known problems, before any download:

- **"Mean flight date" names two different biologies.** For a resident species it is emergence
  timing, set by accumulated spring warmth. For a migrant it is arrival plus residence, set by
  conditions somewhere else entirely. They share a column name and nothing else. The primary leg
  pools both, because that is what makes it commensurable with an aerial leg that also pools
  whatever flew; the migrant-resident split is a **declared secondary** in §4 with its species list
  fixed below before any fit.
- **Eleven species are multi-voltine and the source splits their generations.** A species-level mean
  flight date across broods would be an average of two peaks and a trough, which is not a date any
  animal experienced. Generations are kept separate and treated as distinct units.
- **The decade does not match, and that is one of the four axes already confounded.** UKBMS starts
  in 1976 and the radar in 1995. Registered now, before looking: the primary leg is restricted to
  **1995–2021**, matching the radar's window and costing nineteen years of the record, and the full
  1976–2021 fit is reported beside it as a sensitivity. Choosing the window after seeing which one
  agrees with the aerial leg is exactly what this convention exists to prevent.
- **The driver does not exist in this lake yet.** `era5` samples sit at CONUS radar sites. The leg
  needs monthly 2 m temperature at UKBMS coordinates, which is the same driver and the same
  `GriddedSource` pathway, sampled at new sites. If that sampling fails, the leg does not exist and
  nothing below is computed.
- **Site coordinates arrive from a second dataset.** The phenology CSV carries a site identifier;
  positions are published separately. Without the join there is no temperature and no leg, so the
  join rate is a graded prediction rather than an assumption.
- **The seasonal slope flips sign against the aerial leg, and this is the point rather than a
  problem.** The aerial leg divides an autumn date shift by an autumn *cooling* rate: warming makes
  a given autumn temperature arrive later, so its thermal calendar moves later while the observed
  passage moved earlier. A spring emergence date divides by a spring *warming* rate, and warming
  makes a given spring temperature arrive earlier, so calendar and response move the same way. The
  ratio's sign therefore carries real information here, and §4 turns that into the sharpest
  prediction in this note.
- **A scheme is not a realm.** Two and a half thousand British sites sample one island's climate.
  Any agreement found here is agreement between a radar network and a national scheme, not between
  two independent worlds, and the leg is one point rather than a distribution over places.
- **Recorder turnover is not effort variation but is not nothing either.** Sites enter and leave and
  observers change. The design fixes the protocol, not the personnel, and a site whose recorder
  changed mid-series may carry a step this note does not look for.

## 3. What the catalogue says, quoted, and read on 2026-08-20

Licence, verbatim from the EIDC record: **"Open Government Licence"**, with the condition *"By
accessing or using this dataset, you agree to the terms of the relevant licence agreement(s). You
will ensure that this dataset is cited in any publication that describes research in which the data
have been used."* Downloadable without registration. CSV.

Fields, as published: first appearance, last appearance, date of peak abundance, **mean flight
date**, total days of flight period, and standard deviation around the mean flight date — per
species, per site, per year. Over 2,500 sites. Eleven multi-voltine species carry separate
generations.

Citation of record: Botham, M.; Middlebrook, I.; Harrower, C.; Roy, D.B. (2022). *United Kingdom
Butterfly Monitoring Scheme: phenology 2021.* NERC EDS Environmental Information Data Centre.
`10.5285/0c59eb20-26e3-4066-86f5-418afae18769`.

Two registry entries follow from this, both written before the fetch: `ukbms_phenology` as a
`survey_index` response in the terrestrial realm with `taxon_scope: exact`, and the site positions
it joins against. Sensitivity is `low` rather than `not_sensitive` on the same reasoning `sabap1`
records: the rows are site-level aggregates over a protocol with no individual and no nest in them,
but the gate should not minute a judgement that the taxa themselves are safe.

## 4. Predictions

**The ingest gate, graded first. Nothing below it is interpreted if it fails.**

1. **The licence and the fields are as quoted.** The download carries a mean flight date per
   species-site-year, and the OGL is stated in or with the archive.
2. **Coverage.** At least 800 sites and at least 25 species clear a floor of fifteen years within
   1995–2021, and at least 90% of phenology rows join a published coordinate.

**The leg, and prediction 4 is the one this note is for.**

3. **The fourth leg exists in the common currency**: a per-unit thermal tracking ratio with a
   median standard error no worse than the aerial leg's.
4. **The fourth leg does *not* behave like the aerial leg.** Its median tracking ratio is
   **positive and distinguishable from zero**, where the aerial leg's is the one that broke the
   transfer. Spring phenology following spring warmth is among the best-replicated results in
   ecology, so this is registered as the likely outcome and it is the outcome that *refutes*
   response type as the explanation — leaving the radar, or CONUS, or that record, as the odd one
   out. The alternative is live: if the fourth leg comes back indistinguishable from the marine and
   terrestrial legs *and* the aerial leg stays apart from all three, then dates-against-places was
   never the axis either, and the aerial leg is alone for a reason none of the four candidates
   names.
5. **The migrant-resident split, declared secondary.** Species list fixed here, before any fit:
   *Vanessa cardui*, *Vanessa atalanta*, *Colias croceus* as migrants; every other qualifying
   species as resident. Prediction: the migrant group's tracking ratio is *lower* and its
   between-site spread *wider* than the residents', because a migrant's date is set where it came
   from and not where it was counted. Registered weakly — *V. atalanta* has become partly resident
   in southern England over this very window, which blurs the group it is assigned to, and that is
   stated now rather than discovered later.

## 5. Stop conditions

- **Prediction 1 or 2 fails.** The source does not carry what the catalogue advertises, or the
  coordinate join does not hold. The ingest is reported as a coverage statement, the registry entry
  records what was actually found, and **no leg is computed**. A failed admission is a result about
  a dataset and is published as one.
- **The ERA5 sampling at UK coordinates fails or cannot be verified.** Same treatment. The leg needs
  a measured seasonal slope and there is no literature constant substituting for it — that rule is
  `phase1i` §5's and it is inherited whole.
- **Prediction 3 fails.** If the per-unit standard errors are materially worse than the aerial
  leg's, the fourth leg is too noisy to distinguish anything and is published as a null of the
  instrument rather than a result about transfer. A leg that cannot tell the hypotheses apart must
  not be reported as favouring either.
- **Both readings of prediction 4 survive.** If the fourth leg's interval overlaps both the aerial
  leg and the other two, it discriminates nothing, and that is reported as such rather than resolved
  by picking the nearer one.

## 6. What this cannot establish

- **Not whether a fitted model transfers.** This tests whether four measured responses agree, which
  is `phase1i`'s own weaker question and the only one four cases can answer.
- **Not causality anywhere.** Every leg divides an observed shift by a temperature. A system moved
  by land use, nitrogen, pesticide or a change in recording still reports as tracking or failing to
  track the heat, and `phase1i`'s caveat about wind, land use and fishing pressure applies here
  unchanged.
- **Not a hemisphere or realm result.** One axis moves. A fourth leg that agreed with the southern
  terrestrial leg would say nothing about hemispheres, because it is northern.
- **Not a claim about British butterflies.** The unit is a tracking ratio built to be commensurable
  with a radar record, and it is a worse description of British butterfly phenology than the
  literature this scheme already supports. Anyone wanting that should read the scheme's own reports.
- **Not enough to license a forecast.** Nothing here is projectable and nothing here is asked to be.
