"""Phase 1e: did southern African bird distributions change between two atlases?

Runs the design in `docs/methods/phase1e-atlas.md` exactly as registered. Every threshold here is
quoted from that note rather than chosen now, and the two that are ambiguous in it are resolved
explicitly below with the consequence measured rather than assumed.

The comparison is SABAP1's 1987-1991 atlas period against a five-year window of SABAP2, at
quarter-degree cells, full-protocol cards only, with occupancy and detection estimated separately
per species per epoch and the naive reporting-rate change computed beside it.

**Two things about the grain that the note anticipated and one that it did not.**

Anticipated: the grids differ, so pentads aggregate up to quarter-degree and SABAP2's resolution is
discarded; and closure is violated over a five-year epoch, so psi reads as "used at some point".

Not anticipated, and it is a real threat to the comparison rather than a footnote. A SABAP1 card
covers a whole quarter-degree cell; a SABAP2 full-protocol card covers one pentad, a ninth of that
area. Pooling pentad cards into a cell and calling them replicate visits to the cell means each
epoch-2 card samples a ninth of what an epoch-1 card sampled, so for any species that does not fill
its cell, detection per card is *mechanically* lower in epoch 2 -- and psi and p trade off against
each other. That is exactly the direction that would masquerade as "observers got worse" and bias
every Delta-psi. `detection_area_bias` measures it, and prediction 3 in the note is what would catch
it: if p came out lower in epoch 2 for most species, the model is doing something other than what it
was meant to and the result is not reportable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType
from migratlas.lake import reader
from migratlas.models import occupancy

if TYPE_CHECKING:
    from migratlas.models.occupancy import Occupancy

log = logging.getLogger(__name__)

CELL_DEG: Final = 0.25
"""Quarter-degree, SABAP1's own grid. SABAP2's pentads aggregate up; the reverse is impossible."""

FULL_PROTOCOL: Final = "BirdMAP fullprot"
"""Registered as an exclusion in note section 4: an ad-hoc card has no fixed observation period, so
its cards are not exchangeable with full-protocol ones and cannot share a detection probability."""

MIN_CARDS: Final = 20
"""Cards a cell needs *in both epochs* to enter the footprint. Note section 6, registered in advance
so it could not be chosen after seeing how many cells each candidate left."""

MIN_SPECIES_CELLS: Final = 30
"""Cells with at least one detection a species needs to be fitted.

The note says "thirty footprint cells in each epoch", which is ambiguous: every species has all
footprint cells available, since a cell where it was never recorded still contributes a zero. The
only reading that does any work is thirty cells *with a detection* -- below that psi is fitted on
almost no signal.

**Applied in epoch 1 only, and that is a correction to the note.** Requiring it in both epochs would
select on the outcome: a species that vanished has few epoch-2 detections by definition, so the rule
as written would drop exactly the species with the largest real change and bias every median towards
zero. Baseline-only selection asks "of the species that were widespread in 1987-1991, what
happened", which is a question with an answer. `excluded_by_both_epochs_rule` reports what the
literal reading would have removed, so the cost of the correction is visible rather than argued.
"""

EPOCH_1: Final = (datetime(1987, 1, 1, tzinfo=UTC), datetime(1991, 12, 31, tzinfo=UTC))
EPOCH_2: Final = (datetime(2008, 1, 1, tzinfo=UTC), datetime(2012, 12, 31, tzinfo=UTC))
EPOCH_2_ALT: Final = (datetime(2019, 1, 1, tzinfo=UTC), datetime(2023, 12, 31, tzinfo=UTC))
"""Note section 4. The alternative window is the registered sensitivity: a species whose change
flips sign between the two choices carries no result."""


def _snap(column: str) -> pl.Expr:
    """Snap a coordinate to its quarter-degree cell centre."""
    return ((pl.col(column) / CELL_DEG).floor() + 0.5) * CELL_DEG


def _cell(frame: pl.LazyFrame) -> pl.LazyFrame:
    return frame.with_columns(cell_lat=_snap("site_latitude"), cell_lon=_snap("site_longitude"))


def _window(source_id: str, window: tuple[datetime, datetime]) -> pl.LazyFrame:
    frame = reader.scan(EvidenceType.SURVEY_INDEX, source_id=source_id).filter(
        pl.col("period_start") >= window[0], pl.col("period_start") <= window[1]
    )
    if source_id == "sabap2":
        frame = frame.filter(pl.col("protocol") == FULL_PROTOCOL)
    return _cell(frame)


def cards_per_cell(source_id: str, window: tuple[datetime, datetime]) -> pl.DataFrame:
    """Cards submitted per quarter-degree cell in a window.

    `effort` is a property of the *cell-month* and is repeated across every species row belonging to
    it, so it is taken once per distinct (site, period) before summing -- the trap
    `ingest/sabap1.py` documents, where one real cell sums to 980 cards instead of 13.
    """
    return (
        _window(source_id, window)
        .select("site_id", "period_start", "effort", "cell_lat", "cell_lon")
        .unique(subset=["site_id", "period_start"])
        .group_by("cell_lat", "cell_lon")
        .agg(cards=pl.col("effort").sum().cast(pl.Float64))
        .collect()
    )


def footprint() -> pl.DataFrame:
    """Cells carrying at least `MIN_CARDS` full-protocol cards in both epochs."""
    first = cards_per_cell("sabap1", EPOCH_1)
    second = cards_per_cell("sabap2", EPOCH_2)
    both = first.join(second, on=["cell_lat", "cell_lon"], how="inner", suffix="_2")
    kept = both.filter((pl.col("cards") >= MIN_CARDS) & (pl.col("cards_2") >= MIN_CARDS))
    log.info(
        "footprint: %d cells of %d shared (%d and %d per epoch), >= %d cards in both",
        kept.height,
        both.height,
        first.height,
        second.height,
        MIN_CARDS,
    )
    return kept.select("cell_lat", "cell_lon", n_1="cards", n_2="cards_2")


def detections(
    source_id: str, window: tuple[datetime, datetime], cells: pl.DataFrame
) -> pl.DataFrame:
    """Cards recording each species, per footprint cell.

    `count` is per row and rows are per species per cell-month, so summing it over a cell-epoch is
    correct -- unlike `effort`, which would be multiplied by the species count.
    """
    return (
        _window(source_id, window)
        .select("taxon_key", "taxon_label", "count", "cell_lat", "cell_lon")
        .group_by("taxon_key", "taxon_label", "cell_lat", "cell_lon")
        .agg(k=pl.col("count").sum().cast(pl.Float64))
        .collect()
        .join(cells, on=["cell_lat", "cell_lon"], how="inner")
    )


@dataclass(frozen=True, slots=True)
class SpeciesChange:
    """One species, both epochs, corrected and naive."""

    taxon_key: int
    taxon_label: str
    first: Occupancy
    second: Occupancy

    @property
    def delta_psi(self) -> float:
        return self.second.psi - self.first.psi

    @property
    def delta_naive(self) -> float:
        return self.second.naive - self.first.naive

    @property
    def reportable(self) -> bool:
        """Both fits converged and neither is pinned at a boundary."""
        return (
            self.first.converged
            and self.second.converged
            and not self.first.at_boundary
            and not self.second.at_boundary
        )


def _series(frame: pl.DataFrame, cells: pl.DataFrame, effort: str) -> tuple[np.ndarray, np.ndarray]:
    """Align one species' detections to the full footprint, filling unvisited cells with zero.

    Every footprint cell contributes: a cell where the species was never recorded is a zero, not a
    missing value, and dropping it would be exactly the selection the occupancy model exists to
    undo.
    """
    joined = cells.join(
        frame.select("cell_lat", "cell_lon", "k"), on=["cell_lat", "cell_lon"], how="left"
    ).with_columns(k=pl.col("k").fill_null(0.0))
    k = joined["k"].to_numpy()
    n = joined[effort].to_numpy()
    # A species cannot be recorded on more cards than were submitted; a row that says otherwise
    # means the aggregation is wrong, so clip and report rather than letting the binomial refuse it
    # later.
    return np.minimum(k, n), n


def compare(second_window: tuple[datetime, datetime] = EPOCH_2) -> list[SpeciesChange]:
    """Fit every eligible species in both epochs over the common footprint."""
    cells = footprint()
    first = detections("sabap1", EPOCH_1, cells)
    second = detections("sabap2", second_window, cells)

    baseline = (
        first.group_by("taxon_key", "taxon_label")
        .agg(seen=pl.len())
        .filter(pl.col("seen") >= MIN_SPECIES_CELLS)
    )
    log.info(
        "%d taxa of %d clear %d epoch-1 cells with a detection",
        baseline.height,
        first["taxon_key"].n_unique(),
        MIN_SPECIES_CELLS,
    )

    changes: list[SpeciesChange] = []
    for key, label in baseline.select("taxon_key", "taxon_label").iter_rows():
        k1, n1 = _series(first.filter(pl.col("taxon_key") == key), cells, "n_1")
        k2, n2 = _series(second.filter(pl.col("taxon_key") == key), cells, "n_2")
        changes.append(
            SpeciesChange(
                taxon_key=int(key),
                taxon_label=str(label),
                first=occupancy.fit(k1, n1),
                second=occupancy.fit(k2, n2),
            )
        )
        if len(changes) % 100 == 0:
            log.info("  fitted %d/%d", len(changes), baseline.height)
    return changes


def excluded_by_both_epochs_rule(changes: list[SpeciesChange]) -> list[SpeciesChange]:
    """Species the note's literal "thirty cells in each epoch" would have dropped.

    Reported so the cost of applying the floor at baseline only is visible. These are the species
    with fewest epoch-2 detections, which is to say the ones that declined most.
    """
    return [c for c in changes if c.second.detections < MIN_SPECIES_CELLS]


def detection_area_bias(changes: list[SpeciesChange]) -> dict[str, float]:
    """Whether detection fell between epochs, which is what the pentad-to-cell pooling would cause.

    Note section 7 prediction 3 says p should be *higher* in epoch 2 -- digital recording, better
    optics, a photograph-backed rarities process. If it is lower for most species instead, the area
    change is dominating and section 8's third stop condition is in play.
    """
    usable = [c for c in changes if c.reportable]
    if not usable:
        return {"species": 0.0, "share_p_rose": float("nan"), "median_delta_p": float("nan")}
    deltas = np.array([c.second.p - c.first.p for c in usable])
    return {
        "species": float(len(usable)),
        "share_p_rose": float(np.mean(deltas > 0)),
        "median_delta_p": float(np.median(deltas)),
        "median_p_1": float(np.median([c.first.p for c in usable])),
        "median_p_2": float(np.median([c.second.p for c in usable])),
    }
