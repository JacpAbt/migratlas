# Covariate survey addendum — the explanatory drivers, recorded 2026-08-19

Written the day after [`covariate-survey-2026-08.md`](covariate-survey-2026-08.md), and for a
different question. The parent survey asked what the four modeling tasks need. This one asks the
owner's founding question — *why did movement change* — and it exists because that question is
currently answered by one driver: nine findings, one of them an attribution, and temperature on
both sides of it.

Every external claim below was verified by live HTTP on 2026-08-19 without authentication, or the
failure is stated rather than papered over. Every claim about this repository was measured against
the code today, not remembered. `DATASETS.md`'s four-role test applies to every row, and §2
proposes one change to how its third role is *read* — not to the rule itself.

## 1. Two corrections, before anything is proposed

**Wind is not unused, and the term this project needs already exists.** The plan this addendum
serves said wind "has entered no fit". Measured today, that is wrong in a way worth recording:

- `reports/phase1c.py` uses it as the airspeed control — `airspeed = |radar velocity − NARR
  925 hPa night wind|` per station-night — where the wind is *subtracted* to isolate what the
  animals were doing.
- `reports/phase2a_timing.py` already computes **`wind_support()`**: a traffic-weighted mean
  heading per station as a unit vector, the wind projected onto it
  (`u·heading_east + v·heading_north`), averaged per station-year. It enters `sensitivities()`
  as a co-predictor beside pre-season temperature, and the fit records `per_wind` per station
  alongside `per_degree`, plus the temperature–support correlation as `driver_correlation`. The
  pre-registration in `phase2a-timing.md` fixed it before the temperature was fetched.

So the tailwind term is registered, fitted and published. What is true is narrower and still the
gap: **`reports/phase3a.py`'s `_covariates()` builds seven columns — season and pre-season 2 m
temperature, season precipitation, and ONI/NAO/AO/PDO — and no wind.** No skill number this
project has ever published has seen wind. The correct description of the omission is *the
hindcast harness*, not *the project*, and the fix is a join plus a `season` argument on an
existing function, not a new metric.

**Growing-degree days cannot come from the lake's ERA5.** `era5` in the lake is *monthly means*
(`air_temperature_2m`, `total_precipitation`), and a degree-day sum computed from monthly means is
not a degree-day sum. This moves the candidate out of the no-fetch tier — and the route turned out
cheaper than an hourly aggregation would have been, see §4.

## 2. The role this addendum turns on

`DATASETS.md` says: *"A driver you cannot project cannot appear in a forecasting model."* That is
correct and it should not change. What has happened is that it has been read as a **general** bar,
and the candidate list has been pruned against a forecasting standard even where the question was
not a forecast. Four of the strongest candidates for *why* — human presence in every form, night
lights, wind, oxygen — are unprojectable by nature and were each set aside partly on that ground.

An explanatory driver cannot forecast and can still answer the owner's question. "The change is
larger where the lights arrived" is not a prediction and needs no scenario form.

**The consequence, and it belongs in every downstream registration:** skill and effect must be
reported **twice** — once from projectable drivers alone, once from every driver admitted. The
first number is what licenses a forecast. The second is what answers *why*. Reporting one number
is what lets an explanatory gain quietly inflate a forecast claim, which is the failure mode the
Phase 3d refusal exists to prevent. `phase3a` already computes a nested decomposition
(`full` / `weather_only` / `indices_only`), so this is an extension of a shape that exists.

## 3. Tier 1 — derived from holdings, no fetch, no licence

| Candidate | Where from | Role | Note |
| --- | --- | --- | --- |
| Tailwind support, per station-season | `wind_support()` over `narr` (`wind_u_925hPa`, `wind_v_925hPa`, night means) | explanatory | Exists and is fitted; hard-scoped to autumn today. Needs a `season` argument whose default reproduces the published `per_wind`, pinned by a test |
| Crosswind magnitude, and favourable-night count | the same two columns, one more projection | explanatory | The support term averages a season; a *count of nights above a threshold* is a different and arguably better-matched statistic for a date response |
| Photoperiod at station × day | arithmetic — solar declination and the sunrise equation | **moderator, never a predictor** | Identical every year, so it cannot carry interannual variance by construction. Its use is as an interaction: the standard account of why autumn timing is plastic and spring is not, which is this project's own unexplained asymmetry (`autumn-advance` against a null spring) |
| Instantaneous rate of green-up (IRG) | PKU GIMMS archives already on disk, 2.4 GB in four checksummed zips | explanatory | The green-wave covariate the ungulate literature uses, and the right form of vegetation for #44. The parent survey established that the archives hold every half-month of every year, not only the published climatology |
| Marine-heatwave days; climate velocity | `oisst`, in the lake as of Phase 3e | explanatory | **Unblocked while this note was being written.** Phase 3e ran 2026-08-19 and its gating calibration passed: OISST against in-situ warming at **+0.216** over the ten dual-record units. Two caveats travel with anything computed from it — +0.216 is *modest*, and `phase3b-marine-scale.md` deferred climate velocity on the ground that in-situ beats gridded on the shelf. What changed is coverage: in-situ reaches ten units, OISST reaches eighteen |

## 4. Tier 2 — external, verified 2026-08-19

| Candidate | Route | Licence | Span | Volume | Role |
| --- | --- | --- | --- | --- | --- |
| Harmonised DMSP–VIIRS night lights | Figshare `9828827` v10 (2025-08-10), 34 annual GeoTIFFs; `ndownloader.figshare.com` returned **HTTP 206** with byte ranges and `image/tiff`, no auth | **CC BY 4.0** | **1992–2024** | 1.09 GB total | explanatory |
| Annual terrestrial Human Footprint | Figshare `16571064` v8 (2025-11-05), 26 per-year zips | **CC BY 4.0** | 2000–2018 | 11.94 GB (~457 MB/yr) | explanatory |
| Human Footprint, two epochs | Dryad `10.5061/dryad.052q5` v2 (2016-11-17) | **CC0-1.0** | 1993 and 2009 | 1.72 GB | explanatory |
| ERA5 daily statistics — degree-days, frost days, heat days | CDS `derived-era5-single-levels-daily-statistics`, HTTP 200; 262 variables including `2m_temperature`; `daily_statistic` is one of `daily_sum`, `daily_mean`, `daily_maximum`, `daily_minimum` | CC-BY-4.0 | 1940–present | one request per window | explanatory; projectable in principle via a CMIP6 daily counterpart |
| ERA5 mean sea-level pressure | CDS single levels: `mean_sea_level_pressure` and `surface_pressure` both present in the 260-string enum | CC-BY-4.0 | 1940–present | small | explanatory |
| Humidity | **Not on single levels.** That enum carries `2m_dewpoint_temperature` and no relative humidity; `relative_humidity` and `specific_humidity` are in the 16-string pressure-level enum | CC-BY-4.0 | 1940–present | small | explanatory |
| SOCCO phytoplankton phenology indices | Zenodo `8402932` (2023-10-03), one file | **CC BY 4.0** | — | 17.40 GB (17,395,564,460 bytes) | explanatory |
| RAM Legacy stock assessments | Zenodo `14043031`, v4.66 (2024-11-06), `RAMLDB v4.66.zip` | **CC BY 4.0** | — | 111.9 MB | **control** |

Three of those carry a decision rather than only a row.

**Night lights overturn a standing refusal, and the reason the refusal no longer holds is
specific.** `TASKS.md` refuses night lights because they need "an EOG account" and because "the
two instruments are not comparable without a harmonised product". Both halves have expired: the
harmonised product is published, open, and needs no account — and it now runs **1992–2024**, which
brackets the radar record's 1995–2025 almost exactly. This is also the driver with the most
specific mechanism for the project's *own* response variable: the radar measures **nocturnal**
passage, and artificial light at night is the anthropogenic change that acts on nocturnal
migration directly rather than through climate. It should be re-read as a candidate, not inherited
as refused.

**The two Human Footprint products answer different questions and neither answers both.** The
annual series is annual and starts in 2000 — too late for SABAP1 (1987–1991) and for the radar's
first five years. The two-epoch product straddles the atlas comparison (1993 and 2009, against
atlas eras of 1987–1991 and 2007–2026) and cannot describe annual change at all. Admitting one and
describing it as "the human footprint" would be the mistake; the window has to travel with the
claim.

**Degree-days got cheaper than expected.** `derived-era5-single-levels-daily-statistics` serves
`daily_maximum` and `daily_minimum` directly, so a conventional degree-day sum needs no hourly
download and no aggregation of our own. The same request yields frost-day and heat-day counts —
extreme-event indices, which the phenology literature generally finds move further than means, and
which this project has never fitted. One request, an existing token, no new credential.

## 5. Refused or deferred, each with the measurement behind it

**Dissolved oxygen — deferred, and the reason is a measurement.** Deoxygenation is the strongest
non-thermal driver of fish redistribution in the literature, and the free route cannot carry it.
WOA23 oxygen is reachable two ways without auth (plain HTTPS at NCEI returned HTTP 206 with byte
ranges; the THREDDS OPeNDAP `.das` returned 9,766 bytes of metadata) and it is a **climatology
only**: `cell_methods` reads `time: mean within years time: mean over years`, and every decadal
path probed — `decav`, `5564`, `6574`, `7584`, `8594`, `95A4`, `A5B7` — returned **HTTP 404**. A
climatology cannot carry a trend, so it fails `DATASETS.md`'s fifteen-year bar as a driver of
change and enters, if at all, as static context. A time-varying oxygen field means the CMEMS
biogeochemical reanalysis, which needs a Copernicus Marine account — so it joins 500 m MODIS snow
as an item that stays out until a fitted model's residuals ask for it by name.

**Sea Around Us reconstructed catch — refused on licence.** CC BY-**NC**, which collides with
redistributing anything derived, exactly as the CPR's UK mirror did. RAM Legacy is the open door
to the same question and is in §4.

**ESA CCI annual land cover — still unread.** The parent survey listed its licence text as
unverified and this addendum did not resolve it. Recorded as still open rather than assumed.

**Conspecific abundance as a driver — named, and not proposed.** BBS, the Swedish schemes and the
atlases could all supply it. It is a *response* elsewhere in this ledger, and a design that used
one source as both response and driver without saying how it avoided double-counting would be
worse than not asking. It needs its own design note before it is a candidate.

**Barriers — unchanged.** Fences have no global product. Roads were rejected for change detection
on the correct ground that one snapshot cannot describe change.

## 6. What the parent survey could not verify, now verified

The parent survey's first unresolved item was "the exact CDS API variable strings for ERA5-Land
snow (the page renders them client-side)". They are machine-readable after all, at
`https://cds.climate.copernicus.eu/api/retrieve/v1/processes/<collection-id>`, which returns the
process schema with the variable enum inside it. Verified today:

- **ERA5-Land monthly means** carries **60** variable strings, including `snow_depth` *and*
  `snow_depth_water_equivalent` as distinct values — so the trap the parent survey flagged (`sde`
  is depth, `sd` is water equivalent) is real and is now resolvable by name rather than by
  inspecting a downloaded file. `snow_cover`, `snowmelt` and `snow_density` are there too, which
  is what a melt-out **date** would be computed from.
- **ERA5 single levels monthly means**: 260 strings, licence `CC-BY-4.0`.
- **ERA5 pressure levels monthly means**: 16 strings, licence `CC-BY-4.0`.
- `derived-era5-land-daily-statistics` also returns HTTP 200, which is the daily route to a
  melt-out date at the herd ranges.

Any future survey should use this endpoint before reporting a CDS variable as unverifiable.

## 7. The shortest viable set per question

- **Why did autumn passage advance, beyond the thermal half?** Tier 1 wind (support, and a
  favourable-night count), photoperiod as the latitude interaction, degree-days and frost/heat-day
  counts from one CDS daily request, and night lights as the one anthropogenic driver that acts on
  nocturnal migration directly. Zero new credentials. This is the set with a real chance of
  speaking to the unexplained half of −0.56 d/decade.
- **Why did the southern African atlas not change on net?** The two-epoch Human Footprint (its
  windows straddle the atlas eras), night lights over the same footprint, and ERA5 humidity from
  the pressure-level route. `phase1g`'s water null is the template, and its warning applies: an
  attenuated instrument yields "not detectable", not "absent".
- **Why do the seas disagree in sign?** This question was rhetorical when the note was started
  and is now the sharpest one in the project. Phase 3e ran the same day: Cochran's Q of **235.7
  against a bar of 27.6** — the seas differ enormously — and the cross-unit slope of latitude
  trend on warming is **+0.039 ± 0.179**, graded false against its own registered prediction. Its
  own conclusion is that whatever sorts the movers from the stayers "is not the thermometer
  alone". Every non-thermal marine candidate in this note is therefore promoted from interesting
  to *the remaining hypothesis space*: RAM Legacy fishing pressure (a shift credited to warming
  when it is fishing-down-the-stock is a live confound and no fishing covariate exists anywhere in
  this lake), marine-heatwave days (extremes rather than means), climate velocity (isotherm speed
  rather than warming in place), and SOCCO bloom phenology (food timing rather than heat). Oxygen
  would belong here too and cannot, per §5 — which is now a more expensive absence than it looked
  an hour ago.
- **Which of these may enter a forecast?** Degree-days alone, via a CMIP6 daily counterpart. Every
  other row above is explanatory, which §2 argues is not a demotion.

## 8. What this survey cannot establish

- Whether any of these drivers carries an effect. This document stops at availability, licence,
  cadence, window and role, exactly as the parent did. The fits are Phase 3f's question, and its
  registration must be written before any of them is joined to a response.
- Whether night lights survive admission. `DATASETS.md`'s test, the registry's sensitivity and
  caveat fields, and `catalog.admit()` decide that; this survey nominates.
- Whether the harmonised light product's DMSP-to-VIIRS splice is stable enough to carry a trend at
  station scale. The publication argues it globally; this project has been burned by an instrument
  change inside a record twice — the 2012 dual-polarisation step and the 46.8-day collar effect —
  and should treat the splice year as a break to test for, not a detail to trust.
- Whether the two Human Footprint products agree where their windows overlap. If either is
  admitted, that comparison is the first thing to measure and it costs nothing.
