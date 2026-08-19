# Covariate survey for the modeling arc, recorded 2026-08-18

Done before the pre-registrations of #44 (step-selection), #54 (the predictability atlas),
#55 (the coupling graph) and #57 (the annual prediction), because all four fit models against
environmental drivers and the candidate list of "interesting" data is effectively infinite.
`docs/data/DATASETS.md`'s four-role test applies to every row here: a driver that cannot be
projected cannot enter a forecast, and naming the role is what stops the list growing by
enthusiasm.

Every claim about the lake was measured today against `src/migratlas/catalog/registry.yaml` and
the driver modules; every claim about an external source was verified against its landing page
and licence text on this date, and where verification failed the failure is stated rather than
papered over.

**Continued 2026-08-19** in [`covariate-survey-2026-08-addendum.md`](covariate-survey-2026-08-addendum.md), which asks the explanatory question rather than the four
tasks' question, and which corrects two things below: `narr` is described here as a control and was
already fitted as a co-predictor in Phase 2a, and §3's unverified CDS variable strings turned out to
be machine-readable after all.

## 1. What the lake already holds

| Source | Variables | Span / cadence | Licence | Role |
| --- | --- | --- | --- | --- |
| `era5` | 2 m temperature, total precipitation — monthly means over the CONUS radar band | 1940–present, monthly | CC BY 4.0 (CDS token + `cc-by` acceptance) | projectable driver (via CMIP6 counterpart) |
| `era5_south` | 2 m temperature over the southern African atlas footprint | 1940–present, monthly | CC BY 4.0 | explanatory driver |
| `narr` | wind components at pressure level, for the airspeed control | 1979–present | public domain (NOAA) | control |
| `insitu` (rides `fishglob`) | sea-surface and sea-bottom temperature at every haul | per haul, 1970s–2020s | inherits FISHGLOB | explanatory driver — the water the fish were actually in, better than any gridded product on the shelf |
| `cmip6_damip` | hist-nat counterfactual | scenario runs | CMIP6 terms | control / projectable |
| `isimip3a` | ATTRICI counterfactual near-surface temperature | 1901–2019 | ISIMIP terms | control |
| `nsidc_sea_ice_index` | monthly median ice edge / extent | 1979–present, monthly | citation required, no other restriction | explanatory driver; a seasonal-timing series can be computed from the monthly index |
| `pku_gimms_ndvi` | NDVI, half-monthly at 1/12° | 1982–2022 | CC BY 4.0 | explanatory driver |

Two measured facts about these holdings that the modeling arc should not rediscover:

- **The PKU GIMMS raw archives hold the full yearly record, not the climatology.** The published
  layer collapses 41 years to 24 bins, but the four zips on disk (2.4 GB, checksummed) carry
  every half-month of every year. A yearly green-up-date series per cell or region is one new
  reduction over data already admitted and already downloaded — no new licence, no new fetch.
- **ERA5 in the lake is two variables over two windows**, not the reanalysis. Anything beyond
  monthly temperature and precipitation over the radar band and the atlas footprint is a new CDS
  request, cheap but not free (the token, the licence acceptance, and the one-hour queue are all
  already survived).

## 2. What each task needs, held against what exists

### #44 — step-selection on the cleared tracks

Per-step covariates along the elk, reindeer and fox tracks. From holdings: NDVI (1/12°
half-monthly spans every track year except the fox Argos era's coarse fixes, where 1/12° exceeds
the position error anyway — usable). Missing and surveyed in §3: terrain (static; one DEM tile
per study area), snow (the covariate the elk and reindeer literature says matters most in
winter), land cover (static context). ERA5 monthly is too coarse in time for step scale;
ERA5-Land or daily ERA5 over three small boxes is the candidate, surveyed below.

### #54 — the predictability atlas

Response–driver pairs per unit, era-split (fit early, grade late):

- **Radar stations**: passage timing/intensity vs monthly temperature and precipitation —
  entirely in the lake today. The atlas's aerial half can start without any new source.
- **Fish per sea**: range position vs in-situ haul temperature — entirely in the lake today,
  and the in-situ pairing is the strongest driver data this project owns. The marine half of
  #54 (and all of #56) needs no new source to start; SST products in §3 only add context.
- **Herds**: displacement vs NDVI / snow. NDVI is in hand (yearly series, §1); snow is the gap.

### #55 — the coupling graph

The graph's nodes are timing-anomaly series. Computable from holdings today: radar passage
timing per station-year (1995–2025); per-sea fish range position per survey-year; yearly
green-up date (from the PKU archives, §1); ice seasonal timing from the monthly index
(1979–present). Needing admission: a plankton series (§3). Needing honesty: **the herds cannot
contribute a timing node.** Phase 1d established that a collar record whose fix interval
changed 104-fold cannot measure *when* — that is why Phase 1h measured displacement between
fixed windows — and a coupling graph that quietly re-admitted herd timing through the back door
would be the overclaim this repository exists to refuse. The herds enter, if at all, as
displacement responses, not timing nodes.

Confounders: every candidate edge between two northern-hemisphere series is exposed to the
large-scale modes (NAO, ENSO, AO, PDO, AMO) driving both ends. The indices are surveyed in §3;
conditioning on them is not optional and the pre-registration must say so.

### #57 — the annual prediction

Needs whatever #54 finds skillful, plus a forecast of the driver at issue: seasonal forecast
products surveyed in §3. The prediction target that is computable today with no new source is
the radar passage anomaly; green-up-driven targets follow once the yearly NDVI series exists.

## 3. External candidates

*Each subsection names its licence exactly or says the verification failed. "Verified" means a
live HTTP 200 without authentication on this date, or the licence text read from the provider's
current page.*

### Terrain — Copernicus DEM GLO-30, and nothing else

AWS open bucket, plain HTTPS, no account: `copernicus-dem-30m.s3.amazonaws.com`, one COG per
1° tile. All three study-area tiles verified: N52 W117 (Alberta Rockies), N78 E015 (Svalbard),
N73 W080 (Bylot). Licence: the ESA/Airbus/DLR "Licence for Copernicus DEM instance
COP-DEM-GLO-30-F" — free for research, redistribution permitted, with a mandatory verbatim
attribution notice and liability disclaimers that must be passed to downstream users. The
alternative rules itself out: SRTM/NASADEM stops at 60°N, which excludes two of the three sites
before its Earthdata login is even considered.

### Snow — ERA5-Land, through the pipeline that already exists

0.1°, hourly, 1950–present, CC-BY, on the CDS token the lake already holds. Snow depth, snow
cover, water equivalent and density all exist; the trap to check at first fetch is that
ERA5-Land's `sde` is true depth in metres while `sd` is water equivalent — plain ERA5 has only
the latter. Chosen over MODIS for three reasons that survive review: it works through the polar
night (optical snow products are blind November–February at Svalbard and Bylot, exactly when
snow constrains movement), it provides depth — the locomotion-cost variable — and it needs no
new credential. Caveat for the SSF note: 9 km smooths topographic snow variation in the
Rockies, so terrain covariates ride alongside. If elk residuals ever demand 500 m snow, the
right product is daily gap-filled MOD10A1F, the only item in this survey that would force a new
credential (Earthdata login); deferred until demanded.

### Sea temperature — NOAA OISST and ERSST, public domain, no auth

OISST v2.1: daily, 0.25°, September 1981–present, netCDF over plain HTTPS on NCEI (verified),
public domain as a U.S. Government work, citation Huang et al. 2021. ERSST v5: monthly, 2°,
1854–present, same access shape (verified), citation Huang et al. 2017 — the pre-1981 extension
and the input for computing an AMO in-lake (below). For the fish work these are context beside
the in-situ haul temperatures, not a replacement for them.

### Seasonal forecasts — C3S SEAS5 monthly means, on the existing token

Dataset `seasonal-monthly-single-levels` on CDS: 1°, monthly means, 2 m temperature and total
precipitation, lead times one to six months (verified), hindcasts 1993–2016 for calibration,
real-time 2017–present. Licence CC-BY; using ECMWF SEAS5 alone avoids the extra non-European
acknowledgement clause. **The release clock sets #57's deadline: ECMWF publishes on the 6th of
each month at 12 UTC**, so the annual prediction must be pre-registered before the 6th of its
issue month. Public-domain fallback and multi-model check: NCEP CFSv2 monthly means, verified
no-auth on two endpoints, at the cost of GRIB2 (cfgrib + eccodes, both wheels).

### Climate indices — four current, one stale, all public domain

ONI, NAO, AO (CPC) and PDO (NCEI) verified live through mid-2026 as plain-text files, no auth.
**The AMO is the trap: NOAA PSL's canonical series ends at January 2023** — Kaplan SST is no
longer updated and no operational AMO exists. If the conditioning set needs AMO past 2022, it
must be computed in-lake from the ERSST v5 netCDFs — which is also what "every published number
is computed from the lake" would have demanded of a typed-in index anyway.

### Land cover — ESA WorldCover 2021, one epoch, static

10 m, CC BY 4.0, AWS open bucket verified without auth for both polar sites. The 2020 and 2021
epochs used different algorithms and are not comparable; use v200/2021 alone. For step-selection
a single static layer is the defensible choice — habitat change within a few collar-years is
negligible against 10 m classification error, and a habitat layer that changes under the model
confounds selection with map revision. The 300 m CCI/C3S annual series (1992–present) matters
only if multi-decadal habitat change becomes a hindcast driver, and its "ESA CCI licence" text
was not read this session — verify before any admission.

### Plankton — the CPR through its CC BY door, and a bloom clock from space

The Continuous Plankton Recorder is the record the coupling graph wants — monthly tows since
1946, the base of the North Atlantic food web — and it has two doors. The UK mirror (DASSH IPT,
phyto and zoo Darwin Core archives, verified no-login) is **CC BY-NC 4.0**, which collides with
redistributing derived tiles. The door that works: **the BCO-DMO product** (doi
10.26008/1912/bco-dmo.765141.6), the same survey's western North Atlantic — **CC BY 4.0**
(verified on the page), 1958–2022 and still updated, monthly, 413 taxa, one 72 MB CSV over
plain HTTPS with an ERDDAP beside it. It sits in the same water as FISHGLOB's northwest
Atlantic trawls and downwind of the radar band, which is exactly where the graph's marine edges
would be tested. The NE Atlantic / North Sea complement is **ICES DOME zooplankton** (CC BY 4.0
stated in its download conditions, 1958–2025), with the caveat that it is a query-shaped portal
of heterogeneous national programmes rather than one file.

The satellite proxy: **ESA OC-CCI v6.0** merged chlorophyll (Sep 1997–2024, 4 km, monthly,
no-login HTTPS via CEDA) — the only multi-decade chlorophyll record engineered for cross-sensor
consistency, which is precisely the property a timing analysis needs; its licence *name* was
verified but the full text returned 404, so the licence-clean route for anything redistributed
is the **SOCCO global phytoplankton phenology indices** (Zenodo, doi 10.5281/zenodo.8402932,
**CC BY 4.0**, verified plain-HTTPS, 17.4 GB) — precomputed bloom-timing metrics from OC-CCI,
i.e. the phenology variable itself, under a named licence, with an ESSD data paper.

Rejected with reasons: KRILLBASE (Open Government Licence, fine — but austral-summer-only
sampling defeats within-year timing, and the wrong hemisphere for every series we hold);
COPEPOD (no cadence as a whole; keep as a discovery index); CalCOFI (quarterly since 1985 is
marginal for timing, and its licence statements conflict — a 404'd data policy page is not a
licence); NASA OceanColor per-sensor records (Earthdata login, and stitching sensors yourself
injects the inter-sensor offsets OC-CCI exists to remove).

CPR route-and-method caveats travel with any admission: shipping routes moved over decades,
counting is semi-quantitative on silk, and methods standardised only from 1958 — the analysis
start the famous CPR literature itself uses.

### Not verified this session

The exact CDS API variable strings for ERA5-Land snow (the page renders them client-side); the
ESA CCI land-cover licence text; the PDO file's start year (currency through July 2026 was
checked, the 1854 start is documented not eyeballed).

## 4. The shortest viable set per task

Using only what §1 holds and §3 verified:

- **#44 step-selection**: GLO-30 terrain (slope, aspect, ruggedness), ERA5-Land snow depth,
  WorldCover 2021 static, NDVI from the lake. Zero new credentials.
- **#54 hindcasts**: the lake's own pairings (radar × ERA5, fish × in-situ haul temperature,
  herds × NDVI + ERA5-Land snow), OISST for marine context, and ONI/NAO/AO/PDO plus an in-lake
  AMO as the confounder set. Zero new credentials.
- **#57 annual prediction**: SEAS5 monthly means on the existing CDS token, calibrated on the
  1993–2016 hindcasts, pre-registered before the 6th of the issue month; verified against the
  observation streams above. Zero new credentials.

The only candidate anywhere in the arc that demands a new credential is 500 m MODIS snow, and
it stays out until a fitted model's residuals ask for it by name.

## 5. What this survey cannot establish

- Whether any driver–response pair actually carries skill: that is #54's question, and this
  document deliberately stops at availability, licence and cadence.
- Whether the coupling graph's series are long enough for conditional-independence discovery:
  the literature note (`literature-2026-08-coupling.md`) carries that question.
- Whether a plankton source survives `DATASETS.md`'s admission test: this survey nominates,
  admission decides.
