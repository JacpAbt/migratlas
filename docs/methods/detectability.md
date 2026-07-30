# Where change could ever be measured

`docs/DATASETS.md` audits the lake source by source and reaches a conclusion that is easy to write
and hard to feel: **global extent and measurable change are, so far, different data.** This note
records how that conclusion became a map, and what the map is allowed to say.

Built after the fact rather than pre-registered, because it makes no estimate. Every threshold in it
is one an earlier phase already published, and the only new work is the geography.

## The question it asks, and the one it does not

There is a mature literature on biodiversity knowledge gaps — the Wallacean shortfall and its
relatives — asking **do we know where species are**. This asks **could a change here ever be
detected**, which needs three things the first question does not:

1. a time axis,
2. a repeated protocol,
3. effort fixed or at least measured by design.

The two maps disagree sharply, and the disagreement is the point. `obis_speciesgrids` covers 46,809
one-degree cells and scores as well as anything in the lake on knowing where species are. It cannot
support a single trend.

## The rule

One status per cell, taken as the **best** any source can give it. A cell that FISHGLOB can trend and
OBIS cannot is detectable: the limitation belongs to the source, not to the place.

| status | meaning |
| --- | --- |
| `no-time-axis` | one pooled epoch, so there is nothing to trend |
| `effort-not-measured` | records exist with no per-year record of sampling |
| `too-short` | a repeated protocol, fewer than 15 years in any one unit |
| `detectable` | 15 years or more in one unit, with effort accounted for |

Fifteen years is not invented here. It is the bar `phase1b` and `phase2a_timing` already apply, and
the bar ENRAM failed — one radar of roughly 190 reaches it, which is why that source is not in the
lake at all.

Each source also carries a **ceiling**: the best status it can reach anywhere, decided from its own
method note rather than from its row count. A source capped at `no-time-axis` is not reported as
`too-short`, because that would name the wrong problem: MegaMove's 3.5 million rows are not a short
series, they are one interval.

## Years are counted per protocol unit, never per cell

The layer's one substantive computation, and there are two wrong ways to do it that both produce a
plausible map.

Counting per **cell** lets a rotating set of one-year sites add up to a series — fifteen sites
visited once each would read as fifteen years of monitoring. Counting per **visit** does the opposite:
a trawl haul happens once, so every unit gets a single year.

The second mistake shipped. FISHGLOB's `site_id` is `survey_unit:haul_id`, so counting per `site_id`
reported **0 of 1,126 cells detectable** — twenty-nine scientific bottom-trawl surveys, several
running since the 1960s, described as unable to support a trend. What repeats in a stratified trawl
survey is the *stratum*, which FISHGLOB does not ship; `phase1b` pools by survey programme for
exactly that reason, and this now does the same. The corrected figure is 676 of 1,126.

So each source declares which unit carries its protocol: a radar station, a survey route, an atlas
pentad, a survey programme. A gridded surface has no unit inside a cell and falls back to the cell —
and both sources in that shape are capped below `too-short` anyway, so the fallback only affects how
their own coverage reads, never whether they pass.

## What it found

| status | cells | share |
| --- | --- | --- |
| `effort-not-measured` | 43,939 | 87.9% |
| `no-time-axis` | 3,144 | 6.3% |
| `detectable` | 1,997 | 4.0% |
| `too-short` | 886 | 1.8% |

Per source, ordered by what they can support:

| source | realm | ceiling | cells | detectable |
| --- | --- | --- | --- | --- |
| `bbs` | terrestrial | detectable | 1,458 | 1,225 |
| `fishglob` | marine | detectable | 1,126 | 676 |
| `sabap2` | terrestrial | detectable | 431 | 174 |
| `darkecology_daily` | aerial | detectable | 161 | 156 |
| `sabap1` | terrestrial | detectable | 133 | 23 |
| `obis_speciesgrids` | marine | effort not measured | 46,809 | 0 |
| `megamove` | marine | no time axis | 29,304 | 0 |
| `ebird_status_trends` | aerial | no time axis | 1,176 | 0 |

**Four per cent.** That is the finding, and it is not a statement about this project's ambition:
long digitised radar and trawl series exist where they were funded, and nowhere else. A results map
without this underneath it would invite a reader to think the empty ocean was empty of animals rather
than of measurement.

The three sources that clear the bar on land are all citizen science or roadside-by-design, so each
carries an `effort_note` that any claim built on it has to carry too. Clearing the bar is not the
same as being unbiased.

## A rendering bug that looked like a projection artefact

Worth recording because of how it presented. The wire format encodes a cell as an integer index and
the frontend inverts it as `(index + 0.5) × size − 180`. Written without the matching `+ 180` offset
before the divide, every cell decoded 180° west and 90° south — and on a globe the wrapped result
drew as a dense crescent along the limb, which is exactly what a genuine projection problem looks
like. `tests/test_detectability.py` now decodes the published indices back to coordinates and asserts
they land in bounds and span both hemispheres.

## What this layer must not be read as

- **Not a map of where animals are.** It is an assessment of what eight sources can support.
- **Not a map of where change has been found.** Only one system in the lake has a detected,
  attributed change; `detectable` means the question could be asked.
- **Not a statement about a species.** A cell detectable for a trawl survey's fish says nothing about
  whether a bat could be counted there.
- **Not global.** Cells with no source at all are absent from the grid rather than marked, because
  the lake has nothing to say about them, and colouring them would be an assertion.
