"""Phase 2a, first link: thermal tracking in the bottom-trawl surveys.

Pre-registered in docs/methods/phase2a-thermal.md, including the three predictions and the
identifiability trap, before anything here was fitted.
"""

import logging
from typing import Final

import numpy as np
import polars as pl

from migratlas.drivers.schema import DRIVER_SAMPLES
from migratlas.lake.reader import scan_dataset
from migratlas.metrics import range as range_metrics
from migratlas.metrics import thermal
from migratlas.reports import phase1b

log = logging.getLogger(__name__)

SOURCE_ID: Final = "fishglob"

# Surveys whose occupied-temperature distribution is truncated from above, because a species at its
# thermal maximum there has nowhere warmer to be sampled. Flagged rather than excluded: the
# truncation biases a trend towards looking like tracking, so a reader has to know which rows carry
# it. Confound four in the method note.
WARM_CEILING: Final[tuple[str, ...]] = ("GMEX-Summer", "GMEX-Fall", "SEUS-summer", "SEUS-spring")

# Days per decade. Beyond this the survey's calendar moved enough that its thermal trend is a
# statement about when it sampled rather than about the ocean.
MATERIAL_DATE_DRIFT: Final = 3.0

# Index bands. A species whose occupied temperature rose at half its ocean's rate or less is
# holding its niche; one that rose faster than its ocean moved into warmer water.
TRACKING: Final = 0.5
WARMING: Final = -0.5


def temperatures() -> pl.DataFrame:
    """Per-haul bottom and surface temperature, one row per haul."""
    return (
        scan_dataset(DRIVER_SAMPLES.name, source_id=SOURCE_ID)
        .filter(pl.col("variable").is_in([thermal.BOTTOM, thermal.SURFACE]))
        .select("site_id", "variable", "value")
        .collect()
        .pivot(on="variable", index="site_id", values="value", aggregate_function="first")
    )


def load() -> pl.DataFrame:
    """Survey rows with the haul temperature attached.

    A left join, deliberately: a haul with no temperature is still a haul, and dropping it here
    would shrink the footprint that the consistency rule is computed from -- turning a gap in the
    thermometer into a gap in the survey.
    """
    frame = phase1b.survey_unit(phase1b.load())
    return frame.join(temperatures(), on="site_id", how="left")


def _mean_ci(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return (float("nan"), float("nan"))
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size) if values.size > 1 else 0.0
    return (float(values.mean()), ci)


def analyse(cells: pl.DataFrame) -> tuple[list[str], pl.DataFrame]:
    """Per-survey ambient trend, date drift and per-species tracking indices."""
    lines: list[str] = []
    rows: list[dict[str, object]] = []

    for (raw_unit,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        unit = str(raw_unit)
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue

        available = thermal.available(restricted)
        if available.is_empty():
            continue

        results, ambient = thermal.tracking(thermal.occupied(restricted), available)
        drift = thermal.date_drift(available)

        if ambient is None:
            lines.append(f"  {unit:<14} too few years of temperature to fit an ambient trend")
            continue

        flags = []
        if not ambient.distinguishable:
            flags.append("ambient warming not separable from zero")
        if drift and abs(drift.per_decade) > MATERIAL_DATE_DRIFT:
            flags.append(f"CALENDAR DRIFT {drift.per_decade:+.1f} d/decade")
        if unit in WARM_CEILING:
            flags.append("warm ceiling")

        share = float(available["share"].to_numpy().astype(float).mean())
        calendar = f"{drift.per_decade:+.1f}" if drift else "n/a"
        note = f"  [{'; '.join(flags)}]" if flags else ""
        lines.append(
            f"  {unit:<14} ambient {ambient.per_decade:+.3f} +/- {1.96 * ambient.stderr:.3f} "
            f"degC/dec ({ambient.years} yr), reading share {share:.0%}, "
            f"date {calendar} d/dec{note}"
        )

        # Prediction 3 needs the movement axes alongside the thermal one, from the same
        # restricted footprint so all three describe the same subset of the survey.
        series = range_metrics.centroids(restricted)
        moves = {}
        if not series.is_empty():
            for column, name in (("mean_latitude", "latitude"), ("mean_depth", "depth")):
                if column not in series.columns:
                    continue
                shifts = range_metrics.shift_per_decade(
                    series, column=column, min_years=thermal.MIN_YEARS
                )
                if not shifts.is_empty():
                    moves[name] = dict(
                        zip(shifts["taxon_label"], shifts["per_decade"], strict=True)
                    )

        for item in results:
            rows.append(
                {
                    "survey_unit": unit,
                    "taxon_label": item.taxon_label,
                    "occupied": item.occupied_per_decade,
                    "ambient": item.ambient_per_decade,
                    "index": item.held,
                    "years": item.years,
                    "latitude_shift": moves.get("latitude", {}).get(item.taxon_label, float("nan")),
                    "depth_shift": moves.get("depth", {}).get(item.taxon_label, float("nan")),
                    "date_drift": drift.per_decade if drift else float("nan"),
                    "warm_ceiling": unit in WARM_CEILING,
                }
            )

    return lines, pl.DataFrame(rows)


def by_which_axis(clean: pl.DataFrame) -> list[str]:
    """Prediction 3: is depth the route by which any tracking happens?

    The prediction worth the work. Prediction 2 -- that most species stay rather than track -- is
    close to a restatement of Phase 1b's null latitude shift. This is the part that says *how* the
    minority who do track manage it, in a network whose latitudes are static.

    Reported as one statement, not two. Deeper water is colder, so "went deeper" and "held its
    temperature" are one event described twice; the question is which axis carried it, never
    whether two independent lines of evidence agree.
    """
    lines = [
        "",
        "=" * 78,
        "prediction 3: which axis carries the tracking?",
        "=" * 78,
    ]
    usable = clean.filter(pl.col("depth_shift").is_not_nan(), pl.col("latitude_shift").is_not_nan())
    if usable.height < 30:  # noqa: PLR2004 -- too few pairs to correlate anything
        lines.append(f"\n  only {usable.height} pairs have both a depth and a latitude shift")
        return lines

    index = usable["index"].to_numpy().astype(float)
    lines.append(f"\n  {usable.height:,} pairs with a thermal index and both movement axes")
    for column, label, unit in (
        ("depth_shift", "depth shift", "m/dec"),
        ("latitude_shift", "latitude shift", "deg/dec"),
    ):
        values = usable[column].to_numpy().astype(float)
        mean, ci = _mean_ci(values)
        correlation = float(np.corrcoef(index, values)[0, 1])
        lines.append(
            f"    {label:<15} mean {mean:+7.3f} +/- {ci:.3f} {unit:<8} "
            f"corr with index {correlation:+.2f}"
        )

    # The direct form of the prediction: split on whether the species deepened, and compare.
    deepened = usable.filter(pl.col("depth_shift") > 0)
    shoaled = usable.filter(pl.col("depth_shift") <= 0)
    if deepened.height and shoaled.height:
        deep_mean, deep_ci = _mean_ci(deepened["index"].to_numpy().astype(float))
        shoal_mean, shoal_ci = _mean_ci(shoaled["index"].to_numpy().astype(float))
        lines.append(
            f"\n    deepened  (n={deepened.height:>4}): index {deep_mean:+.2f} +/- {deep_ci:.2f}"
        )
        lines.append(
            f"    shoaled   (n={shoaled.height:>4}): index {shoal_mean:+.2f} +/- {shoal_ci:.2f}"
        )
        gap = deep_mean - shoal_mean
        holds = gap > (deep_ci + shoal_ci)
        lines.append(
            f"    difference {gap:+.2f} -> prediction 3 "
            f"{'HOLDS' if holds else 'does NOT hold'}: species that went deeper "
            f"{'do' if holds else 'do not'} hold their temperature better"
        )
    return lines


def render() -> str:
    out = [
        "Phase 2a, first link -- thermal tracking in bottom-trawl surveys",
        "=" * 78,
        "Pre-registered in docs/methods/phase2a-thermal.md: bottom temperature, the Phase 1b",
        "consistent footprint, the occupied-against-available ratio, three predictions and the",
        "depth identifiability trap were all fixed before this ran.",
    ]

    frame = load()
    if frame.is_empty():
        out.append("\nNo FISHGLOB rows in the lake. Run `make ingest-fishglob` first.")
        return "\n".join(out)

    cells = range_metrics.to_cells(frame)
    with_bottom = frame[thermal.BOTTOM].is_not_null().to_numpy()
    out.append(
        f"\n{frame.height:,} survey rows, "
        f"{int(with_bottom.sum()):,} with a bottom temperature "
        f"({float(with_bottom.mean()):.0%})."
    )

    out += ["", "=" * 78, "per survey: did the water warm, and was the calendar stable?", "=" * 78]
    lines, tracked = analyse(cells)
    out += lines

    if tracked.is_empty():
        out += ["", "No survey had a separable ambient trend and a species with enough years."]
        return "\n".join(out)

    out += [
        "",
        "=" * 78,
        "tracking index: 1 = held its temperature, 0 = stayed and warmed, <0 = moved warmer",
        "=" * 78,
    ]

    clean = tracked.filter(pl.col("date_drift").abs() <= MATERIAL_DATE_DRIFT)
    out.append(
        f"\n{tracked.height:,} species-survey pairs; {clean.height:,} from surveys whose calendar "
        f"held to within {MATERIAL_DATE_DRIFT:.0f} d/decade."
    )

    for label, subset in (("all pairs", tracked), ("calendar-stable only", clean)):
        if subset.is_empty():
            continue
        index = subset["index"].to_numpy().astype(float)
        mean, ci = _mean_ci(index)
        out.append(
            f"\n  {label}: median index {float(np.median(index)):+.2f}, "
            f"mean {mean:+.2f} +/- {ci:.2f}"
        )
        out.append(
            f"    tracking (>{TRACKING}): {float((index > TRACKING).mean()):.0%}   "
            f"staying: {float(((index >= WARMING) & (index <= TRACKING)).mean()):.0%}   "
            f"moving warmer (<{WARMING}): {float((index < WARMING).mean()):.0%}"
        )

    out += ["", "per survey, calendar-stable pairs only:"]
    for (raw_unit,), group in clean.group_by(["survey_unit"], maintain_order=True):
        unit = str(raw_unit)
        index = group["index"].to_numpy().astype(float)
        mean, ci = _mean_ci(index)
        ceiling = " [warm ceiling]" if bool(group["warm_ceiling"][0]) else ""
        out.append(
            f"  {unit:<14} n={group.height:>4}  median {float(np.median(index)):+.2f}  "
            f"mean {mean:+.2f} +/- {ci:.2f}{ceiling}"
        )

    out += by_which_axis(clean)

    out += [
        "",
        "=" * 78,
        "Reading this: the index is a ratio, so a species whose occupied temperature rose as fast",
        "as its ocean scores 0 and one that held its temperature scores 1. Depth and temperature",
        "are not independent -- deeper is colder -- so 'went deeper' and 'held its temperature'",
        "are one event described twice, and are never counted as two findings.",
    ]
    return "\n".join(out)
