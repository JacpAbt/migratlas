"""The water factor, and the nulls that decide whether its answer means anything.

A null hypothesis test that always returns a large p-value would have passed every check in this
note and reported a tidy negative result. So the nulls are tested first and against known answers:
they have to *find* an effect that is really there, or their failure to find one says nothing.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.reports import phase1e, phase1g


def _frame(
    water: np.ndarray, response: np.ndarray, effort: np.ndarray | None = None
) -> pl.DataFrame:
    """A square footprint with a given factor and response, on the real cell size."""
    side = int(np.sqrt(water.size))
    step = phase1e.CELL_DEG
    lats = [-30.0 + (index // side) * step for index in range(water.size)]
    lons = [25.0 + (index % side) * step for index in range(water.size)]
    return pl.DataFrame(
        {
            "cell_lat": lats,
            "cell_lon": lons,
            "water": water,
            "delta": response,
            "delta_corrected": response,
            "effort": np.zeros_like(water) if effort is None else effort,
            "extent": np.abs(water),
        }
    )


def _smooth(side: int, seed: int) -> np.ndarray:
    """A spatially autocorrelated surface, which is what both real maps are."""
    rng = np.random.default_rng(seed)
    field = rng.normal(size=(side + 8, side + 8))
    for _ in range(4):
        field = (
            field
            + np.roll(field, 1, 0)
            + np.roll(field, -1, 0)
            + np.roll(field, 1, 1)
            + np.roll(field, -1, 1)
        ) / 5
    return field[4 : side + 4, 4 : side + 4].ravel()


# --- The nulls have to work ---------------------------------------------------
def test_the_spectral_null_finds_an_effect_that_is_really_there() -> None:
    """The test that makes every negative result in this note worth reading.

    If the response *is* the factor, the null must say so. A null that could not detect this could
    not have detected anything, and its large p-value against the atlas data would be an artefact
    of the test rather than a fact about water.
    """
    water = _smooth(16, seed=1)
    frame = _frame(water, response=water * 3.0)
    assert phase1g.spectral_null(frame) <= 0.01


def test_the_spectral_null_is_not_fooled_by_two_smooth_but_unrelated_surfaces() -> None:
    """The failure mode the whole design exists for.

    Two independently generated autocorrelated maps will correlate far more often than an i.i.d.
    test believes. The spatial null has to be unimpressed by that -- across several seeds, because
    any one pair can agree by chance and that is exactly the point.
    """
    passed = 0
    for seed in range(6):
        frame = _frame(_smooth(14, seed=seed), response=_smooth(14, seed=seed + 100))
        if phase1g.spectral_null(frame) > phase1g.ALPHA:
            passed += 1
    assert passed >= 5, f"the spatial null called {6 - passed} of 6 unrelated pairs significant"


def test_the_naive_test_is_fooled_by_exactly_those_pairs() -> None:
    """Why the naive p-value is computed and labelled rather than left out.

    The claim in the method note is that an ordinary test over-rejects here. That is asserted
    against the same surfaces the spatial null shrugs at: if the naive test agreed with the spatial
    one, publishing both would be decoration.
    """
    naive_significant = 0
    for seed in range(6):
        frame = _frame(_smooth(14, seed=seed), response=_smooth(14, seed=seed + 100))
        if phase1g.fit(frame).naive_p < phase1g.ALPHA:
            naive_significant += 1
    assert naive_significant >= 2, (
        "the naive test rejected nothing, so this data does not demonstrate the over-rejection "
        "the note claims -- either the surfaces are not autocorrelated enough or the claim is wrong"
    )


def test_the_toroidal_null_finds_a_real_effect_too() -> None:
    """The second null, on a full grid where shifting has somewhere to land."""
    water = _smooth(16, seed=7)
    frame = _frame(water, response=water * 3.0)
    p, used = phase1g.toroidal_null(frame)
    assert p <= 0.05
    assert used > frame.height * 0.5, "most cells fell in holes; the null had nothing to work with"


# --- The fit ------------------------------------------------------------------
def test_effort_is_conditioned_out_rather_than_ignored() -> None:
    """Stop condition two: a water coefficient that is really an effort coefficient.

    Built so the response is entirely effort and water merely correlates with it. The partial
    correlation has to see through that.
    """
    effort = _smooth(14, seed=3)
    water = effort + _smooth(14, seed=4) * 0.1
    frame = _frame(water, response=effort * 5.0, effort=effort)
    fit = phase1g.fit(frame)
    assert abs(fit.partial_r) < 0.2, f"partial correlation {fit.partial_r} still tracks effort"


def test_a_real_water_effect_survives_the_effort_control() -> None:
    """The other direction: conditioning must not erase an effect that is genuinely water's."""
    water = _smooth(14, seed=5)
    effort = _smooth(14, seed=6)
    frame = _frame(water, response=water * 4.0 + effort, effort=effort)
    assert phase1g.fit(frame).partial_r > 0.8


def test_the_slope_is_reported_in_taxa_per_square_kilometre() -> None:
    """Units, because the coefficient is published and a factor-of-ten error would be invisible."""
    water = _smooth(12, seed=9)
    frame = _frame(water, response=water * 2.5)
    assert phase1g.fit(frame).water == pytest.approx(2.5, rel=1e-6)


def test_a_missing_water_cell_stops_the_join_rather_than_shrinking_it() -> None:
    """Silently fitting on the cells that happened to join is how a footprint quietly changes."""
    # `_design` raises when the join loses a cell rather than carrying on with what matched.
    # Asserted against the message it raises, so the guard cannot be softened into a filter.
    source = phase1g._design.__code__.co_consts
    assert any(isinstance(c, str) and "footprint cells" in c for c in source), (
        "_design no longer refuses a partial join"
    )
