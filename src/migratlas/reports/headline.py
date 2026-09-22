"""Each claim's headline result as a picture, computed from the lake like the number it draws.

A first reading of the book found that a project about numbers showed almost none of them as
pictures: the claim page carried a world map with one circle on it, and the same map three times in
one chapter. The result the sentence states -- the busiest night sliding earlier, eighteen seas
pulling in different directions, a pile of species centred on nothing -- was never drawn.

**One document, one small chart per claim, three shapes.** A *years* chart where the claim is a
trend: the measured value per year, with the published slope drawn through the series' own mean
so the line is the ledger's number and not a second fit. A *histogram* where the claim is about a
pile of units -- species, surveys, stations -- and the finding is the shape of the pile. A *strip*
where the units are few enough to name, one bar each with its interval, around a zero line.

**Every value comes from the same functions the ledger calls**, in the same order, so a chart
cannot disagree with the sentence under it. Where a report kept its per-unit values private this
module asks the report for them rather than reading the lake again: `phase1k.flight_slopes`,
`phase1c.airspeed_by_year` and `findings.autumn_band_slopes` were split out of the functions that
already computed them, and those functions call the same thing.

**Four claims draw nothing new here, on purpose.** The attribution has its counterfactual ribbon
and the coverage limit has its assessment, both figures in their own right. The transfer test is
three numbers, which the sentence says better than three bars; and the protocol disagreement is a
ratio of two scatters, which no honest single picture carries. Those pages keep the plate.

Nothing here is a claim and nothing is pre-registered: a chart is a figure of values the ledger
already publishes, drawn from the same computation. `tests/test_headline.py` holds the binning and
the anchoring to their arithmetic, and holds every key here to a published finding.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final

import numpy as np

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 1

PUBLIC: Final = Path("web/public")
DOCUMENT: Final = PUBLIC / "headline.json"

BINS: Final = 24
"""Bars in a histogram. Enough to show a shape, few enough that each is a stroke."""

CLIP: Final = (1.0, 99.0)
"""Percentiles a histogram's axis is cut at. A pile with a tail out to five times its own spread
would spend most of the page on three units; what is cut is counted and said, never hidden."""


@dataclass(frozen=True, slots=True)
class Point:
    """One year of one series."""

    year: int
    value: float
    n: int
    """How many units the year's value averages over -- stations, animals."""


@dataclass(frozen=True, slots=True)
class Trend:
    """The published slope, drawn through the series' own mean rather than fitted again."""

    per_decade: float
    start: float
    end: float


@dataclass(frozen=True, slots=True)
class Series:
    key: str
    label: str
    points: list[Point]
    trend: Trend | None


@dataclass(frozen=True, slots=True)
class Years:
    unit: str
    series: list[Series]
    kind: str = "years"


@dataclass(frozen=True, slots=True)
class Bin:
    low: float
    high: float
    count: int


@dataclass(frozen=True, slots=True)
class Mark:
    """A vertical rule the reader is meant to compare the pile or the bars against."""

    value: float
    label: str


@dataclass(frozen=True, slots=True)
class Histogram:
    unit: str
    bins: list[Bin]
    marks: list[Mark]
    n: int
    clipped: int
    """Units outside the drawn axis, counted so the cut is stated on the page."""
    kind: str = "histogram"


@dataclass(frozen=True, slots=True)
class Bar:
    label: str
    value: float
    low: float | None
    high: float | None


@dataclass(frozen=True, slots=True)
class Strip:
    unit: str
    bars: list[Bar]
    marks: list[Mark]
    kind: str = "strip"


@dataclass(frozen=True, slots=True)
class Headline:
    """One claim's picture, with the two sentences a reader needs to read it."""

    key: str
    title: str
    """What the picture shows, in the plain register. Carries no digit."""
    reading: str
    """How to read it: what one dot, bar or point is, and what the line means."""
    chart: Years | Histogram | Strip


@dataclass(frozen=True, slots=True)
class Document:
    schema_version: int
    headlines: list[Headline] = field(default_factory=list)


# --- The arithmetic, held to tests ---------------------------------------------------------------


def anchored(points: list[Point], per_decade: float) -> Trend:
    """The published slope drawn through the mean of the points, over the years they span.

    The ribbon does the same: a line fitted again to the drawn points would be a second estimator
    and could disagree with the number under it. Anchoring at the mean puts the ledger's slope
    through the middle of the evidence.
    """
    years = np.array([p.year for p in points], dtype=float)
    values = np.array([p.value for p in points], dtype=float)
    mid_year = float(years.mean())
    mid_value = float(values.mean())
    per_year = per_decade / 10.0
    return Trend(
        per_decade=per_decade,
        start=mid_value + per_year * (float(years.min()) - mid_year),
        end=mid_value + per_year * (float(years.max()) - mid_year),
    )


def histogram(
    values: np.ndarray, *, bins: int = BINS, clip: tuple[float, float] = CLIP
) -> tuple[list[Bin], int]:
    """Equal-width bins between the clip percentiles, and how many values fell outside them.

    Zero is always a bin edge when the range straddles it, so the pile's two sides can be read
    against the mark rather than against a bar that spans it.
    """
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return [], 0
    low, high = (float(x) for x in np.percentile(finite, clip))
    if high <= low:
        low, high = float(finite.min()), float(finite.max()) or (low + 1.0)
    if low < 0.0 < high:
        # Snap the edges outward so zero lands on one.
        width = (high - low) / bins
        low = -np.ceil(-low / width) * width
        high = np.ceil(high / width) * width
        edges = np.arange(low, high + width / 2, width)
    else:
        edges = np.linspace(low, high, bins + 1)
    counts, _ = np.histogram(finite, bins=edges)
    out = [
        Bin(low=float(edges[i]), high=float(edges[i + 1]), count=int(counts[i]))
        for i in range(len(counts))
    ]
    inside = int(counts.sum())
    return out, int(finite.size) - inside


def _median(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    return float(np.median(finite)) if finite.size else float("nan")


# --- The claims ------------------------------------------------------------------------------


def _autumn_advance() -> Headline | None:
    from migratlas.reports import counterfactual, findings  # noqa: PLC0415 -- heavy

    years = counterfactual.observed_series()
    if not years:
        return None
    slope, _ci, _n = findings.autumn_band_slopes()
    points = [Point(year=y.year, value=y.observed, n=y.stations) for y in years]
    return Headline(
        key="autumn-advance",
        title="The night the autumn passes, year by year",
        reading=(
            "Each dot is one autumn's middle night, averaged over the radar stations that "
            "reported. "
            "The line is the published trend, drawn through the middle of the dots."
        ),
        chart=Years(
            unit="day of year",
            series=[
                Series(
                    key="autumn",
                    label="autumn passage",
                    points=points,
                    trend=anchored(points, slope),
                )
            ],
        ),
    )


def _composition_stable() -> Headline | None:
    from migratlas.reports import phase1c  # noqa: PLC0415 -- heavy
    from migratlas.reports.phase1 import AUTUMN  # noqa: PLC0415

    by_year = phase1c.airspeed_by_year(AUTUMN)
    drift = phase1c.airspeed_trend(AUTUMN)
    if by_year is None or by_year.is_empty() or drift is None:
        return None
    points = [
        Point(year=int(row["year"]), value=float(row["airspeed"]), n=int(row["stations"]))
        for row in by_year.sort("year").iter_rows(named=True)
    ]
    return Headline(
        key="composition-stable",
        title="How fast whatever is up there flies, year by year",
        reading=(
            "Each dot is one autumn's flight speed through the air, wind taken out, averaged over "
            "the stations. The line is the published drift, and it is flat."
        ),
        chart=Years(
            unit="m/s",
            series=[
                Series(
                    key="airspeed",
                    label="airspeed",
                    points=points,
                    trend=anchored(points, drift.mean),
                )
            ],
        ),
    )


HERDS: Final[dict[str, str]] = {
    "movebank_yahatinda_elk": "Ya Ha Tinda elk",
    "movebank_svalbard_reindeer": "Svalbard reindeer",
}


def _displacement_flat() -> Headline | None:
    from migratlas.reports import phase1h  # noqa: PLC0415 -- heavy

    series: list[Series] = []
    for source_id in phase1h.SOURCES:
        found = phase1h.seasons(source_id)
        if not found:
            return None
        verdict = phase1h.grade(found)
        by_year: dict[int, list[float]] = {}
        for season in found:
            by_year.setdefault(season.year, []).append(season.displacement_km)
        points = [
            Point(year=year, value=float(np.median(values)), n=len(values))
            for year, values in sorted(by_year.items())
            if len(values) >= phase1h.MIN_ANIMALS
        ]
        if len(points) < 2:  # noqa: PLR2004 -- a line needs two years
            return None
        series.append(
            Series(
                key=source_id,
                label=HERDS.get(source_id, source_id),
                points=points,
                trend=anchored(points, verdict.slope_km_per_decade),
            )
        )
    return Headline(
        key="displacement-flat",
        title="How far each herd moves between winter and summer, year by year",
        reading=(
            "Each dot is one year's typical distance between a herd's winter and summer grounds. "
            "The lines are the published trends, one per herd."
        ),
        chart=Years(unit="km", series=series),
    )


def _marine_null() -> Headline | None:
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- heavy
    from migratlas.reports import phase1b  # noqa: PLC0415 -- heavy

    _, pooled, _ = phase1b.analyse(range_metrics.to_cells(phase1b.survey_unit(phase1b.load())))
    values = pooled["per_decade"].to_numpy().astype(float)
    if values.size == 0:
        return None
    bins, clipped = histogram(values)
    return Headline(
        key="marine-null",
        title="Which way each species moved, in each survey",
        reading=(
            "Every species in every survey is one count in the pile: to the right it moved north, "
            "to the left south. The pile sits on the zero line."
        ),
        chart=Histogram(
            unit="degrees latitude per decade",
            bins=bins,
            marks=[Mark(0.0, "no movement"), Mark(_median(values), "median")],
            n=int(values.size),
            clipped=clipped,
        ),
    )


def _atlas_no_net_change() -> Headline | None:
    from migratlas.reports import phase1e  # noqa: PLC0415 -- heavy, two and a half minutes

    pairs = phase1e.paired()
    values = np.array([p.primary.delta_psi for p in pairs if p.primary.reportable], dtype=float)
    if values.size == 0:
        return None
    bins, clipped = histogram(values)
    return Headline(
        key="atlas-no-net-change",
        title="How much more, or less, of the country each species occupies now",
        reading=(
            "Every species is one count: to the right it is found in more squares than thirty "
            "years ago, to the left fewer. The pile sits on the zero line."
        ),
        chart=Histogram(
            unit="change in the chance a square holds the species",
            bins=bins,
            marks=[Mark(0.0, "no change"), Mark(_median(values), "median")],
            n=int(values.size),
            clipped=clipped,
        ),
    )


def _flight_advance() -> Headline | None:
    from migratlas.reports import phase1k  # noqa: PLC0415 -- heavy

    fitted = phase1k.flight_slopes()
    if fitted is None:
        return None
    slopes, _series = fitted
    values = slopes["per_decade"].to_numpy().astype(float)
    bins, clipped = histogram(values)
    return Headline(
        key="flight-advance",
        title="How much earlier each butterfly flies, place by place",
        reading=(
            "Every species at every site is one count: to the left it flies earlier each decade, "
            "to the right later. Most of the pile is left of the zero line."
        ),
        chart=Histogram(
            unit="days per decade",
            bins=bins,
            marks=[Mark(0.0, "no change"), Mark(_median(values), "median")],
            n=int(values.size),
            clipped=clipped,
        ),
    )


def _skill_sparse() -> Headline | None:
    from migratlas.reports import phase3a  # noqa: PLC0415 -- heavy

    results = [r for r in phase3a.aerial() if r.season == "autumn"]
    if not results:
        return None
    values = np.array([r.full.score for r in results], dtype=float)
    bins, clipped = histogram(values)
    beat = sum(1 for r in results if r.full.significant)
    return Headline(
        key="skill-sparse",
        title="How well next autumn could be predicted, station by station",
        reading=(
            "Every radar station is one count. At the zero line a forecast knows nothing the "
            "long-run average did not; to the right it does better, to the left worse. "
            f"{beat} of {len(results)} beat their own shuffled years."
        ),
        chart=Histogram(
            unit="forecast skill",
            bins=bins,
            marks=[Mark(0.0, "no better than the average")],
            n=int(values.size),
            clipped=clipped,
        ),
    )


def _seas_disagree() -> Headline | None:
    from migratlas.reports import phase3e  # noqa: PLC0415 -- heavy

    fitted, _coverage, calibration = phase3e.units_3e()
    if not calibration.passes or not fitted:
        return None
    bars = sorted(
        (
            Bar(
                label=f"{u.segment.survey} ({u.segment.start}-{u.segment.end})",
                value=u.latitude_trend,
                low=u.latitude_trend - u.latitude_ci,
                high=u.latitude_trend + u.latitude_ci,
            )
            for u in fitted
        ),
        key=lambda b: b.value,
    )
    return Headline(
        key="seas-disagree",
        title="Which way the fish went, sea by sea",
        reading=(
            "Each bar is one stretch of shelf sea: how far north or south its fish moved each "
            "decade, with the range the survey can vouch for. They do not agree."
        ),
        chart=Strip(
            unit="degrees latitude per decade",
            bars=bars,
            marks=[Mark(0.0, "no movement")],
        ),
    )


def _projection_mask() -> Headline | None:
    from migratlas.drivers.cmip6 import SCENARIOS  # noqa: PLC0415 -- heavy
    from migratlas.reports import forecast_a  # noqa: PLC0415 -- heavy

    rows, _notes = forecast_a.cells()
    if not rows:
        return None
    bars: list[Bar] = []
    for scenario in SCENARIOS:
        for window in forecast_a.WINDOWS:
            subset = [c for c in rows if c.scenario == scenario and c.window == window]
            if not subset:
                continue
            share = 100.0 * sum(1 for c in subset if c.sayable) / len(subset)
            bars.append(Bar(label=f"{scenario}, {window}", value=share, low=None, high=None))
    if not bars:
        return None
    return Headline(
        key="projection-mask",
        title="How much of the map we can still speak for, future by future",
        reading=(
            "Each bar is one emissions future and one window of years: the share of radar "
            "stations whose warming stays inside the range we measured. Where the bar is short, "
            "we decline to guess."
        ),
        chart=Strip(unit="% of stations", bars=bars, marks=[]),
    )


BUILDERS: Final = (
    _autumn_advance,
    _flight_advance,
    _composition_stable,
    _marine_null,
    _atlas_no_net_change,
    _displacement_flat,
    _seas_disagree,
    _skill_sparse,
    _projection_mask,
)


def collect() -> Document:
    """Every headline the analyses can currently draw. Slow: it re-runs them."""
    headlines: list[Headline] = []
    for build in BUILDERS:
        drawn = build()
        if drawn is None:
            log.warning("%s: nothing to draw, the analysis withheld", build.__name__)
            continue
        log.info("%s: drawn", drawn.key)
        headlines.append(drawn)
    return Document(schema_version=SCHEMA_VERSION, headlines=headlines)


def render(document: Document) -> str:
    return json.dumps(asdict(document), indent=2, sort_keys=True, allow_nan=False) + "\n"


def write(destination: Path = DOCUMENT, computed: Document | None = None) -> int:
    """Publish it, sorted so a rebuild with no change is a no-op in the diff."""
    document = computed if computed is not None else collect()
    text = render(document)
    destination.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))
