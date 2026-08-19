"""Forecast A: the fitted thermal response read forwards under scenario warming.

`docs/methods/forecast-a.md` binds all of it. There is no fit here and no null: this is arithmetic
on a coefficient the ledger already publishes, `S = -0.659 +/- 0.165` days per degC, multiplied by
each model's own June-July anomaly against its own 1995-2014 baseline. Which is also why it can run
at all on a response whose *test era* Phase 3f spent -- a within-station sensitivity read forwards
does not use an era split.

**The deliverable is the mask.** `S` was fitted over within-station departures whose 5th-to-95th
band is about +/-1.8 degC, and any warm scenario's late century leaves that range, where a straight
line is arithmetic rather than evidence. So the registered output is where the projection may be
stated at all, and the projected values only where it may.

The response and its envelope come from `response.fitted_response()`, shared with the reader-facing
dial rather than recomputed, so the slider and the scenario map cannot contradict each other about
the same coefficient.

Two things this module refuses to let a reader miss. Every row carries whether that station has any
*interannual* skill -- Phase 3a found it at 20 of 143 -- because a scenario response is not a
year-ahead forecast and the difference is presentation's job. And every row is the thermally-driven
component only: `anthropogenic-share` puts `-0.30 +/- 0.09` of the observed `-0.56 +/- 0.25` as
tracking pre-season temperature, so the rest is unexplained and unprojected here.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.constants import CLAIM_BAND
from migratlas.drivers.cmip6 import SCENARIO_SOURCE_ID, SCENARIOS
from migratlas.lake.reader import scan_dataset
from migratlas.reports.response import fitted_response

log = logging.getLogger(__name__)

BASELINE: Final[tuple[int, int]] = (1995, 2014)
"""The period every model's anomaly is taken against. Ends at 2014 because `historical` does, which
is the same window boundary the attribution ran into."""

WINDOWS: Final[dict[str, tuple[int, int]]] = {
    "2040-2059": (2040, 2059),
    "2080-2099": (2080, 2099),
}
"""Two, not a curve: the point is the contrast between a horizon inside the fitted range and one
outside it."""

MIN_MODELS: Final = 13
"""Below this the phase publishes as coverage. The count §1 measured for all four SSPs."""

MAX_SAYABLE_DAYS: Final = 2.0
"""Prediction 4's ceiling. `S` times the envelope's upper bound is about 1.15 days, so a sayable
projection larger than this would mean the mask was not applied."""

LATE_SAYABLE_SHARE: Final = 0.10
EARLY_SAYABLE_SHARE: Final = 0.50


@dataclass(frozen=True, slots=True)
class Cell:
    """One station, scenario and window: the warming, the mask, and the implied shift."""

    station_id: str
    scenario: str
    window: str
    models: int
    delta: float
    """Multi-model median June-July warming against the baseline, degC."""
    spread: float
    """Inter-model range of that warming, degC. Not uncertainty about the world."""
    sayable: bool
    """Inside the fitted 5-95 band."""
    sayable_extremes: bool
    """Inside the absolute observed range. The registered sensitivity, never the bound."""
    shift: float
    """`S x delta`, days. Negative is earlier. Meaningless where `sayable` is false."""
    shift_ci: float
    skilled: bool
    """Whether Phase 3a found interannual skill at this station. Carried on every row."""


def _member_mean(source_id: str, variable: str) -> pl.DataFrame:
    """Per model, station and year, averaged across members first.

    Members before models, always: CanESM5 and MIROC6 publish fifty each against three for nine
    other models, so a mean taken in the other order is a statement about two models.
    """
    return (
        scan_dataset("driver_samples", source_id=source_id)
        .filter(pl.col("variable") == variable)
        .with_columns(
            year=pl.col("period_start").dt.year(),
            model=pl.col("derived_from").str.split(":").list.get(2),
        )
        .group_by("model", "site_id", "year")
        .agg(pl.col("value").mean())
        .collect()
    )


def baseline() -> pl.DataFrame:
    """Each model's own 1995-2014 June-July mean, from the historical run already in the lake.

    Not re-fetched. The DAMIP ingest landed `historical` at these same stations over the same
    window, so the baseline the anomalies are differenced against costs nothing and is guaranteed
    to be the same water the attribution used.
    """
    historical = _member_mean("cmip6_damip", "air_temperature_2m_junjul_historical")
    return (
        historical.filter(pl.col("year").is_between(*BASELINE))
        .group_by("model", "site_id")
        .agg(pl.col("value").mean().alias("baseline"))
    )


def cells(skilled_stations: set[str] | None = None) -> tuple[list[Cell], list[str]]:
    """Every station-scenario-window, and the reasons any were dropped."""
    read = fitted_response()
    if read is None:
        return [], ["no published response in the claim band"]

    from migratlas.reports.phase2a_timing import sensitivities  # noqa: PLC0415 -- heavy

    in_band = {
        item.station_id
        for item in sensitivities()
        if CLAIM_BAND[0] <= item.latitude < CLAIM_BAND[1]
    }
    low, high = read.band
    floor, ceiling = read.extremes
    skilled = skilled_stations or set()

    base = baseline()
    notes: list[str] = []
    out: list[Cell] = []
    for scenario in SCENARIOS:
        scenario_rows = _member_mean(SCENARIO_SOURCE_ID, f"air_temperature_2m_junjul_{scenario}")
        # The inner join is the registered pairing: a model with a scenario and no baseline of its
        # own cannot contribute an anomaly, and the ingest deliberately landed more models than the
        # registration licenses.
        paired = scenario_rows.join(base, on=["model", "site_id"], how="inner").filter(
            pl.col("site_id").is_in(in_band)
        )
        models = paired["model"].n_unique()
        notes.append(f"{scenario}: {models} paired models")
        if models < MIN_MODELS:
            notes.append(f"{scenario}: below the floor of {MIN_MODELS}, no projection")
            continue

        for label, (start, end) in WINDOWS.items():
            window = (
                paired.filter(pl.col("year").is_between(start, end))
                .group_by("model", "site_id")
                .agg((pl.col("value").mean() - pl.col("baseline").first()).alias("delta"))
                .group_by("site_id")
                .agg(
                    delta=pl.col("delta").median(),
                    spread=pl.col("delta").max() - pl.col("delta").min(),
                    models=pl.col("model").n_unique(),
                )
            )
            for row in window.sort("site_id").iter_rows(named=True):
                delta = float(row["delta"])
                out.append(
                    Cell(
                        station_id=str(row["site_id"]),
                        scenario=scenario,
                        window=label,
                        models=int(row["models"]),
                        delta=delta,
                        spread=float(row["spread"]),
                        sayable=low <= delta <= high,
                        sayable_extremes=floor <= delta <= ceiling,
                        shift=read.thermal * delta,
                        shift_ci=read.thermal_ci * abs(delta),
                        skilled=str(row["site_id"]) in skilled,
                    )
                )
    return out, notes


def _share(rows: list[Cell], scenario: str, window: str) -> tuple[int, int, float]:
    """Sayable, total, and the share, for one scenario-window."""
    subset = [c for c in rows if c.scenario == scenario and c.window == window]
    sayable = sum(1 for c in subset if c.sayable)
    return sayable, len(subset), (sayable / len(subset) if subset else float("nan"))


def _grade(passed: bool) -> str:  # noqa: FBT001 -- a grade is a boolean by nature
    return "GRADED TRUE" if passed else "GRADED FALSE"


def render() -> str:
    """The registered numbers, every prediction graded, run exactly once."""
    read = fitted_response()
    rows, notes = cells()
    out = [
        "Forecast A -- the fitted response under scenario warming, and where it stops",
        "=" * 96,
        "Pre-registered in docs/methods/forecast-a.md before any scenario store was opened. No fit",
        "and no null: arithmetic on a published coefficient. The deliverable is the mask.",
        "",
    ]
    if read is None or not rows:
        out += ["No projectable cells. " + "; ".join(notes)]
        return "\n".join(out)

    low, high = read.band
    floor, ceiling = read.extremes
    out += [
        f"Response  S = {read.thermal:+.3f} +/- {read.thermal_ci:.3f} days per degC, "
        f"{read.stations} stations in {CLAIM_BAND[0]}-{CLAIM_BAND[1]}N",
        f"Envelope  band {low:+.2f} to {high:+.2f} degC (the bound); "
        f"absolute {floor:+.2f} to {ceiling:+.2f} (the sensitivity)",
        f"Baseline  {BASELINE[0]}-{BASELINE[1]}, each model against its own",
        "",
        "  " + "; ".join(notes),
        "",
        "=" * 96,
        "the mask, which is the result",
        "=" * 96,
        f"  {'scenario':10s} {'window':11s} {'sayable':>9s} {'of':>5s} {'share':>7s} "
        f"{'median dT':>10s} {'median shift':>13s}",
    ]
    for scenario in SCENARIOS:
        for window in WINDOWS:
            sayable, total, share = _share(rows, scenario, window)
            subset = [c for c in rows if c.scenario == scenario and c.window == window]
            if not subset:
                continue
            median_delta = float(np.median([c.delta for c in subset]))
            inside = [c.shift for c in subset if c.sayable]
            shift = f"{np.median(inside):+.2f} d" if inside else "-- masked --"
            out.append(
                f"  {scenario:10s} {window:11s} {sayable:9d} {total:5d} {share:6.0%} "
                f"{median_delta:+10.2f} {shift:>13s}"
            )

    early_share = _share(rows, "ssp126", "2040-2059")[2]
    late_share = _share(rows, "ssp585", "2080-2099")[2]
    monotone_scenario = all(
        _share(rows, a, w)[2] >= _share(rows, b, w)[2]
        for w in WINDOWS
        for a, b in zip(list(SCENARIOS), list(SCENARIOS)[1:], strict=False)
    )
    monotone_time = all(
        _share(rows, s, "2040-2059")[2] >= _share(rows, s, "2080-2099")[2] for s in SCENARIOS
    )
    sayable_shifts = [abs(c.shift) for c in rows if c.sayable]
    largest = max(sayable_shifts) if sayable_shifts else 0.0

    early = [c for c in rows if c.window == "2040-2059"]
    spread_days = float(np.median([abs(read.thermal) * c.spread for c in early])) if early else 0.0
    response_width = float(np.median([c.shift_ci for c in early])) if early else 0.0

    out += [
        "",
        "=" * 96,
        "predictions",
        "=" * 96,
        f"  1 (mask grows with warming and with time): "
        f"{_grade(monotone_scenario and monotone_time)}",
        f"  2 (ssp585 late century under {LATE_SAYABLE_SHARE:.0%} sayable): "
        f"{_grade(late_share < LATE_SAYABLE_SHARE)}  ({late_share:.0%})",
        f"  3 (ssp126 mid century over {EARLY_SAYABLE_SHARE:.0%} sayable): "
        f"{_grade(early_share > EARLY_SAYABLE_SHARE)}  ({early_share:.0%})",
        f"  4 (no sayable shift beyond {MAX_SAYABLE_DAYS:g} days): "
        f"{_grade(largest <= MAX_SAYABLE_DAYS)}  (largest {largest:.2f} d)",
        f"  5 (model spread at least as wide as the response interval): "
        f"{_grade(spread_days >= response_width)}  "
        f"(spread {spread_days:.2f} d against {response_width:.2f} d)",
        "",
        "=" * 96,
        "how to read this",
        "=" * 96,
        "A masked cell is not a small number, it is a refusal: the projection would sit",
        "outside the range S was fitted over, where a straight line is arithmetic rather than",
        "evidence.",
        "",
        "Every number here is the thermally-driven component only. anthropogenic-share puts",
        "-0.30 +/- 0.09 of the observed -0.56 +/- 0.25 days per decade as tracking pre-season",
        "temperature; the rest tracks nothing this project has found, and adding the two would be",
        "inventing the second.",
        "",
        "This is not a year-ahead forecast. Phase 3a found interannual skill at 20 of 143",
        "stations and Phase 3d refused a standing prediction on measured grounds. A scenario",
        "response and an",
        "interannual forecast are different objects; the skilled column exists so a reader cannot",
        "mistake one for the other.",
        "",
        "Wind, land use, light and the unexplained half are all held at no change, which is itself",
        "a claim about the future and is stated here rather than in a footnote.",
    ]
    return "\n".join(out)
