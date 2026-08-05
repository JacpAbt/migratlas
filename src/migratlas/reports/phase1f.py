"""Phase 1f — the atlas comparison, per cell.

Pre-registered in `docs/methods/phase1f-atlas-surface.md`. Phase 1e answers "did this species move"
and this answers "did this cell change", which is a different question with a different way of going
wrong: a per-cell number can draw where the volunteers went instead of where the animals are. §5 of
the note registers four stop conditions and the one that matters is the effort correlation.

The estimand is the expected count of the *analysed* taxa present in a cell -- the ones Phase 1e
could fit -- and not richness. Every scarce taxon is excluded by that floor, so the number is a
floor on richness and moves for reasons richness would not.

Nothing here is split by taxon, and that is the ethics constraint rather than a presentation choice:
the registry classifies both atlases `low` rather than `not_sensitive` because some taxa are
sensitive at fine scale, so a per-taxon per-cell surface would be a 27 km locator for each of them.
The sum over ~500 taxa is not one.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl
from scipy import stats

from migratlas.models import occupancy
from migratlas.reports import phase1e

log = logging.getLogger(__name__)

# Note §5. A cell needs this many taxa each moving by more than `MOVER_SHARE` of a whole presence,
# or its change is a handful of coin flips.
MIN_MOVERS: Final = 5
MOVER_SHARE: Final = 0.5

# Note §5, the condition the layer lives or dies by: if the change tracks the change in cards, the
# surface is a map of atlassing.
MAX_EFFORT_RHO: Final = 0.3

# Note §5. Past a tenth of cells failing the mover floor the surface is noise wherever it was
# not dropped either, so the whole layer goes.
MAX_DROP_SHARE: Final = 0.1

# Conventional, and named so the structure test cannot be loosened by editing a digit.
STRUCTURE_ALPHA: Final = 0.05

# Note §4 predictions 1 and 2, in taxa.
MAX_MEDIAN_DRIFT: Final = 1.5
MAX_MODEL_GAP: Final = 1.0

# Permutations for the Moran's I null, and the seed that makes it reproducible. A published p-value
# that moves between builds is not a published p-value.
PERMUTATIONS: Final = 999
SEED: Final = 1_987_2008


@dataclass(frozen=True, slots=True)
class CellChange:
    """One footprint cell, both epochs, corrected and naive."""

    cell_lat: float
    cell_lon: float
    first: float
    """Expected analysed taxa present in epoch 1."""
    second: float
    detected_first: float
    """Taxa actually recorded -- the uncorrected count, published beside the corrected one."""
    detected_second: float
    movers: int
    """Taxa whose presence in this cell changed by more than `MOVER_SHARE`."""
    cards_first: float
    cards_second: float

    @property
    def delta(self) -> float:
        return self.second - self.first

    @property
    def delta_detected(self) -> float:
        return self.detected_second - self.detected_first

    @property
    def steady(self) -> bool:
        """Enough taxa moved here for the cell's change to be more than a few coin flips."""
        return self.movers >= MIN_MOVERS


@dataclass(frozen=True, slots=True)
class Surface:
    """The computed surface and the size of the taxon set behind it."""

    cells: list[CellChange]
    taxa: int


def _counts(detections: pl.DataFrame, cells: pl.DataFrame, keys: list[int]) -> np.ndarray:
    """Cards recording each taxon per cell, as a dense (taxa x cells) matrix.

    Dense on purpose. 512 taxa by 496 cells is 254,000 floats, and the alternative -- one polars
    filter per taxon, as `phase1e.compare` does because it also has to fit each one -- is 512 passes
    over the same frame to build the same thing.
    """
    indexed = cells.with_row_index("cell_index").select("cell_lat", "cell_lon", "cell_index")
    joined = detections.join(indexed, on=["cell_lat", "cell_lon"], how="inner")
    at = {key: row for row, key in enumerate(keys)}
    out = np.zeros((len(keys), cells.height))
    for key, cell_index, k in joined.select("taxon_key", "cell_index", "k").iter_rows():
        row = at.get(int(key))
        if row is not None:
            out[row, int(cell_index)] = k
    return out


def _present(
    counts: np.ndarray, cards: np.ndarray, psi: np.ndarray, detection: np.ndarray
) -> np.ndarray:
    """Pr(present) per taxon per cell: one where recorded, the model's answer where silent.

    The silence term comes from `occupancy.occupied_given_silence` rather than being written out
    again here, so the map and the note's §5 cannot drift apart. Called per taxon because that
    function takes a scalar psi and p, which is what it is: a property of the taxon.
    """
    silence = np.vstack(
        [
            occupancy.occupied_given_silence(float(psi[row]), float(detection[row]), cards)
            for row in range(len(psi))
        ]
    )
    return np.where(np.minimum(counts, cards) > 0, 1.0, silence)


def surface() -> Surface:
    """The per-cell change, over the primary window's footprint.

    Refits rather than reading a cached fit, for the reason `findings.py` gives: a number that is
    computed once is a number that goes stale without telling anyone.
    """
    cells = phase1e.footprint(phase1e.EPOCH_2)
    first = phase1e.detections("sabap1", phase1e.EPOCH_1, cells)
    second = phase1e.detections("sabap2", phase1e.EPOCH_2, cells)

    # Note §3: the same taxa in both epochs, or the difference is partly a change of taxon set.
    # `reportable` is where that lives -- both fits converged, neither pinned at a boundary. The
    # note pointed at `paired()` for this, which is imprecise: `paired()` adds the second *window*,
    # which the surface does not use. Recorded in the results section rather than edited away.
    changes = [change for change in phase1e.compare(phase1e.EPOCH_2) if change.reportable]
    keys = [change.taxon_key for change in changes]
    log.info("surface: %d taxa over %d cells", len(keys), cells.height)

    cards_first = cells["n_1"].to_numpy()
    cards_second = cells["n_2"].to_numpy()
    counts_first = _counts(first, cells, keys)
    counts_second = _counts(second, cells, keys)

    present_first = _present(
        counts_first,
        cards_first,
        np.array([change.first.psi for change in changes]),
        np.array([change.first.p for change in changes]),
    )
    present_second = _present(
        counts_second,
        cards_second,
        np.array([change.second.psi for change in changes]),
        np.array([change.second.p for change in changes]),
    )

    moved = np.abs(present_second - present_first) > MOVER_SHARE
    cells_out = [
        CellChange(
            cell_lat=float(lat),
            cell_lon=float(lon),
            first=float(present_first[:, index].sum()),
            second=float(present_second[:, index].sum()),
            detected_first=float((counts_first[:, index] > 0).sum()),
            detected_second=float((counts_second[:, index] > 0).sum()),
            movers=int(moved[:, index].sum()),
            cards_first=float(cards_first[index]),
            cards_second=float(cards_second[index]),
        )
        for index, (lat, lon) in enumerate(cells.select("cell_lat", "cell_lon").iter_rows())
    ]
    return Surface(cells=cells_out, taxa=len(keys))


def _weights(changes: list[CellChange]) -> np.ndarray:
    """Queen contiguity on the quarter-degree grid, row-standardised.

    Contiguity rather than a distance kernel: the cells are a regular grid with holes in it, and a
    kernel would quietly reach across the holes -- which are the places nobody atlassed twice, so
    reaching across them is exactly the interpolation the note refuses.
    """
    lat = np.array([change.cell_lat for change in changes])
    lon = np.array([change.cell_lon for change in changes])
    step = phase1e.CELL_DEG
    close = (np.abs(lat[:, None] - lat[None, :]) <= step * 1.5) & (
        np.abs(lon[:, None] - lon[None, :]) <= step * 1.5
    )
    np.fill_diagonal(close, val=False)
    weights = close.astype(np.float64)
    total = weights.sum(axis=1, keepdims=True)
    standardised: np.ndarray = np.divide(
        weights, total, out=np.zeros_like(weights), where=total > 0
    )
    return standardised


def morans_i(values: np.ndarray, weights: np.ndarray) -> float:
    """Spatial autocorrelation of `values` under `weights`. Zero is no structure."""
    z = values - values.mean()
    denominator = float((z**2).sum())
    if denominator == 0:
        return 0.0
    return float(len(values) * (z @ weights @ z) / (weights.sum() * denominator))


@dataclass(frozen=True, slots=True)
class Verdict:
    """Every registered prediction and stop condition, graded."""

    cells: int
    taxa: int
    median_delta: float
    median_gap: float
    """Median |corrected - uncorrected| change, note §4 prediction 2."""
    morans_i: float
    morans_p: float
    effort_rho: float
    effort_p: float
    dropped: int
    """Cells failing the mover floor, note §5."""

    @property
    def drift_ok(self) -> bool:
        return abs(self.median_delta) <= MAX_MEDIAN_DRIFT

    @property
    def model_ok(self) -> bool:
        return self.median_gap <= MAX_MODEL_GAP

    @property
    def structure_ok(self) -> bool:
        return self.morans_i > 0 and self.morans_p < STRUCTURE_ALPHA

    @property
    def effort_ok(self) -> bool:
        return abs(self.effort_rho) < MAX_EFFORT_RHO

    @property
    def drop_share(self) -> float:
        return self.dropped / self.cells if self.cells else 1.0

    @property
    def publishable(self) -> bool:
        """Whether a layer may be drawn at all. Note §5, all four conditions."""
        return (
            self.drift_ok
            and self.model_ok
            and self.structure_ok
            and self.effort_ok
            and self.drop_share <= MAX_DROP_SHARE
        )


def _spearman(first: np.ndarray, second: np.ndarray) -> tuple[float, float]:
    """Rank correlation, with the constant-input case answered instead of raised.

    A constant array has no ranks to correlate and `scipy` warns, which this project turns into an
    error. The honest answer there is "no relationship detectable" rather than a crash on the way to
    deciding whether a layer may be published -- and a perfectly flat surface fails the structure
    condition anyway, so passing the effort one costs nothing.
    """
    if np.all(first == first[0]) or np.all(second == second[0]):
        return 0.0, 1.0
    result = stats.spearmanr(first, second)
    return float(result.statistic), float(result.pvalue)


def grade(changes: list[CellChange], taxa: int) -> Verdict:
    """Run every stop condition in the note against the computed surface."""
    delta = np.array([change.delta for change in changes])
    gap = np.abs(delta - np.array([change.delta_detected for change in changes]))
    effort = np.array([change.cards_second - change.cards_first for change in changes])

    weights = _weights(changes)
    observed = morans_i(delta, weights)
    rng = np.random.default_rng(SEED)
    null = np.array([morans_i(rng.permutation(delta), weights) for _ in range(PERMUTATIONS)])
    # One-sided, and the +1s count the observed value as one of its own draws -- without them a
    # p-value of exactly zero is reportable, which no permutation test can license.
    morans_p = float((np.sum(null >= observed) + 1) / (PERMUTATIONS + 1))

    effort_rho, effort_p = _spearman(np.abs(delta), effort)

    return Verdict(
        cells=len(changes),
        taxa=taxa,
        median_delta=float(np.median(delta)),
        median_gap=float(np.median(gap)),
        morans_i=observed,
        morans_p=morans_p,
        effort_rho=effort_rho,
        effort_p=effort_p,
        dropped=sum(1 for change in changes if not change.steady),
    )


def drawable(changes: list[CellChange], verdict: Verdict) -> pl.DataFrame:
    """The surface the note's stop conditions permit, as a frame `tiles/export.py` can take.

    The *uncorrected* count, and not by preference. Note §5 registered that a disagreement between
    the corrected and naive surfaces impeaches the model rather than the count, and sends the naive
    one to the map if prediction 2 fails. It failed, so this is what ships -- with the corrected
    surface computed on every build, graded, and withheld.

    Raises rather than returning an empty frame if the conditions that stop the layer outright have
    fired. A caller that quietly drew nothing would be indistinguishable from a build that worked.
    """
    if not (verdict.structure_ok and verdict.effort_ok and verdict.drop_share <= MAX_DROP_SHARE):
        msg = (
            f"phase1f: the surface is not publishable under the registered conditions -- "
            f"Moran's I {verdict.morans_i:+.4f} (p {verdict.morans_p:.4f}), effort rho "
            f"{verdict.effort_rho:+.4f}, {verdict.drop_share:.1%} of cells dropped. "
            f"See docs/methods/phase1f-atlas-surface.md section 5."
        )
        raise ValueError(msg)

    kept = [change for change in changes if change.steady]
    return pl.DataFrame(
        {
            "cell_longitude": [change.cell_lon for change in kept],
            "cell_latitude": [change.cell_lat for change in kept],
            "value": [change.delta_detected for change in kept],
        }
    ).with_columns(period_start=pl.lit(None, dtype=pl.Datetime("us", "UTC")))
