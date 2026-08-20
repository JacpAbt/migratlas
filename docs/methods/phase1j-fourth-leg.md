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
- **Thirteen species have their generations split by the source** (eleven multivoltine plus two
  overwintering univoltines; corrected from eleven in amendment D). A species-level mean
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

## 3a. Amendments, written while implementing and before any fetch

Three things found by reading the catalogue further, each of which would have been a silent
assumption otherwise. Recorded here rather than folded into the sections above, so what was known
when §1 to §3 were written stays legible.

**A. The weekly transect counts are not openly published, so the date cannot be derived here.** The
open products are the site indices, the collated indices and the phenology summary; the collection
page directs anyone wanting more to request it from the scheme. The better design was therefore
unavailable: the radar leg derives its date from nightly `flux` rows through
`metrics/phenology.py`, and had the visit-level counts been open, this leg could have used *the same
metric on the same statistic*. It cannot. It must take the publisher's **mean** flight date against
the radar's **median** passage date.

That mismatch is bounded rather than waved away. The leg is a ratio of *trends*, so any constant
offset between a mean and a median cancels exactly; only a **trend in the skew** of the flight curve
could bias it. That is partly checkable, because the source publishes the flight-period duration and
the standard deviation around the mean flight date, so a trend in either is a trend in shape. Both
are reported beside the leg, and a significant trend in either is grounds to withdraw the comparison
rather than to caveat it. Registered as prediction 6.

**B. The publisher withholds sensitive site locations itself, and that is respected rather than
worked around.** The site-location dataset states that the locations of some sites are sensitive and
are excluded, with a request route for the rest. This project does not take that route here: #50 is
the only legitimate one and it is not being opened for this leg. Two consequences. Prediction 2's
join rate becomes a real test rather than a formality. And the exclusion propagates automatically,
because `SURVEY_INDEX` requires a non-null longitude and latitude — a site whose position the
publisher withheld **cannot be written to this lake at all**, without any code here deciding it. The
schema enforces another organisation's sensitivity judgement for free, which is worth writing down
because it is the first time that has happened in this project.

**C. The encoding, decided before the fetch because the obvious one is a trap.** A phenology summary
fits none of the seven evidence shapes cleanly, which `evidence/types.py` says is a design
conversation. The tempting move — `count` = mean flight date as a day of year — puts a *coordinate
on the time axis* into the table's `value_column`, where `sabap1` puts a reporting rate and
`fishglob` a standardised index. Every one of those is an intensity; a date is not, and anything
that aggregates `count` would then be averaging calendars. So instead:

- `period_start` = first appearance, `period_end` = last appearance. A true period, in the columns
  that hold dates.
- `count` = **days from first appearance to the mean flight date**. A genuine count of days, and the
  mean flight date is recovered exactly as `period_start + count`, with no approximation.

Nothing is stored under a name that misdescribes it, and nothing published is lost. If a later phase
needs dates as first-class objects across realms, the design conversation is an eighth evidence type
and this encoding is not an argument against it.

**D. What the supporting documentation says, read after the fetch and before any row was written.**
The archive carries a `.docx` that settles four things the catalogue page did not, and the first
would have silently wrecked the leg.

- **The day numbers are counted from 1 April, not from 1 January.** Verbatim: *"FIRSTDAY: the day
  number after 1st April on which a species was first recorded ... (e.g. 20 = 20th April)"*, and the
  same for `LASTDAY`, `PEAKDAY` and `MEAN_FLIGHT_DATE`. Read as a day of year, every date would have
  landed about ninety days early and looked perfectly plausible — a Peacock flying on 20 January
  rather than 20 April. The conversion is explicit in the adapter and pinned by a test.
- **`MEAN_FLIGHT_DATE` is the count-weighted mean date**, not an unweighted mean of survey dates.
  That is a closer analogue to the radar's traffic-weighted `q50_doy` than amendment A assumed:
  both are centroids of an intensity-weighted time distribution, differing in being a mean against a
  median rather than in what they are a summary of. Amendment A's caution stands and its bound is
  the same, but the two quantities are more alike than it feared.
- **Phenology comes only from the weekly standard transects.** The scheme's own words: the reduced
  effort and Wider Countryside squares are visited two or three times a year, so *"phenology data
  can only be calculated from standard butterfly transects where weekly counts are made"*. The
  effort behind this response is therefore the 26-visit Pollard walk and nothing else, which is
  stronger than §1 claimed and removes the mixed-protocol worry the site table raises.
- **Thirteen species carry split flight periods, not eleven, and §2 is corrected.** Eleven are
  multivoltine; two more are univoltine adults that overwinter — Brimstone and Peacock — whose two
  periods are the same generation before and after winter rather than two generations. `BROOD = 0`
  is the pooled row for every species and is exactly the average-of-two-peaks-and-a-trough §2
  refused: it is present in the file for all thirteen and must be dropped for them and kept for
  everyone else. The documentation also warns that `FIRSTDAY` and `LASTDAY` are unreliable where a
  flight period runs past the 1 April to 30 September window, and recommends the mean flight date
  and its standard deviation as *"less sensitive to the UKBMS methodology"* — which is what this leg
  uses, arrived at independently in amendment C and confirmed here.

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

6. **The flight curve's shape did not trend**, so the mean-against-median mismatch in amendment A
   stays a cancelling offset. Neither the flight-period duration nor the standard deviation around
   the mean flight date carries a trend distinguishable from zero over 1995-2021, pooled across
   units. If either does, the comparison is withdrawn rather than caveated.

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

## Results — the ingest gate, run 2026-08-20

Landed: **627,752 flight periods, 3,144 sites, 59 taxa, 1973–2021.** From 830,132 published rows,
189,739 pooled-brood rows were dropped as §2 required, and 12,641 more for sites whose position the
scheme withholds.

### Grading

**Prediction 1 — TRUE.** The archive carries `MEAN_FLIGHT_DATE` per species-site-year exactly as the
catalogue advertised, and the Open Government Licence is stated in the supporting document inside
the archive as well as on the record.

**Prediction 2 — FALSE, on one of its three clauses.**

| clause | floor | actual | |
| --- | --- | --- | --- |
| sites clearing fifteen years within 1995–2021 | 800 | **550** | fails |
| taxa clearing fifteen years within 1995–2021 | 25 | 56 | holds |
| phenology rows joining a published coordinate | 90% | **98.0%** | holds |

**§5's stop condition therefore fires: the ingest is reported as a coverage statement and no leg
is computed.** That is what the registration says happens, and it happens.

### The correction that goes with it

The prediction was specified on the wrong quantity, and this is recorded rather than edited away.

§2 fixes the unit as a **site-species-generation**. Prediction 2 then set its floor on *sites*,
which is not the unit and is not what the leg needs — a site carries many species and some species carry
two generations. Measured on the unit the note actually declared: **10,941 units clear fifteen
years inside the registered window**, out of 88,230. The aerial leg this is being compared against has 143.

So the honest position is uncomfortable in a specific way: the data is ample, and the prediction that
failed was a badly chosen proxy for whether it is ample. Both halves of that are true and neither
cancels the other. Proceeding anyway would make the stop condition decorative — the whole point of
writing one down is that it binds when it is inconvenient — so the leg waits for a successor
registration that sets the floor on the unit, and that registration inherits this measurement rather
than pretending to be blind to it.

### Four things the fetch found that the catalogue did not say

- **The span starts in 1973, not 1976.** Both the catalogue page and the supporting document say the
  scheme runs from 1976; the file carries 91 rows across three earlier years. Trivial in volume and
  worth writing down, because a note claiming 1976 beside data starting in 1973 is the kind of small
  discrepancy that makes a reader doubt the rest.
- **Both CSVs are Windows-1252, not UTF-8.** One byte proves it: a curly apostrophe in "RSPB
  Chafey's Weymouth", 81.7 MB into the phenology file. Polars reports `invalid utf-8 sequence` with
  no indication of where or why, and a reader that had guessed latin-1 would have turned that
  character into a different one and carried on.
- **One name in fifty-nine will not resolve bare.** `Limenitis camilla`, the White Admiral, matches
  only its *genus* in the GBIF Backbone — matchType `HIGHERRANK`, which the matcher refuses rather
  than accepting a genus for a species. Appending the authority resolves it at confidence 100 to key
  7712938, the same key the Backbone's own accepted name `Ladoga camilla` gives. Recorded in
  `ingest/ukbms.SYNONYMS` with the check that was run, as `sabap1` does for exactly this case.
- **The publisher's withheld sites propagate without any code deciding it.** 12,641 rows name a site
  whose position the scheme does not publish, and because `SURVEY_INDEX` requires a non-null
  longitude and latitude they cannot be written at all. Another organisation's sensitivity judgement
  enforced by this project's schema, which is the first time that has happened here.

### What the successor needs

1. **A floor on the unit**, and 10,941 is the number to set it against.
2. **The ERA5 sample at UK coordinates**, which does not exist yet and which §5 already makes a stop
   condition of its own — the leg needs a measured seasonal slope and no literature constant
   substitutes for it.
3. **The 1995–2021 window and the migrant species list stay as registered.** Neither was chosen
   after seeing anything, and re-opening them now would cost the thing this convention buys.
