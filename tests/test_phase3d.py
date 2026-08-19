"""The rehearsal's arithmetic, tested without the lake, the archive, or the targets."""

import numpy as np

from migratlas.reports.phase3d import _fit_target


def test_the_fit_never_sees_the_target() -> None:
    """The prediction changes with the forecast row; the model does not."""
    rng = np.random.default_rng(4)
    x_train = rng.normal(size=(15, 3))
    y_train = 250.0 + 2.0 * x_train[:, 0] + rng.normal(scale=0.1, size=15)
    fit = _fit_target(x_train, y_train, year=2020, observed=252.0)
    warm = fit.predict(np.array([1.0, 0.0, 0.0]))
    cold = fit.predict(np.array([-1.0, 0.0, 0.0]))
    assert warm > cold
    assert abs(fit.climatology - float(y_train.mean())) < 1e-9


def test_a_perfect_forecast_beats_climatology_and_a_wrong_one_does_not() -> None:
    """The grading logic in miniature: skill is relative to the training mean."""
    rng = np.random.default_rng(9)
    x_train = rng.normal(size=(20, 3))
    y_train = 250.0 + 3.0 * x_train[:, 0] + rng.normal(scale=0.2, size=20)
    fit = _fit_target(x_train, y_train, year=2020, observed=253.0)
    # The "true" driver row for an observed 253 under the planted slope is x0 = 1.
    good = (fit.observed - fit.predict(np.array([1.0, 0.0, 0.0]))) ** 2
    wrong = (fit.observed - fit.predict(np.array([-1.0, 0.0, 0.0]))) ** 2
    baseline = (fit.observed - fit.climatology) ** 2
    assert good < baseline < wrong


def test_a_constant_training_column_does_not_crash() -> None:
    rng = np.random.default_rng(5)
    x_train = np.column_stack([np.ones(12), rng.normal(size=12), rng.normal(size=12)])
    fit = _fit_target(x_train, rng.normal(size=12), year=2020, observed=0.0)
    assert np.isfinite(fit.predict(np.array([1.0, 0.0, 0.0])))
