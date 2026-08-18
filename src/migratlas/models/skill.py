"""The hindcast harness: exactly the design `docs/methods/phase3a-skill.md` registered.

One skill number per unit, from one model class, against one baseline, era-split so the test
years are touched once. Everything here is deliberately boring — ridge in closed form,
standardisation from the training era only, the Murphy score, a year-shuffle null — because the
pre-registration bound to these words and a cleverer model would be a different experiment.

No scikit-learn: a ridge solve is five lines of numpy, and a dependency that large for five
lines would be the wheel-only stack's first regret.
"""

from dataclasses import dataclass
from typing import Final

import numpy as np

TRAIN_SHARE: Final = 0.7
MIN_TEST_YEARS: Final = 5
MIN_TOTAL_YEARS: Final = 15

# The lambda grid the training era may choose from, spanning "barely regularised" to "almost
# the climatology". Fixed here, per the registration: a grid chosen after seeing results would
# be model shopping with extra steps.
LAMBDAS: Final = (0.01, 0.1, 1.0, 10.0, 100.0)

PERMUTATIONS: Final = 1000
SIGNIFICANCE_PERCENTILE: Final = 95.0


@dataclass(frozen=True, slots=True)
class Split:
    """The era split for one unit: indices into the unit's year-ordered rows."""

    train: np.ndarray
    test: np.ndarray


@dataclass(frozen=True, slots=True)
class Skill:
    """One unit's verdict, with everything needed to publish it honestly."""

    score: float
    """Murphy score on the test era: 1 - MSE_model / MSE_climatology. Zero is 'knows nothing
    the training mean did not'; negative is worse than the mean."""

    null_threshold: float
    """The 95th percentile of the year-shuffle null. Skill below this is indistinguishable
    from a model fitted to shuffled drivers."""

    significant: bool
    train_years: int
    test_years: int
    ridge_lambda: float


def era_split(n_years: int) -> Split | None:
    """First 70% to train, the rest to test, or None where the registration excludes the unit.

    Operates on counts rather than year values: the caller sorts by year, and a unit with gap
    years is split by its observed rows — the registration's minimums are about information,
    which lives in rows, not calendar spans.
    """
    if n_years < MIN_TOTAL_YEARS:
        return None
    boundary = int(np.floor(n_years * TRAIN_SHARE))
    if n_years - boundary < MIN_TEST_YEARS:
        boundary = n_years - MIN_TEST_YEARS
    indices = np.arange(n_years)
    return Split(train=indices[:boundary], test=indices[boundary:])


def murphy_score(observed: np.ndarray, predicted: np.ndarray, climatology: float) -> float:
    """1 - MSE_model / MSE_climatology, with the degenerate case made explicit.

    A test era the training mean predicts perfectly (MSE_climatology = 0) offers no skill to
    measure; returning 0 says "nothing beyond the mean" rather than crashing or inventing an
    infinity.
    """
    baseline = float(np.mean((observed - climatology) ** 2))
    if baseline == 0.0:
        return 0.0
    return 1.0 - float(np.mean((observed - predicted) ** 2)) / baseline


def fit_ridge(x: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """Closed-form ridge on already-standardised x with an unpenalised intercept column."""
    design = np.column_stack([np.ones(len(y)), x])
    penalty = lam * np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    return np.linalg.solve(design.T @ design + penalty, design.T @ y)


def _loo_error(x: np.ndarray, y: np.ndarray, lam: float) -> float:
    """Leave-one-out MSE for ridge, from the hat matrix rather than n refits."""
    design = np.column_stack([np.ones(len(y)), x])
    penalty = lam * np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    hat = design @ np.linalg.solve(design.T @ design + penalty, design.T)
    residuals = y - hat @ y
    leverage = np.clip(np.diag(hat), 0.0, 1.0 - 1e-9)
    return float(np.mean((residuals / (1.0 - leverage)) ** 2))


def hindcast(x: np.ndarray, y: np.ndarray, *, seed: int) -> Skill | None:
    """The registered procedure for one unit: rows in year order, drivers by column.

    Standardisation statistics come from the training era alone — the test years leaking into
    a mean would be the model reading the answer sheet's margins — and the lambda is chosen by
    leave-one-out inside the training era, never against the test.
    """
    split = era_split(len(y))
    if split is None:
        return None
    x_train, y_train = x[split.train], y[split.train]
    x_test, y_test = x[split.test], y[split.test]

    centre = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale == 0.0] = 1.0
    x_train = (x_train - centre) / scale
    x_test = (x_test - centre) / scale

    errors = [_loo_error(x_train, y_train, lam) for lam in LAMBDAS]
    lam = LAMBDAS[int(np.argmin(errors))]
    weights = fit_ridge(x_train, y_train, lam)

    climatology = float(y_train.mean())
    predicted = np.column_stack([np.ones(len(y_test)), x_test]) @ weights
    score = murphy_score(y_test, predicted, climatology)

    rng = np.random.default_rng(seed)
    null_scores = np.empty(PERMUTATIONS)
    for index in range(PERMUTATIONS):
        shuffled = rng.permutation(len(y))
        x_null_train = x[shuffled[split.train]]
        x_null_test = x[shuffled[split.test]]
        null_centre = x_null_train.mean(axis=0)
        null_scale = x_null_train.std(axis=0)
        null_scale[null_scale == 0.0] = 1.0
        x_null_train = (x_null_train - null_centre) / null_scale
        x_null_test = (x_null_test - null_centre) / null_scale
        null_weights = fit_ridge(x_null_train, y_train, lam)
        null_predicted = np.column_stack([np.ones(len(y_test)), x_null_test]) @ null_weights
        null_scores[index] = murphy_score(y_test, null_predicted, climatology)

    threshold = float(np.percentile(null_scores, SIGNIFICANCE_PERCENTILE))
    return Skill(
        score=score,
        null_threshold=threshold,
        significant=score > threshold,
        train_years=len(split.train),
        test_years=len(split.test),
        ridge_lambda=lam,
    )
