# A second counterfactual, and a disagreement worth reporting

Pre-registration, 2026-07-31. Written **after** a one-station scoping probe and before any run at
scale, which is a departure from how Phase 1 and Phase 2a were pre-registered and is declared here
rather than hidden: the probe changed what the experiment should predict, and pretending otherwise
would make a post-hoc prediction look prior.

## Why a second counterfactual at all

`phase2a-attribution.md` established `f = 0.98`: of the modelled pre-season warming the animals
tracked, essentially all is attributable to human forcing, across 15 CMIP6 models with both a
`historical` and a `hist-nat` run.

The ribbon draws a third line, "with no warming at all", as a reference. But that line comes from the
same DAMIP arithmetic as the second, so it cannot disagree with it in any informative way — it is
`observed − S×W` where the other is `observed − f·S×W`, and `f` is 0.98. Two lines from one
ensemble are one piece of evidence drawn twice.

**ATTRICI asks a different question of different data.** DAMIP asks *what if there had been no human
forcing*, and answers it by running models without it. ATTRICI asks *what if there had been no
warming*, and answers it by removing from the **observations** the component of each daily series
that correlates with global mean temperature — quantile-preserving, so internal variability survives,
and carrying no model bias because no model produced it.

Reporting both, and any disagreement between them, is stronger than either.

## Access, verified rather than assumed

- **No account.** The counterfactual is public in the ISIMIP repository. Four `counterclim` daily
  `tas` datasets exist for ISIMIP3a; the one to use is **GSWP3-W5E5**, the round's standard forcing.
- **Server-side point extraction works**, which is what makes this tractable at all. `POST` to
  `https://files.isimip.org/api/v2` with `{"paths": [...], "operations": [{"operation":
  "select_point", "point": [lat, lon]}]}` returns a job id; poll it; collect a zip. A nine-year daily
  series at one point is **243 KB**. Six files for one station took about 70 seconds.
  - The point order is `[latitude, longitude]`. Passing `[lon, lat]` fails loudly with "latitude is
    < -90", which is the good kind of API.
  - This is the same async request/poll/collect shape as the GBIF download API and CDS, so it fits
    the pattern `ingest/http.py` already carries.
- **ADR 0006's lesson does not apply here.** ARCO-ERA5 was unusable for point series because a chunk
  was the smallest fetchable unit and one station-hour cost 154 MB. ISIMIP subsets before it sends,
  so the cost is proportional to what is asked for.

**The binding limitation: `counterclim` ends in 2019.** The radar record runs to 2025. So this
comparison can cover **1995–2019, 25 of the 31 years**, and can say nothing about the last six. That
is the same shape of problem as DAMIP's `historical` runs stopping in 2014 and should be reported the
same way — as a window mismatch stated on the claim, not smoothed over.

## The scoping probe, and what it found

One station's grid cell (37.93°N, 93.65°W), June–July means, 1991–2019, naive linear trend:

| scenario | June–July trend |
| --- | --- |
| `obsclim` (factual) | **+0.590 °C/decade** |
| `counterclim` (counterfactual) | **+0.502 °C/decade** |

**ATTRICI removes about 0.088 °C/decade — roughly 15% of the local warming.** DAMIP's `f = 0.98` says
essentially all of the *modelled* warming was anthropogenic. These are not the same quantity and the
gap between them is the interesting part:

- `f` is a ratio of **ensemble-mean forced** signals. Averaging 15 models suppresses internal
  variability by construction, so what is left is close to pure forced response.
- ATTRICI operates on **one 0.5° cell's actual daily series**. A 29-year trend in local June–July
  temperature contains a great deal of internal variability, and only the part that co-varies with
  global mean temperature is removed.

So the honest reading of the probe is: **a local 29-year warming trend is mostly not GMT-correlated**,
which is a caution against reading `f = 0.98` as "98% of the warming at these stations was us". That
is a claim about the forced component, not about the trend a thermometer at one station measured.

Stated as a scoping observation, not a result. One station, one window, one naive fit, no interval.

## Predictions, registered now

1. **The ATTRICI counterfactual will remove substantially less than `f × S × W`.** Concretely, across
   the 78 claim-band stations, the ATTRICI-implied removal will be **under half** of DAMIP's
   −0.296 d/decade. The probe implies it, so this is close to a check that the pipeline reproduces
   what the probe saw rather than a discovery.
2. **`obsclim` will reproduce ERA5's warming at the same stations to within its own interval.** This
   is the control that licenses using the pair at all: if the *factual* half of ISIMIP disagrees with
   the reanalysis already in the lake, the counterfactual half cannot be trusted either. **A failure
   here stops the whole thing** — it would mean the two datasets are describing different places.
3. **The two counterfactuals will disagree beyond their intervals**, and the ribbon will therefore
   show four lines that do not collapse into two. If they agree, the extra line is redundant and
   should be dropped rather than shipped as false corroboration.
4. **Truncating DAMIP to 1995–2019 will not rescue the disagreement.** If matching the windows brings
   the two into line, then the disagreement was the window and not the method, and that is the
   finding instead.

## What this cannot establish

Neither counterfactual attributes the *animals*. Both attribute the warming the animals tracked,
through a response function fitted on observations — so a confounder common to both temperature and
passage date survives either one. That limit is unchanged from `phase2a-attribution.md` and adding a
second climate counterfactual does not touch it.

And a disagreement between the two does not adjudicate itself. If ATTRICI removes 15% where DAMIP
removes 98%, the right output is two numbers and an explanation of why they measure different things
— not an average, and not a decision about which is correct.
