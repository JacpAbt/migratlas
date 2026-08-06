"""The per-cell atlas surface, and the instruments that decide whether it may be drawn.

The surface itself needs a lake and is not built here. What is tested is every piece of arithmetic
the stop conditions rest on, because a stop condition computed wrongly is worse than none: it
licenses the layer while appearing to police it.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.models import occupancy
from migratlas.reports import phase1e, phase1f
from migratlas.reports.phase1f import CellChange


def _cell(**overrides: object) -> CellChange:
    fields: dict[str, object] = {
        "cell_lat": -25.125,
        "cell_lon": 28.125,
        "first": 100.0,
        "second": 100.0,
        "detected_first": 90.0,
        "detected_second": 90.0,
        "movers": phase1f.MIN_MOVERS,
        "cards_first": 40.0,
        "cards_second": 40.0,
    }
    fields.update(overrides)
    return CellChange(**fields)  # type: ignore[arg-type]


# --- Moran's I ----------------------------------------------------------------
def _grid(side: int) -> list[CellChange]:
    step = phase1e.CELL_DEG
    return [
        _cell(cell_lat=-25.0 + row * step, cell_lon=28.0 + column * step)
        for row in range(side)
        for column in range(side)
    ]


def test_a_smooth_gradient_is_positively_autocorrelated() -> None:
    """The behaviour prediction 3 is asking about: neighbours resembling each other."""
    cells = _grid(8)
    weights = phase1f.weights(cells)
    gradient = np.array([cell.cell_lat for cell in cells])
    assert phase1f.morans_i(gradient, weights) > 0.5


def test_noise_is_not() -> None:
    """A surface of noise must not pass the structure test, or the map is decoration."""
    cells = _grid(8)
    weights = phase1f.weights(cells)
    rng = np.random.default_rng(0)
    values = rng.normal(size=len(cells))
    assert abs(phase1f.morans_i(values, weights)) < 0.25


def test_a_checkerboard_reads_as_no_structure_under_queen_contiguity() -> None:
    """A real limitation, found by asserting the wrong thing first.

    This was written expecting strong *negative* autocorrelation, which is what rook contiguity
    would give. Under queen the four diagonal neighbours of a checkerboard cell carry its own value
    and the four orthogonal ones carry the opposite, so they cancel and the statistic reads ~0.

    Queen is kept anyway, and this test records the cost. The footprint is a grid with holes in it,
    and under rook a cell whose only surviving neighbour is diagonal would be isolated -- which
    matters more here than seeing a one-cell alternation, a pattern no ecological process would make
    at 27 km. What it means for the layer: prediction 3 cannot detect structure at exactly this
    frequency, so a surface that passed it is not thereby proved smooth.
    """
    cells = _grid(8)
    weights = phase1f.weights(cells)
    board = np.array(
        [
            1.0
            if (round(cell.cell_lat / phase1e.CELL_DEG) + round(cell.cell_lon / phase1e.CELL_DEG))
            % 2
            else -1.0
            for cell in cells
        ]
    )
    assert abs(phase1f.morans_i(board, weights)) < 0.2


def test_a_constant_surface_has_no_structure_rather_than_a_division_by_zero() -> None:
    cells = _grid(4)
    weights = phase1f.weights(cells)
    assert phase1f.morans_i(np.ones(len(cells)), weights) == 0.0


def test_neighbours_stop_at_the_holes() -> None:
    """The reason for contiguity over a distance kernel.

    A cell three steps away is not a neighbour. If it were, the weights would reach across the gaps
    in the footprint -- which are the places nobody atlassed twice -- and smooth over the one thing
    the note refuses to guess.
    """
    step = phase1e.CELL_DEG
    cells = [
        _cell(cell_lat=-25.0, cell_lon=28.0),
        _cell(cell_lat=-25.0, cell_lon=28.0 + step),
        _cell(cell_lat=-25.0, cell_lon=28.0 + step * 3),
    ]
    weights = phase1f.weights(cells)
    assert weights[0][1] > 0
    assert weights[0][2] == 0
    # Two steps of empty grid is a hole, and the cell across it is nobody's neighbour rather than
    # somebody's distant one. Nothing is carried over the gap in either direction.
    assert weights[2].sum() == 0.0
    assert weights[:, 2].sum() == 0.0


def test_an_isolated_cell_contributes_nothing_rather_than_a_nan() -> None:
    """A footprint cell with no neighbour at all. Row standardisation divides by its zero total."""
    weights = phase1f.weights([_cell()])
    assert weights.shape == (1, 1)
    assert not np.isnan(weights).any()


# --- The presence term --------------------------------------------------------
def test_a_recorded_taxon_is_present_whatever_the_model_thinks() -> None:
    """A detection is not a probability. It happened."""
    present = phase1f._present(
        counts=np.array([[3.0, 0.0]]),
        cards=np.array([40.0, 40.0]),
        psi=np.array([0.01]),
        detection=np.array([0.9]),
    )
    assert present[0][0] == 1.0
    assert present[0][1] < 0.01


def test_silence_over_many_cards_means_absent_and_over_few_means_unknown() -> None:
    """The whole reason the surface is not a count of what was seen."""
    present = phase1f._present(
        counts=np.zeros((1, 2)),
        cards=np.array([2.0, 200.0]),
        psi=np.array([0.6]),
        detection=np.array([0.2]),
    )
    assert present[0][0] > present[0][1]
    assert present[0][1] < 0.01


def test_the_presence_term_is_the_note_s_own_formula() -> None:
    """Pinned to `occupied_given_silence` so the map and section 5 cannot drift apart."""
    cards = np.array([1.0, 7.0, 60.0])
    expected = occupancy.occupied_given_silence(0.4, 0.3, cards)
    present = phase1f._present(
        counts=np.zeros((1, 3)), cards=cards, psi=np.array([0.4]), detection=np.array([0.3])
    )
    assert present[0] == pytest.approx(expected)


def test_a_count_above_the_card_total_is_not_read_as_a_detection() -> None:
    """`phase1e._series` clips these; the matrix here is built separately and must agree."""
    present = phase1f._present(
        counts=np.array([[0.0]]),
        cards=np.array([0.0]),
        psi=np.array([0.5]),
        detection=np.array([0.5]),
    )
    assert present[0][0] == pytest.approx(0.5)


# --- The dense matrix ---------------------------------------------------------
def test_the_matrix_puts_each_taxon_and_cell_where_the_footprint_says() -> None:
    """Row and column order carry the whole result, and nothing else checks them."""
    cells = pl.DataFrame(
        {"cell_lat": [-25.0, -25.25], "cell_lon": [28.0, 28.0], "n_1": [40.0, 40.0]}
    )
    detections = pl.DataFrame(
        {
            "taxon_key": [111, 222, 111],
            "cell_lat": [-25.0, -25.25, -25.25],
            "cell_lon": [28.0, 28.0, 28.0],
            "k": [5.0, 7.0, 2.0],
        }
    )
    matrix = phase1f._counts(detections, cells, [111, 222])
    assert matrix.tolist() == [[5.0, 2.0], [0.0, 7.0]]


def test_a_taxon_outside_the_analysed_set_is_left_out_rather_than_misfiled() -> None:
    """A key not in `keys` must vanish, not land on whichever row happens to be there."""
    cells = pl.DataFrame({"cell_lat": [-25.0], "cell_lon": [28.0], "n_1": [40.0]})
    detections = pl.DataFrame(
        {"taxon_key": [999], "cell_lat": [-25.0], "cell_lon": [28.0], "k": [9.0]}
    )
    assert phase1f._counts(detections, cells, [111]).tolist() == [[0.0]]


# --- The stop conditions ------------------------------------------------------
def test_a_surface_that_tracks_the_cards_is_not_publishable() -> None:
    """Note section 5, the condition the layer lives or dies by.

    Built so the change *is* the change in effort. Whatever else passes, this must refuse it.
    """
    cells = [
        _cell(
            cell_lat=-25.0 + index * phase1e.CELL_DEG,
            cards_first=20.0,
            cards_second=20.0 + index,
            first=100.0,
            second=100.0 + index,
            detected_first=100.0,
            detected_second=100.0 + index,
        )
        for index in range(40)
    ]
    verdict = phase1f.grade(cells, taxa=512)
    assert verdict.effort_rho > phase1f.MAX_EFFORT_RHO
    assert not verdict.effort_ok
    assert not verdict.publishable


def test_a_cell_moved_by_too_few_taxa_is_dropped() -> None:
    below = _cell(movers=phase1f.MIN_MOVERS - 1)
    assert not below.steady
    assert _cell(movers=phase1f.MIN_MOVERS).steady


def test_too_many_dropped_cells_takes_the_whole_layer() -> None:
    """Note section 5: past a tenth, the surface is noise wherever it is not dropped too."""
    cells = [_cell(movers=0) for _ in range(20)] + [_cell() for _ in range(80)]
    verdict = phase1f.grade(cells, taxa=512)
    assert verdict.drop_share == pytest.approx(0.2)
    assert not verdict.publishable


def test_the_verdict_reports_a_p_value_a_permutation_test_can_license() -> None:
    """Never exactly zero: the observed value counts as one of its own draws."""
    cells = _grid(6)
    verdict = phase1f.grade(cells, taxa=512)
    assert verdict.morans_p >= 1 / (phase1f.PERMUTATIONS + 1)


# --- The published layer ------------------------------------------------------
def _publishable(side: int = 6) -> list[CellChange]:
    """A surface that clears every condition `drawable` enforces.

    Structured, because a flat one fails prediction 3 and is refused -- which is the check working,
    and which makes a constant fixture useless for testing anything downstream of it. Corrected and
    uncorrected are deliberately different so a test can tell which reached the frame.
    """
    step = phase1e.CELL_DEG
    return [
        _cell(
            cell_lat=-25.0 + row * step,
            cell_lon=28.0 + column * step,
            first=100.0,
            second=100.0 + (-10.0 + row * 2.0),
            detected_first=100.0,
            detected_second=100.0 + (-5.0 + row * 1.0),
        )
        for row in range(side)
        for column in range(side)
    ]


def test_the_drawable_frame_carries_the_uncorrected_count() -> None:
    """Note section 5, applied. The corrected surface is computed, graded and withheld.

    The corrected value is the one this project would normally prefer, so a build that quietly
    published it would look exactly like a build that obeyed the note.
    """
    cells = _publishable()
    frame = phase1f.drawable(cells, phase1f.grade(cells, taxa=512))
    assert frame.columns == ["cell_longitude", "cell_latitude", "value", "period_start"]

    drawn = frame["value"].to_list()
    assert drawn == [cell.delta_detected for cell in cells]
    # And emphatically not the corrected one, which is the value this project would normally
    # prefer and the reason a silent swap would be invisible.
    assert drawn != [cell.delta for cell in cells]


def test_a_surface_that_failed_its_conditions_raises_rather_than_drawing_nothing() -> None:
    """An empty layer and a refused one look identical on a globe. Only one is a bug."""
    cells = [
        _cell(
            cell_lat=-25.0 + index * phase1e.CELL_DEG,
            cards_first=20.0,
            cards_second=20.0 + index,
            first=100.0,
            second=100.0 + index,
            detected_first=100.0,
            detected_second=100.0 + index,
        )
        for index in range(40)
    ]
    verdict = phase1f.grade(cells, taxa=512)
    with pytest.raises(ValueError, match="not publishable"):
        phase1f.drawable(cells, verdict)


def test_a_dropped_cell_is_not_in_the_layer() -> None:
    """The mover floor has to reach the frame, not only the verdict."""
    cells = _publishable()
    first = cells[0]
    cells[0] = _cell(
        cell_lat=first.cell_lat,
        cell_lon=first.cell_lon,
        first=first.first,
        second=first.second,
        detected_first=first.detected_first,
        detected_second=first.detected_second,
        movers=0,
    )
    frame = phase1f.drawable(cells, phase1f.grade(cells, taxa=512))
    assert frame.height == len(cells) - 1
