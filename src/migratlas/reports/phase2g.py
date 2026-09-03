"""Phase 2g -- did the cells that got wetter gain birds? The southern atlas's rain.

Pre-registered in ``docs/methods/phase2g-southern-rain.md`` before the fetch. Southern Africa is
semi-arid and the one driver ever tested against its per-cell change was surface water; nobody had
asked the region's own question. Two five-year atlas epochs thirty years apart differ in how wet
they were, cell by cell, and that difference is the obvious explanatory driver for who was recorded.

**The cell-level question is Phase 1g's with rain in place of water**, and it is *called*: `fit`,
`toroidal_null`, `spectral_null` and `leave_one_quadrant_out` took a `driver` argument for this
purpose, so the two phases condition on effort identically. **The species-level question is new**:
each species' per-cell reporting rate in each epoch, its change regressed across the footprint on
the rainfall change conditioning on the change in cards, one coefficient per species before any
median.
"""

import logging
from dataclasses import dataclass
from typing import Final
from zlib import crc32

import numpy as np
import polars as pl
from scipy import stats

from migratlas.lake.identifiers import cell_site_id
from migratlas.lake.reader import scan_dataset
from migratlas.reports import phase1e, phase1f, phase1g
from migratlas.reports.phase3a import binomial_bar

log = logging.getLogger(__name__)

SEED: Final = 1
DRAWS: Final = 1_000

SOURCE_ID: Final = "era5_south"
PRECIPITATION: Final = "total_precipitation"
RAIN: Final = "rain"
"""The epoch-2 mean monthly rainfall minus the epoch-1 mean, mm per day."""
RAIN_FIRST: Final = "rain_first"
"""The epoch-1 mean, for the placebo."""

FIRST_EPOCH: Final[tuple[int, int]] = (1987, 1991)
SECOND_EPOCH: Final[tuple[int, int]] = (2008, 2012)

MONTHS_PER_EPOCH: Final = 60
"""Five years of twelve months. Prediction 1 asks for all of them at every cell."""

PLACEBO_QUANTILE: Final = 0.75
"""The wettest quarter by epoch-1 rainfall, where rain should not be what limits the birds."""

WATER_CALIBRATION: Final = -0.036
"""Phase 1g's published partial r, which the refactored path must reproduce to two decimals."""
CALIBRATION_TOLERANCE: Final = 5e-3

MIN_POINTS: Final = 2


@dataclass(frozen=True, slots=True)
class Coverage:
    cells: int
    with_rain: int
    complete: int
    """Cells with all 120 months present."""

    @property
    def landed(self) -> bool:
        return self.cells > 0 and self.complete == self.cells


@dataclass(frozen=True, slots=True)
class CellLevel:
    """Phase 1g's four quantities, on rain."""

    main: phase1g.Fit
    toroidal_p: float
    toroidal_usable: int
    spectral_p: float
    quadrants: tuple[phase1g.Fit, ...]
    placebo: phase1g.Fit
    placebo_spectral_p: float
    placebo_cells: int

    @property
    def wetter_gained(self) -> bool:
        """Prediction 3."""
        return self.main.water > 0 and self.spectral_p < phase1g.ALPHA

    @property
    def sign_survives_quadrants(self) -> bool:
        """Prediction 4."""
        return len({q.direction for q in self.quadrants}) == 1

    @property
    def placebo_quiet(self) -> bool:
        """Prediction 5."""
        return self.placebo_spectral_p >= phase1g.ALPHA


@dataclass(frozen=True, slots=True)
class SpeciesResponse:
    taxon_key: int
    taxon_label: str
    cells_detected: int
    coefficient: float
    """Change in reporting rate per mm per day of rainfall change, conditioning on cards."""
    half: float

    @property
    def clear(self) -> bool:
        return bool(np.isfinite(self.half)) and abs(self.coefficient) > self.half


@dataclass(frozen=True, slots=True)
class SpeciesLevel:
    responses: tuple[SpeciesResponse, ...]
    bar: int
    median: float
    interval: tuple[float, float]
    q_statistic: float
    q_bar: float

    @property
    def clear(self) -> int:
        return sum(1 for r in self.responses if r.clear)

    @property
    def more_than_chance(self) -> bool:
        """Prediction 6."""
        return self.clear > self.bar

    @property
    def heterogeneous(self) -> bool:
        """Prediction 7."""
        return bool(np.isfinite(self.q_statistic)) and self.q_statistic > self.q_bar


@dataclass(frozen=True, slots=True)
class Phase2g:
    coverage: Coverage
    calibration: float
    cells: CellLevel | None
    species: SpeciesLevel | None

    @property
    def calibrated(self) -> bool:
        return abs(self.calibration - WATER_CALIBRATION) < CALIBRATION_TOLERANCE


def _seed(name: str) -> int:
    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


# --- The driver -----------------------------------------------------------------------------


def rain_change() -> pl.DataFrame:
    """Per cell: the epoch-2 mean monthly rainfall minus the epoch-1 mean, and the epoch-1 mean.

    Keyed by the cell's own site id, because `era5_south`'s rows carry the ERA5 grid centre as
    their coordinates and the atlas cell as their site id.
    """
    rows = (
        scan_dataset("driver_samples", source_id=SOURCE_ID)
        .filter(pl.col("variable") == PRECIPITATION)
        .select(
            site_id=pl.col("site_id").cast(pl.String),
            year=pl.col("period_start").dt.year(),
            value=pl.col("value").cast(pl.Float64),
        )
        .collect()
    )
    first = (
        rows.filter(pl.col("year").is_between(*FIRST_EPOCH))
        .group_by("site_id")
        .agg(pl.col("value").mean().alias(RAIN_FIRST), pl.len().alias("months_first"))
    )
    second = (
        rows.filter(pl.col("year").is_between(*SECOND_EPOCH))
        .group_by("site_id")
        .agg(pl.col("value").mean().alias("rain_second"), pl.len().alias("months_second"))
    )
    return (
        first.join(second, on="site_id", how="inner")
        .with_columns((pl.col("rain_second") - pl.col(RAIN_FIRST)).alias(RAIN))
        .select("site_id", RAIN, RAIN_FIRST, "months_first", "months_second")
    )


def design() -> tuple[pl.DataFrame, Coverage]:
    """Phase 1f's cells with their change and effort, joined to the rainfall on the cell's id."""
    surface = phase1f.surface()
    response = pl.DataFrame(
        {
            "cell_lat": [c.cell_lat for c in surface.cells],
            "cell_lon": [c.cell_lon for c in surface.cells],
            "delta": [c.delta_detected for c in surface.cells],
            "delta_corrected": [c.delta for c in surface.cells],
            "effort": [c.cards_second - c.cards_first for c in surface.cells],
            "site_id": [cell_site_id(c.cell_lat, c.cell_lon) for c in surface.cells],
        }
    )
    joined = response.join(rain_change(), on="site_id", how="left")
    with_rain = joined.drop_nulls(RAIN)
    complete = with_rain.filter(
        (pl.col("months_first") == MONTHS_PER_EPOCH) & (pl.col("months_second") == MONTHS_PER_EPOCH)
    )
    coverage = Coverage(cells=response.height, with_rain=with_rain.height, complete=complete.height)
    return with_rain.drop("months_first", "months_second"), coverage


# --- The cells ------------------------------------------------------------------------------


def cell_level(frame: pl.DataFrame) -> CellLevel:
    """Phase 1g's four quantities, called with the rain as the driver."""
    toroidal_p, usable = phase1g.toroidal_null(frame, driver=RAIN)
    cut = float(np.quantile(frame[RAIN_FIRST].to_numpy(), PLACEBO_QUANTILE))
    wettest = frame.filter(pl.col(RAIN_FIRST) >= cut)
    return CellLevel(
        main=phase1g.fit(frame, driver=RAIN),
        toroidal_p=toroidal_p,
        toroidal_usable=usable,
        spectral_p=phase1g.spectral_null(frame, driver=RAIN),
        quadrants=tuple(phase1g.leave_one_quadrant_out(frame, driver=RAIN)),
        placebo=phase1g.fit(wettest, driver=RAIN),
        placebo_spectral_p=phase1g.spectral_null(wettest, driver=RAIN),
        placebo_cells=wettest.height,
    )


# --- The species ----------------------------------------------------------------------------


def reporting_rates(cells: pl.DataFrame) -> pl.DataFrame:
    """Per species per cell: the reporting rate in each epoch and its change, zeros included.

    `cells` is Phase 1e's footprint with its cards per epoch. A species never recorded in a cell in
    an epoch has a rate of nought there, which is a cell and not a gap -- the same reading Phase
    1e's occupancy fits take.
    """
    first = phase1e.detections("sabap1", phase1e.EPOCH_1, cells)
    second = phase1e.detections("sabap2", phase1e.EPOCH_2, cells)
    baseline = (
        first.group_by("taxon_key", "taxon_label")
        .agg(seen=pl.len())
        .filter(pl.col("seen") >= phase1e.MIN_SPECIES_CELLS)
        .select("taxon_key", "taxon_label", "seen")
    )
    keys = ["taxon_key", "cell_lat", "cell_lon"]
    grid = baseline.join(cells.select("cell_lat", "cell_lon", "n_1", "n_2"), how="cross")
    return (
        grid.join(first.select(*keys, k_1=pl.col("k")), on=keys, how="left")
        .join(second.select(*keys, k_2=pl.col("k")), on=keys, how="left")
        .with_columns(pl.col("k_1").fill_null(0.0), pl.col("k_2").fill_null(0.0))
        .with_columns(delta_rate=(pl.col("k_2") / pl.col("n_2")) - (pl.col("k_1") / pl.col("n_1")))
        .select("taxon_key", "taxon_label", "seen", "cell_lat", "cell_lon", "delta_rate")
    )


def _species_coefficient(
    rate: np.ndarray, rain: np.ndarray, effort: np.ndarray
) -> tuple[float, float]:
    """Slope on rain conditioning on effort, and its 95% half-width."""
    matrix = np.column_stack([np.ones_like(rain), rain, effort])
    dof = matrix.shape[0] - matrix.shape[1]
    if dof < 1 or np.linalg.matrix_rank(matrix) < matrix.shape[1]:
        return (float("nan"), float("nan"))
    solution, *_ = np.linalg.lstsq(matrix, rate, rcond=None)
    residuals = rate - matrix @ solution
    sigma2 = float(residuals @ residuals) / dof
    covariance = sigma2 * np.linalg.pinv(matrix.T @ matrix)
    return float(solution[1]), 1.96 * float(np.sqrt(covariance[1, 1]))


def species_level(
    frame: pl.DataFrame, rates: pl.DataFrame, *, draws: int = DRAWS
) -> SpeciesLevel | None:
    """One rainfall coefficient per species, then the pooled count, median and heterogeneity."""
    joined = rates.join(
        frame.select("cell_lat", "cell_lon", RAIN, "effort"),
        on=["cell_lat", "cell_lon"],
        how="inner",
    )
    responses: list[SpeciesResponse] = []
    groups = joined.group_by(["taxon_key", "taxon_label", "seen"], maintain_order=True)
    for (key, label, seen), group in groups:
        coefficient, half = _species_coefficient(
            group["delta_rate"].to_numpy().astype(float),
            group[RAIN].to_numpy().astype(float),
            group["effort"].to_numpy().astype(float),
        )
        if not np.isfinite(coefficient):
            continue
        responses.append(
            SpeciesResponse(
                taxon_key=int(key),
                taxon_label=str(label),
                cells_detected=int(seen),
                coefficient=coefficient,
                half=half,
            )
        )
    if len(responses) < MIN_POINTS:
        return None
    responses.sort(key=lambda r: (r.taxon_key, r.taxon_label))
    values = np.array([r.coefficient for r in responses])
    halves = np.array([r.half for r in responses])
    rng = np.random.default_rng(_seed("phase2g:species"))
    medians = np.array(
        [np.median(rng.choice(values, size=values.size, replace=True)) for _ in range(draws)]
    )
    keep = np.isfinite(halves) & (halves > 0)
    weights = 1.0 / (halves[keep] / 1.96) ** 2
    centre = float(np.sum(weights * values[keep]) / np.sum(weights))
    return SpeciesLevel(
        responses=tuple(responses),
        bar=int(binomial_bar(len(responses))),
        median=float(np.median(values)),
        interval=(float(np.percentile(medians, 2.5)), float(np.percentile(medians, 97.5))),
        q_statistic=float(np.sum(weights * (values[keep] - centre) ** 2)),
        q_bar=float(stats.chi2.ppf(0.95, int(keep.sum()) - 1)),
    )


# --- The phase ------------------------------------------------------------------------------


def collect(*, draws: int = DRAWS) -> Phase2g:
    """Calibrate Phase 1g's fit through the refactored path, then the cells, then the species."""
    calibration = phase1g.fit(phase1g._design()).partial_r  # noqa: SLF001 -- the project's own
    frame, coverage = design()
    if not coverage.landed:
        log.warning(
            "phase2g: rain at %d of %d cells, %d complete",
            coverage.with_rain,
            coverage.cells,
            coverage.complete,
        )
        return Phase2g(coverage=coverage, calibration=calibration, cells=None, species=None)
    cells = phase1e.footprint(phase1e.EPOCH_2)
    return Phase2g(
        coverage=coverage,
        calibration=calibration,
        cells=cell_level(frame),
        species=species_level(frame, reporting_rates(cells), draws=draws),
    )


def render() -> str:
    """Coverage, calibration, the cells, the species, one verdict line."""
    out = [
        "Phase 2g -- did the cells that got wetter gain birds?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2g-southern-rain.md before the fetch. The cell-level",
        "question is Phase 1g's with rain as the driver, called rather than copied; the",
        "species-level question is new. Predictions are graded in the note.",
        "",
    ]
    read = collect()
    landed = "landed" if read.coverage.landed else "DID NOT land"
    out.append(
        f"Coverage -- rain at {read.coverage.with_rain} of {read.coverage.cells} cells, "
        f"{read.coverage.complete} with all {MONTHS_PER_EPOCH * 2} months: {landed}"
    )
    out.append(
        f"Calibration -- Phase 1g's water partial r through the refactored path "
        f"{read.calibration:+.3f} against {WATER_CALIBRATION:+.3f}: "
        f"{'PASS' if read.calibrated else 'FAIL'}"
    )
    out.append("")
    if read.cells is None or not read.calibrated:
        return "\n".join([*out, "VERDICT: nothing above the gate is read."])

    c = read.cells
    out += [
        f"Cells -- rainfall change coefficient {c.main.water:+.3f} taxa per mm/day, partial r "
        f"{c.main.partial_r:+.3f}; toroidal p {c.toroidal_p:.3f} ({c.toroidal_usable} cells "
        f"usable per draw), spectral p {c.spectral_p:.3f}; naive p {c.main.naive_p:.3f} kept and "
        f"labelled -- wetter cells gained: {'YES' if c.wetter_gained else 'NO'}",
        "  leave-one-quadrant-out: "
        + ", ".join(f"{q.water:+.3f}" for q in c.quadrants)
        + f" -- sign survives: {'YES' if c.sign_survives_quadrants else 'NO'}",
        f"  placebo, wettest quarter ({c.placebo_cells} cells): coefficient "
        f"{c.placebo.water:+.3f}, spectral p {c.placebo_spectral_p:.3f} -- quiet: "
        f"{'YES' if c.placebo_quiet else 'NO'}",
        "",
    ]
    if read.species is not None:
        s = read.species
        out += [
            f"Species -- {len(s.responses)} with a rainfall coefficient; {s.clear} clear of zero "
            f"against a chance bar of {s.bar}; median {s.median:+.4f} [{s.interval[0]:+.4f}, "
            f"{s.interval[1]:+.4f}] per mm/day; Q {s.q_statistic:.1f} against {s.q_bar:.1f}",
            "",
        ]
    effect = "wetter gained" if c.wetter_gained else "no rainfall effect"
    verdict = [f"cells {effect} (spectral p {c.spectral_p:.3f})"]
    if read.species is not None:
        verdict.append(
            f"species clear of zero {read.species.clear} against bar {read.species.bar}; "
            f"Q {'clears' if read.species.heterogeneous else 'inside'}"
        )
    return "\n".join([*out, "VERDICT: " + "; ".join(verdict)])
