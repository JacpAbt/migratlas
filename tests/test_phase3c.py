"""The edge machinery, held to the registration's two core promises on synthetic series."""

import numpy as np

from migratlas.reports.phase3c import MIN_EDGE_YEARS, edge

YEARS = list(range(1980, 2020))


def _series(values: np.ndarray) -> dict[int, float]:
    return {year: float(v) for year, v in zip(YEARS, values, strict=True)}


def test_a_planted_edge_is_detected() -> None:
    rng = np.random.default_rng(3)
    driver = rng.normal(size=len(YEARS))
    response = 2.0 * driver + rng.normal(scale=0.3, size=len(YEARS))
    result = edge("planted", _series(driver), _series(response), {})
    assert result is not None
    assert result.detected
    assert result.ci_low > 0


def test_a_shared_trend_is_not_an_edge() -> None:
    """The registration's bluntest warning: two warming series must not couple by warming."""
    rng = np.random.default_rng(5)
    axis = np.arange(len(YEARS), dtype=float)
    driver = 0.5 * axis + rng.normal(size=len(YEARS))
    response = 0.8 * axis + rng.normal(size=len(YEARS))
    result = edge("trend-only", _series(driver), _series(response), {})
    assert result is not None
    assert not result.detected


def test_a_mode_driven_pair_is_absorbed_by_conditioning() -> None:
    """Phase 3a's prediction 5, as a unit test: the mode owns the edge, so conditioning kills it."""
    rng = np.random.default_rng(8)
    mode = rng.normal(size=len(YEARS))
    driver = mode + rng.normal(scale=0.2, size=len(YEARS))
    response = mode + rng.normal(scale=0.2, size=len(YEARS))
    bare = edge("bare", _series(driver), _series(response), {})
    conditioned = edge("conditioned", _series(driver), _series(response), {"m": _series(mode)})
    assert bare is not None
    assert bare.detected
    assert conditioned is not None
    assert abs(conditioned.coefficient) < abs(bare.coefficient)


def test_too_few_overlapping_years_returns_none() -> None:
    short = dict(list(_series(np.zeros(len(YEARS))).items())[: MIN_EDGE_YEARS - 1])
    assert edge("short", short, short, {}) is None
