"""ADR 0016's rule, on panels where the answer is built in.

The rule is that on a small panel a verdict which does not survive the removal of any single unit
is not a verdict. That is a claim about an estimate, so it is testable with a refit callable and no
data: build a panel whose slope one unit carries, and the rule must refuse it.
"""

from collections.abc import Sequence

import numpy as np

from migratlas.models import influence


def _slope(points: Sequence[tuple[float, float]]) -> tuple[float, float]:
    """Ordinary least squares on (x, y) pairs, returning the slope and its 95% half-width."""
    x = np.array([px for px, _ in points])
    y = np.array([py for _, py in points])
    design = np.column_stack([np.ones_like(x), x])
    solution, *_ = np.linalg.lstsq(design, y, rcond=None)
    residuals = y - design @ solution
    dof = len(y) - 2
    sigma2 = float(np.sum(residuals**2) / dof)
    errors = np.sqrt(np.diag(sigma2 * np.linalg.pinv(design.T @ design)))
    return (float(solution[1]), float(1.96 * errors[1]))


def _measure(points: Sequence[tuple[float, float]]) -> influence.Influence:
    result = influence.leave_one_out(points, _slope, name=lambda point: f"x={point[0]:g}")
    assert result is not None
    return result


def test_a_slope_one_unit_carries_is_refused() -> None:
    """Fifteen points with no relationship, plus one extreme that manufactures one."""
    flat = [(float(index), 0.0) for index in range(15)]
    carried = _measure([*flat, (60.0, 40.0)])

    assert carried.clears_at_full, "the panel does not clear zero, so there is nothing to refuse"
    assert not carried.survives
    assert carried.carried_by_one
    assert not carried.publishable
    worst = carried.worst()
    assert worst is not None
    assert worst[0] == "x=60"


def test_a_slope_every_unit_agrees_about_is_published() -> None:
    points = [(float(index), 2.0 * index) for index in range(16)]
    result = _measure(points)

    assert result.clears_at_full
    assert result.survives
    assert not result.carried_by_one
    assert result.publishable


def test_a_null_has_no_leverage_to_lose() -> None:
    """A non-clearing estimate is unaffected by the rule: there is no verdict to overturn."""
    rng = np.random.default_rng(3)
    points = [(float(index), float(rng.normal(0.0, 1.0))) for index in range(16)]
    result = _measure(points)

    assert not result.clears_at_full
    assert not result.carried_by_one
    assert result.publishable


def test_the_rule_does_not_apply_above_the_panel_floor() -> None:
    """On a large panel one row cannot carry a slope, so the refits are not asked to decide."""
    flat = [(float(index), 0.0) for index in range(influence.SMALL_PANEL + 5)]
    carried = _measure([*flat, (200.0, 400.0)])

    assert not carried.small_panel
    assert carried.publishable, "the rule fired above its own floor"


def test_two_units_cannot_be_measured() -> None:
    assert influence.leave_one_out([(0.0, 0.0), (1.0, 1.0)], _slope, name=str) is None
