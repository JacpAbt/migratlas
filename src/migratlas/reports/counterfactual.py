"""Two worlds without us, drawn separately because they answer different questions.

The first version drew one chart with three lines. Two of those came from the same DAMIP ensemble --
`observed - f x S x W` and `observed - S x W`, with `f` at 0.98 -- so they sat 0.006 days apart and
were one piece of evidence drawn twice. `phase2a_attrici` replaced the second with a real
independent counterfactual, and it disagrees with the first by a factor of 2.4.

**So: two ribbons, one question each, two lines each.** Not one chart with four lines. Four lines
where two nearly coincide and two sit far apart invites a reader to average them, and averaging is
the one thing that must not happen here -- these are different quantities, not two estimates of one.

| ribbon | question | how it answers |
| --- | --- | --- |
| DAMIP | no human *forcing* | fifteen models run without it |
| ATTRICI | no *warming* | the observations, detrended against global mean temperature |

**Neither counterfactual is flat, and that is still the point.** Each removes only what it
attributes, and about half the observed advance does not track temperature at all. A flat
counterfactual would claim that unexplained half is natural.

**And each is drawn to the observed scatter, never to its own gap.** The DAMIP lines part by 0.89
days over thirty years and the ATTRICI lines by less; a reader has to be able to see that one gap is
smaller, which is impossible if each chart is rescaled to fill itself. Both use the same vertical
rule for that reason. See `docs/methods/counterfactual.md`.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 2
"""Bumped from 1: one ribbon with three lines became two ribbons with two lines each."""


@dataclass(frozen=True, slots=True)
class YearPoint:
    """One year's observed passage date, averaged across the claim band's stations."""

    year: int
    observed: float
    """Median passage day-of-year, meaned over stations. Lower is earlier."""
    stations: int
    spread: float
    """95% interval on the mean across stations -- the *sampling* spread, not the year-to-year
    variability, which is what the scatter of the points themselves shows."""


@dataclass(frozen=True, slots=True)
class Line:
    """A fitted trajectory, anchored so the two lines are comparable rather than offset."""

    key: str
    label: str
    per_decade: float
    start: float
    end: float
    note: str


@dataclass(frozen=True, slots=True)
class Ribbon:
    """One counterfactual, with everything needed to read it without the other."""

    key: str
    question: str
    """The counterfactual question, in the reader's words rather than the method's."""

    method_note: str
    """How it answers that question, in one line."""

    window: tuple[int, int]
    years: list[YearPoint]
    lines: list[Line]
    terms: dict[str, float]
    divergence: float
    """Days between the two lines at the end of the window."""

    caveat: str
    method: str


@dataclass(frozen=True, slots=True)
class Comparison:
    """Both ribbons, and why they disagree."""

    schema_version: int
    unit: str
    ribbons: list[Ribbon]
    disagreement: str
    """Why two honest counterfactuals give different numbers. The payload of showing both."""

    shared_caveat: str
    supporting: list[str] = field(default_factory=list)


def observed_series(max_year: int = 2025) -> list[YearPoint]:
    """Mean passage date per year across the stations the claim is made from."""
    from migratlas.evidence import EvidenceType, spec_for  # noqa: PLC0415
    from migratlas.metrics.phenology import passage_quantiles  # noqa: PLC0415
    from migratlas.reports.phase1 import (  # noqa: PLC0415
        AUTUMN,
        MIN_COVERAGE,
        MIN_NIGHTS,
        load_conus_nights,
    )
    from migratlas.reports.sandbox import CLAIM_BAND  # noqa: PLC0415

    nights = load_conus_nights(quantity="reflectivity_traffic")
    quantiles = passage_quantiles(
        nights.filter(pl.col("timestamp").dt.year() <= max_year),
        spec_for(EvidenceType.FLUX),
        seasons=[AUTUMN],
        quantiles=[0.5],
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    ).filter(pl.col("q50_doy").is_not_null())

    sites = nights.group_by("station_id").agg(pl.col("station_latitude").first())
    band = quantiles.join(sites, on="station_id", how="inner").filter(
        pl.col("station_latitude").is_between(*CLAIM_BAND, closed="left")
    )

    per_year = (
        band.group_by("year")
        .agg(
            observed=pl.col("q50_doy").mean(),
            deviation=pl.col("q50_doy").std(),
            stations=pl.len(),
        )
        .sort("year")
    )
    return [
        YearPoint(
            year=int(row["year"]),
            observed=float(row["observed"]),
            stations=int(row["stations"]),
            spread=(
                1.96 * float(row["deviation"]) / np.sqrt(row["stations"])
                if row["deviation"] is not None and row["stations"] > 1
                else 0.0
            ),
        )
        for row in per_year.iter_rows(named=True)
    ]


@dataclass(frozen=True, slots=True)
class Draft:
    """Everything one ribbon needs that differs between the two.

    A dataclass rather than eleven keyword arguments: a signature that long is one nobody can hold
    in their head, and the two call sites are easier to compare when the fields are a block.
    """

    key: str
    question: str
    method_note: str
    label: str
    note: str
    observed_slope: float
    removed: float
    years: list[YearPoint]
    terms: dict[str, float]
    caveat: str
    method: str


def _ribbon(draft: Draft) -> Ribbon:
    """Two lines through the window mean, because the attribution constrains slopes not levels."""
    window = (draft.years[0].year, draft.years[-1].year)
    midpoint = (window[0] + window[1]) / 2
    anchor = float(np.mean([point.observed for point in draft.years]))

    def line(key: str, label: str, per_decade: float, note: str) -> Line:
        return Line(
            key=key,
            label=label,
            per_decade=per_decade,
            start=anchor + per_decade / 10 * (window[0] - midpoint),
            end=anchor + per_decade / 10 * (window[1] - midpoint),
            note=note,
        )

    return Ribbon(
        key=draft.key,
        question=draft.question,
        method_note=draft.method_note,
        window=window,
        years=draft.years,
        lines=[
            line(
                "observed",
                "what happened",
                draft.observed_slope,
                "The fitted trend at the claim-band stations, and the number the ledger publishes.",
            ),
            line(
                "counterfactual",
                draft.label,
                draft.observed_slope - draft.removed,
                draft.note,
            ),
        ],
        terms=draft.terms,
        divergence=abs(draft.removed) / 10 * (window[1] - window[0]),
        caveat=draft.caveat,
        method=draft.method,
    )


def collect(max_year: int = 2025) -> Comparison:
    """Both ribbons, from each attribution's own terms, recomputed rather than quoted."""
    from migratlas.reports import phase2a_attribution as attribution  # noqa: PLC0415
    from migratlas.reports import phase2a_attrici as second  # noqa: PLC0415

    years = observed_series(max_year)
    if not years:
        msg = "no claim-band station has a passage series; run the radar ingest first"
        raise RuntimeError(msg)

    simulations = attribution.simulated()
    windows = [
        found
        for window in attribution.WINDOWS
        if (found := attribution.fraction(simulations, window)) is not None
    ]
    seen = attribution.observed()
    if not windows or seen is None:
        msg = "the attribution has no fraction or no observed terms; run its ingests first"
        raise RuntimeError(msg)
    primary = attribution.chosen(windows)
    damip_removed = primary.ensemble * seen.explained

    ribbons = [
        _ribbon(
            Draft(
                key="damip",
                question="What if there had been no human forcing?",
                method_note=(
                    f"{primary.models} CMIP6 models run with and without it, and the ratio between "
                    # Not "the birds": this claim's taxon scope is `unattributed`, and the margin
                    # beside the chart says so. The radar measures aerial biomass.
                    "them applied to the warming these stations actually recorded."
                ),
                label="no human forcing",
                note=(
                    "The observed trend with the attributed human share removed. It still "
                    "advances, because about half the observed advance does not track "
                    "temperature at all and was never attributed to anything; flattening it "
                    "would claim that half is natural."
                ),
                observed_slope=seen.advance,
                removed=damip_removed,
                years=years,
                terms={
                    "sensitivity_days_per_degree": seen.sensitivity,
                    "warming_degrees_per_decade": seen.warming,
                    "thermal_days_per_decade": seen.explained,
                    "human_share_of_warming": primary.ensemble,
                    "removed_days_per_decade": damip_removed,
                    "observed_days_per_decade": seen.advance,
                    "stations": float(seen.stations),
                    "models": float(primary.models),
                },
                caveat=(
                    "The share is a ratio of forced warming as the ensemble mean has it. "
                    "Averaging "
                    f"{primary.models} models suppresses year-to-year variability by "
                    "construction, so this is a statement about the forced signal and not about "
                    "the trend any one thermometer measured. CMIP6's historical runs also stop "
                    "in 2014 while the radar record runs to 2025."
                ),
                method="docs/methods/phase2a-attribution.md",
            )
        )
    ]

    # The second ribbon only exists if its own control passed. Pre-registered as a stop condition:
    # if ISIMIP's factual half disagrees with the ERA5 warming already in the lake, the pair is
    # describing a different place and drawing it would be worse than leaving it out.
    answer = second.attributed(seen.sensitivity, seen.sensitivity_ci95)
    if answer is None:
        log.warning("the second counterfactual's control did not pass; drawing DAMIP alone")
        disagreement = (
            "There is only one ribbon here. A second, independent counterfactual exists and did "
            "not earn its place: its factual half has to reproduce the reanalysis already in "
            "the lake before its counterfactual half can be read, and it did not. So the pair "
            "is describing a different climate than the one these animals were in. Said here "
            "rather than quietly dropped, because a check that only ever passes is not a check."
        )
        supporting = []
    else:
        window = answer.window
        ribbons.append(
            _ribbon(
                Draft(
                    key="attrici",
                    question="What if there had been no warming at all?",
                    method_note=(
                        "The observations themselves, with the part of each station's daily series "
                        "that tracks global mean temperature removed. No model involved."
                    ),
                    label="no warming",
                    note=(
                        "The observed trend with the warming-correlated share removed. Smaller "
                        "than the forcing answer, and the gap between the two is the point: "
                        "most of a 25-year trend at one place does not move with the global "
                        "mean at all."
                    ),
                    observed_slope=seen.advance,
                    removed=answer.advance,
                    # Windowed to where the counterfactual exists, so the chart is not drawn over
                    # years it says nothing about.
                    years=[point for point in years if window[0] <= point.year <= window[1]],
                    terms={
                        "sensitivity_days_per_degree": seen.sensitivity,
                        "warming_removed_degrees_per_decade": answer.warming_removed,
                        "warming_removed_ci95": answer.warming_removed_ci95,
                        "share_of_factual_warming": answer.share_of_factual,
                        "removed_days_per_decade": answer.advance,
                        "removed_days_ci95": answer.advance_ci95,
                        "observed_days_per_decade": seen.advance,
                        "stations": float(answer.stations),
                    },
                    caveat=(
                        f"This covers {window[0]}-{window[1]}, because the counterfactual ends in "
                        f"{window[1]} while the radar record runs to {max_year}. It says nothing "
                        "about the last six years. The detrending removes what correlates with "
                        "global mean temperature, which at one half-degree cell is a smaller share "
                        "of the trend than the forced signal is."
                    ),
                    method="docs/methods/phase2a-attrici.md",
                )
            )
        )
        disagreement = (
            "The two ribbons disagree by a factor of about "
            f"{abs(damip_removed / answer.advance):.1f}, and both are right — they are not "
            "two estimates of one number. The forcing ribbon asks how much of the forced part "
            f"of the warming was human, and gets {primary.ensemble:.0%} — but it reaches that by "
            f"averaging {primary.models} models, which cancels the year-to-year weather until "
            "almost nothing but the forced signal is left. The warming ribbon works on one "
            "half-degree patch of real daily temperature, where a 25-year trend is largely "
            f"weather that leaned one way, and only {answer.share_of_factual:.0%} of it moves "
            "with the globe. So the distance between the two ribbons is itself a measurement: "
            f"roughly {1 - abs(answer.advance / damip_removed):.0%} of the warming at these "
            "stations does not follow the global mean at all. Across twenty-five years at one "
            "cell, most of that is weather leaning one way — but it also holds any forcing that "
            "does not scale with the global average, which makes it an upper bound on the "
            "chance part rather than a reading of it. Averaging the two ribbons would destroy "
            "all of this and answer neither question."
        )
        supporting = [
            "Shuffling the years destroys the observed trend entirely (-0.56 to -0.001 days per "
            "decade), so the line being drawn is order and not arithmetic.",
            "A synthetic null on two halves of one climate experiment returns 3% of the forced "
            "difference, so the forcing method does not manufacture a gap where none exists.",
            "The factual half of the warming answer reproduces the reanalysis already in the lake "
            f"to {answer.control_gap:.3f} °C per decade, which is the control that licenses "
            "using its counterfactual at all.",
        ]

    return Comparison(
        schema_version=SCHEMA_VERSION,
        unit="day of year",
        ribbons=ribbons,
        disagreement=disagreement,
        shared_caveat=(
            "Both attribute the warming, not the animals. Each removes a share of the temperature "
            "signal and passes it through a response function fitted on observations, so anything "
            "that moved both temperature and passage date together survives either one. And the "
            "attribution is of the *trend*: no single year's date can be called human-caused."
        ),
        supporting=supporting,
    )


def render(comparison: Comparison) -> str:
    return json.dumps(asdict(comparison), indent=1)


def write(destination: Path, computed: Comparison | None = None) -> int:
    payload = render(computed if computed is not None else collect())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload + "\n", encoding="utf-8")
    return len(payload)
