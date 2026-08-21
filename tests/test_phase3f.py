"""Phase 3f's estimator and its two new covariates, on data where the answer is known.

The lake is never touched. What is tested is the machinery the registration bound to: the natural
spline's linear tails, the training-only threshold behind the favourable-night share, and the
pooled fit's ability to recover a signal that is genuinely shared across stations. The 1,000-draw
null is not exercised here -- it is slow by design and it is the same shuffle Phase 3a's harness
already carries.
"""

import numpy as np
import polars as pl

from migratlas.reports.phase3f import (
    ALL_COLUMNS,
    POST,
    SHARE,
    TEMP_COLUMN,
    WIND,
    Pooled,
    Unit,
    favourable_share,
    natural_spline,
    spline_knots,
    unit_key,
)


def _unit(name: str, x: dict[str, np.ndarray], y: np.ndarray, *, train: int) -> Unit:
    """One synthetic station-season, with unnamed covariates left at zero."""
    years = np.arange(2000, 2000 + y.size)
    columns = np.zeros((y.size, len(ALL_COLUMNS)))
    for column, values in x.items():
        columns[:, ALL_COLUMNS.index(column)] = values
    return Unit(
        station_id=name,
        season="autumn",
        years=years,
        y=y,
        x=columns,
        train=np.arange(train),
        test=np.arange(train, y.size),
    )


def test_the_spline_is_linear_beyond_its_boundary_knots() -> None:
    """The registered reason for a natural spline over a plain cubic one.

    The test era is later than the training era and may sit outside its range. A cubic basis
    curves away there; a natural one does not, and the difference is the difference between a
    prediction and nonsense. Linearity shows up as a vanishing second difference.
    """
    knots = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    beyond = np.array([10.0, 20.0, 30.0])
    below = np.array([-30.0, -20.0, -10.0])

    for outside in (beyond, below):
        basis = natural_spline(outside, knots)
        second = basis[0] - 2 * basis[1] + basis[2]
        assert np.allclose(second, 0.0, atol=1e-8), f"curved outside the knots: {second}"


def test_the_spline_does_curve_inside_its_knots() -> None:
    """The complement of the test above: a basis that were linear everywhere would be useless."""
    knots = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    inside = np.array([1.0, 2.0, 3.0])
    basis = natural_spline(inside, knots)
    second = basis[0] - 2 * basis[1] + basis[2]
    # The linear column is straight by construction; at least one spline column must not be.
    assert not np.allclose(second[1:], 0.0, atol=1e-8)


def test_a_column_with_too_few_distinct_values_gets_no_knots() -> None:
    """A two-valued column has no quartiles to knot at, so the caller leaves it linear."""
    assert spline_knots(np.array([0.0, 0.0, 1.0, 1.0, 1.0])) is None
    assert spline_knots(np.linspace(0.0, 1.0, 40)) is not None


def test_the_favourable_threshold_comes_from_the_training_era_alone() -> None:
    """A threshold that saw the test era would be reading the answer sheet's margins.

    Training nights sit at support 0, test nights at 10. Against a training-only median the test
    years are entirely favourable; against a median over all years they would be about half.
    """
    nightly = pl.DataFrame(
        {
            "station_id": ["KAAA"] * 8,
            "year": [2000, 2000, 2001, 2001, 2002, 2002, 2003, 2003],
            "date": [None] * 8,
            "support": [-1.0, 1.0, -1.0, 1.0, 10.0, 10.0, 10.0, 10.0],
        }
    )
    shares = favourable_share(nightly, train_years={2000, 2001})
    by_year = {row["year"]: row[SHARE] for row in shares.to_dicts()}

    assert by_year[2002] == 1.0
    assert by_year[2003] == 1.0
    # Half of the training nights beat the training median, which is what "near a half in
    # training" means and is the reference the test years depart from.
    assert by_year[2000] == 0.5


def test_a_station_with_no_training_nights_reports_nothing() -> None:
    nightly = pl.DataFrame(
        {
            "station_id": ["KAAA"],
            "year": [2005],
            "date": [None],
            "support": [1.0],
        }
    )
    assert favourable_share(nightly, train_years={2000}).is_empty()


def _shared_signal_units(stations: int = 12, years: int = 20) -> list[Unit]:
    """Stations that differ wildly in level and agree exactly in response.

    This is the case pooling exists for: each station has far too few rows to identify the
    response alone, and together they identify it precisely.
    """
    rng = np.random.default_rng(11)
    built = []
    for index in range(stations):
        temperature = rng.normal(size=years)
        wind = rng.normal(size=years)
        offset = 100.0 * index  # a level a shared slope vector must not have to explain
        built.append(
            _unit(
                f"K{index:03d}",
                {TEMP_COLUMN: temperature, WIND: wind},
                offset + 3.0 * temperature - 2.0 * wind,
                train=14,
            )
        )
    return built


def test_the_pooled_fit_recovers_a_shared_response_and_scores_it() -> None:
    pooled = Pooled(_shared_signal_units(), (TEMP_COLUMN, WIND), spline=False)
    design = pooled._design(pooled._raw)
    weights = pooled._solve(design, lam=1e-6)
    scores = pooled._scores(design, weights)

    # A noiseless shared signal must be predicted essentially perfectly out of era, at every
    # station, from coefficients no station could have estimated alone.
    assert scores.min() > 0.999


def test_the_within_station_centring_leaves_each_training_mean_at_zero() -> None:
    """The intercept lives in the station's own climatology, so the pooled design must have none.

    If this drifts, a shared slope vector starts trying to explain why Florida and Minnesota
    differ in level, which is the thing the centring exists to prevent.
    """
    pooled = Pooled(_shared_signal_units(), (TEMP_COLUMN, WIND), spline=False)
    centred = pooled._centre(pooled._raw)
    for rows, train in zip(pooled._rows, pooled._train, strict=True):
        assert np.allclose(centred[train].mean(axis=0), 0.0)
        assert rows.size >= train.size


def test_the_instrument_column_survives_the_spline_arm_unsplined() -> None:
    """A spline basis on a two-valued dummy would be rank-deficient, so it stays one column."""
    units = _shared_signal_units()
    for unit in units:
        unit.x[:, ALL_COLUMNS.index(POST)] = (unit.years >= 2014).astype(float)

    linear = Pooled(units, (TEMP_COLUMN, WIND, POST), spline=False)
    splined = Pooled(units, (TEMP_COLUMN, WIND, POST), spline=True)
    width_linear = linear._design(linear._raw).shape[1]
    width_splined = splined._design(splined._raw).shape[1]

    # Temperature and wind each expand; the dummy does not; and the registered interaction adds one.
    assert width_linear == 3
    assert width_splined > width_linear
    assert splined._knot_sets[2] is None


def test_the_null_does_not_depend_on_the_order_the_units_arrived_in() -> None:
    """The defect measuring twice caught, pinned so it cannot come back.

    The first run drew every unit's permutations from one generator in list order, and the unit
    order is not stable across calls -- so the null thresholds, and with them the significant-unit
    count, moved by three between reruns of the same seed. Observed skill was always identical,
    which is exactly why this needed a test rather than an eyeball: the number that moved was the
    bar, not the score.
    """
    units = _shared_signal_units(stations=6, years=18)
    forward = Pooled(units, (TEMP_COLUMN, WIND), spline=False)
    backward = Pooled(list(reversed(units)), (TEMP_COLUMN, WIND), spline=False)

    first, _ = forward.skills(seed=7)
    second, _ = backward.skills(seed=7)

    assert set(first) == set(second)
    for station in first:
        assert np.isclose(first[station].score, second[station].score)
        assert np.isclose(first[station].null_threshold, second[station].null_threshold)
        assert first[station].significant == second[station].significant


def test_the_unit_key_is_stable_across_processes() -> None:
    """`hash` is salted per process for strings, which would reintroduce the irreproducibility."""
    assert unit_key("KABR") == unit_key("KABR")
    assert unit_key("KABR") != unit_key("KABX")
    # A literal, so a change to the keying function is visible in the diff rather than silent.
    assert unit_key("KABR") == 1529084552
