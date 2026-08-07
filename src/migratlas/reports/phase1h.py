"""Phase 1h — seasonal displacement in a collar record whose sampling changed 52-fold.

Pre-registered in `docs/methods/phase1h-elk.md`. The lake holds six million track fixes and no track
finding, because Phase 1d showed that swapping a radio collar for a GPS collar moves a measured
migration date by 46.8 days. This asks whether anything survives that, using a measure the
instrument cannot reach.

A path length accumulates along a track, so it scales with how often the collar reported. A
*displacement* between two calendar dates needs one fix near each and does not. Both are computed
here on the same animals in the same years: the confounded one is published beside the robust one,
which is what this project does when it has both.
"""

import logging
from dataclasses import dataclass
from statistics import median
from typing import TYPE_CHECKING, Final

import polars as pl
from scipy import stats

from migratlas.evidence import EvidenceType
from migratlas.lake.reader import scan
from migratlas.metrics.correlation import spearman

if TYPE_CHECKING:
    import numpy as np

log = logging.getLogger(__name__)

EARTH_KM: Final = 6371.0088

# Note §2. Fixed calendar blocks inside the settled part of each season, so an animal that shifted
# *when* it moved is invisible here -- which is the trade the note makes, because when-it-moved is
# what Phase 1d proved a collar record cannot measure.
WINTER: Final = (15, 60)
SUMMER: Final = (196, 241)

# Note §4. A year whose median rests on fewer animals than this is a year about those animals.
MIN_ANIMALS: Final = 10

# Note §3 predictions 1 and 2: the confound has to be shown, and the escape has to clear a bar.
CONFOUND_RHO: Final = 0.5
ESCAPE_RHO: Final = 0.2

# A within-animal slope needs an animal seen in more than one year, and a line needs more than
# two points. Below this the centred fit is not reported rather than being reported thinly.
MIN_CENTRED_POINTS: Final = 2


@dataclass(frozen=True, slots=True)
class Season:
    """One animal in one year, measured both ways."""

    individual_id: str
    year: int
    displacement_km: float
    """Winter position to summer position, straight line. Independent of fix rate."""

    path_km: float
    """Distance walked along the recorded fixes between those two dates. Not independent of it."""

    fixes: int
    median_gap_h: float


def _haversine(lat1: pl.Expr, lon1: pl.Expr, lat2: pl.Expr, lon2: pl.Expr) -> pl.Expr:
    """Great-circle kilometres between two positions given in degrees."""
    first, second = lat1.radians(), lat2.radians()
    return (
        2
        * EARTH_KM
        * (
            (
                ((second - first) / 2).sin() ** 2
                + first.cos() * second.cos() * ((lon2.radians() - lon1.radians()) / 2).sin() ** 2
            )
            .sqrt()
            .arcsin()
        )
    )


def seasons(source_id: str) -> list[Season]:
    """Winter-to-summer displacement and path length per animal-year, from the lake."""
    return from_fixes(
        scan(EvidenceType.TRACK, source_id=source_id)
        .select("individual_id", "timestamp", "latitude", "longitude")
        .collect(),
        label=source_id,
    )


def from_fixes(fixes: pl.DataFrame, *, label: str = "fixes") -> list[Season]:
    """The measurement itself, on any frame of fixes.

    Separate from the lake read so the central claim can be tested rather than argued: decimate a
    track and the displacement must not move while the path length does.

    Both measures come from the same rows so the comparison in §3 is about the measure and not about
    which animals happened to be in each.
    """
    frame = fixes.with_columns(
        year=pl.col("timestamp").dt.year(),
        doy=pl.col("timestamp").dt.ordinal_day(),
    )

    def centroid(low: int, high: int) -> pl.DataFrame:
        # The median position over a window, so one wandering day at the edge is not the season.
        return (
            frame.filter(pl.col("doy").is_between(low, high))
            .group_by("individual_id", "year")
            .agg(
                lat=pl.col("latitude").median(),
                lon=pl.col("longitude").median(),
                edge=pl.col("timestamp").max() if low == WINTER[0] else pl.col("timestamp").min(),
            )
        )

    winter = centroid(*WINTER)
    summer = centroid(*SUMMER)
    paired = winter.join(summer, on=["individual_id", "year"], how="inner", suffix="_summer")
    if paired.is_empty():
        return []

    paired = paired.with_columns(
        displacement_km=_haversine(
            pl.col("lat"), pl.col("lon"), pl.col("lat_summer"), pl.col("lon_summer")
        )
    )

    # The confounded measure, over exactly the stretch between the two seasonal anchors.
    walked = (
        frame.join(
            paired.select("individual_id", "year", "edge", "edge_summer"),
            on=["individual_id", "year"],
        )
        .filter(pl.col("timestamp").is_between(pl.col("edge"), pl.col("edge_summer")))
        .sort("individual_id", "year", "timestamp")
        .with_columns(
            prev_lat=pl.col("latitude").shift().over(["individual_id", "year"]),
            prev_lon=pl.col("longitude").shift().over(["individual_id", "year"]),
            gap_h=pl.col("timestamp").diff().over(["individual_id", "year"]).dt.total_seconds()
            / 3600,
        )
        .drop_nulls("prev_lat")
        .with_columns(
            step_km=_haversine(
                pl.col("prev_lat"), pl.col("prev_lon"), pl.col("latitude"), pl.col("longitude")
            )
        )
        .group_by("individual_id", "year")
        .agg(
            path_km=pl.col("step_km").sum(),
            fixes=pl.len(),
            median_gap_h=pl.col("gap_h").median(),
        )
    )

    joined = paired.join(walked, on=["individual_id", "year"], how="inner")
    log.info("%s: %d animal-years with both seasons", label, joined.height)
    return [
        Season(
            individual_id=str(row["individual_id"]),
            year=int(row["year"]),
            displacement_km=float(row["displacement_km"]),
            path_km=float(row["path_km"]),
            fixes=int(row["fixes"]),
            median_gap_h=float(row["median_gap_h"]),
        )
        for row in joined.iter_rows(named=True)
    ]


@dataclass(frozen=True, slots=True)
class Verdict:
    """Both measures against the sampling that produced them, and the trend in the robust one."""

    animal_years: int
    animals: int
    years: int
    path_vs_gap: float
    """Note §3 prediction 1: the confound, which has to be shown rather than asserted."""

    displacement_vs_gap: float
    """Note §3 prediction 2: the escape. The one the note lives or dies by."""

    slope_km_per_decade: float
    slope_ci95: float
    within_animal_slope: float
    """Note §4: the same trend fitted inside animals, so it cannot be collar turnover."""

    @property
    def confound_shown(self) -> bool:
        return abs(self.path_vs_gap) > CONFOUND_RHO

    @property
    def escape_holds(self) -> bool:
        return abs(self.displacement_vs_gap) < ESCAPE_RHO

    @property
    def moved(self) -> bool:
        """Whether the trend clears its own interval."""
        return abs(self.slope_km_per_decade) > self.slope_ci95


def grade(found: list[Season]) -> Verdict:
    """Every registered prediction, computed from one list of animal-years."""
    frame = pl.DataFrame(
        {
            "individual_id": [s.individual_id for s in found],
            "year": [s.year for s in found],
            "displacement": [s.displacement_km for s in found],
            "path": [s.path_km for s in found],
            "gap": [s.median_gap_h for s in found],
        }
    )
    gap = frame["gap"].to_numpy()
    slope, ci = _trend(frame["year"].to_numpy(), frame["displacement"].to_numpy())

    # Within animal: each animal centred on its own mean, so an animal collared only in late years
    # cannot contribute to the trend through its level.
    centred = frame.with_columns(
        year_c=pl.col("year") - pl.col("year").mean().over("individual_id"),
        disp_c=pl.col("displacement") - pl.col("displacement").mean().over("individual_id"),
    ).filter(pl.col("year_c") != 0)
    within = (
        _trend(centred["year_c"].to_numpy(), centred["disp_c"].to_numpy())[0]
        if centred.height > MIN_CENTRED_POINTS
        else float("nan")
    )

    return Verdict(
        animal_years=frame.height,
        animals=frame["individual_id"].n_unique(),
        years=frame["year"].n_unique(),
        path_vs_gap=spearman(gap, frame["path"].to_numpy())[0],
        displacement_vs_gap=spearman(gap, frame["displacement"].to_numpy())[0],
        slope_km_per_decade=slope,
        slope_ci95=ci,
        within_animal_slope=within,
    )


def _trend(year: np.ndarray, value: np.ndarray) -> tuple[float, float]:
    """Ordinary least squares in km per decade, with a 95% interval on the slope."""
    result = stats.linregress(year.astype(float), value)
    return float(result.slope * 10), float(result.stderr * 10 * 1.96)


SOURCES: Final = ("movebank_yahatinda_elk", "movebank_svalbard_reindeer")
"""Note §1's two records: the confounded herd, and the well-behaved one asked to replicate the
escape. Prediction 1 is registered for the elk only -- the reindeer fix interval varies 8-fold
against the elk's 104-fold, so there is little sampling variation for a path length to track."""


def render() -> str:
    """Both herds against the registered predictions, with the width the null must be read at."""
    out: list[str] = []
    for source_id in SOURCES:
        found = seasons(source_id)
        verdict = grade(found)
        median_km = median(s.displacement_km for s in found)
        out += [
            f"{source_id}: {verdict.animal_years} animal-years over {verdict.animals} animals "
            f"and {verdict.years} years",
            f"  path length vs fix gap   rho {verdict.path_vs_gap:+.3f}  "
            f"(confound shown at |rho| > {CONFOUND_RHO}: "
            f"{'yes' if verdict.confound_shown else 'no'})",
            f"  displacement vs fix gap  rho {verdict.displacement_vs_gap:+.3f}  "
            f"(escape holds at |rho| < {ESCAPE_RHO}: {'yes' if verdict.escape_holds else 'no'})",
            f"  displacement trend {verdict.slope_km_per_decade:+.2f} +/- "
            f"{verdict.slope_ci95:.2f} km/decade, within animals "
            f"{verdict.within_animal_slope:+.2f} -> "
            f"{'moved' if verdict.moved else 'no change detected'}",
            f"  median displacement {median_km:.2f} km; the +/- alone is "
            f"{verdict.slope_ci95 / median_km:.0%} of it per decade, so this null is wide "
            f"rather than bounded",
            "",
        ]
    return "\n".join(out)
