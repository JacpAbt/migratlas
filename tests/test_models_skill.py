"""The hindcast harness, held to the words of phase3a-skill.md."""

import numpy as np

from migratlas.models.skill import (
    MIN_TOTAL_YEARS,
    era_split,
    fit_ridge,
    hindcast,
    murphy_score,
)


def test_units_below_the_registered_floor_are_excluded() -> None:
    assert era_split(MIN_TOTAL_YEARS - 1) is None
    split = era_split(MIN_TOTAL_YEARS)
    assert split is not None
    assert len(split.test) == 5


def test_the_split_is_seventy_thirty_with_the_test_minimum_enforced() -> None:
    split = era_split(30)
    assert split is not None
    assert len(split.train) == 21
    assert len(split.test) == 9
    tight = era_split(16)
    assert tight is not None
    # floor(16 * 0.7) = 11 would leave 5 test years, exactly the minimum.
    assert len(tight.test) == 5


def test_the_eras_do_not_overlap_and_the_test_comes_last() -> None:
    split = era_split(20)
    assert split is not None
    assert set(split.train.tolist()).isdisjoint(split.test.tolist())
    assert split.train.max() < split.test.min()


def test_murphy_score_brackets() -> None:
    observed = np.array([1.0, 2.0, 3.0])
    assert murphy_score(observed, observed, climatology=2.0) == 1.0
    assert murphy_score(observed, np.full(3, 2.0), climatology=2.0) == 0.0
    flat = np.full(3, 5.0)
    assert murphy_score(flat, flat + 1, climatology=5.0) == 0.0


def test_ridge_recovers_a_clean_linear_signal() -> None:
    rng = np.random.default_rng(7)
    x = rng.normal(size=(200, 2))
    weights = fit_ridge(x, 3.0 + 2.0 * x[:, 0] - 1.0 * x[:, 1], 0.01)
    assert np.allclose(weights, [3.0, 2.0, -1.0], atol=0.01)


def test_a_real_signal_is_significant_and_noise_is_not() -> None:
    rng = np.random.default_rng(11)
    years = 40
    driver = rng.normal(size=(years, 1))
    signal = 10.0 + 3.0 * driver[:, 0] + rng.normal(scale=0.5, size=years)
    forced = hindcast(driver, signal, seed=1)
    assert forced is not None
    assert forced.score > 0.5
    assert forced.significant

    noise = rng.normal(size=years)
    unforced = hindcast(driver, noise, seed=1)
    assert unforced is not None
    assert not unforced.significant


def test_the_same_seed_reproduces_the_same_verdict() -> None:
    rng = np.random.default_rng(3)
    x = rng.normal(size=(25, 2))
    y = rng.normal(size=25)
    assert hindcast(x, y, seed=42) == hindcast(x, y, seed=42)


def test_a_constant_driver_does_not_crash_the_standardisation() -> None:
    rng = np.random.default_rng(5)
    x = np.column_stack([np.ones(20), rng.normal(size=20)])
    y = rng.normal(size=20)
    result = hindcast(x, y, seed=9)
    assert result is not None
