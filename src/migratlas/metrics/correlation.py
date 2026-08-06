"""Rank correlation with the degenerate cases answered rather than raised.

Extracted after hitting the same wall twice: `scipy.stats.spearmanr` warns on a constant input, this
project turns warnings into errors, and both `phase1g` and `phase1h` legitimately meet constant
columns -- a flat surface, a synthetic fixture, a subset where the covariate does not vary.

A crash there would be a report failing on its way to concluding "no relationship", which is the
answer a constant input actually has.
"""

import numpy as np
from scipy import stats

# Two points is the fewest that can be ranked against each other at all.
MIN_POINTS = 2


def spearman(first: np.ndarray, second: np.ndarray) -> tuple[float, float]:
    """Spearman's rho and its p-value; ``(0.0, 1.0)`` when either side cannot be ranked.

    A constant array has no ranks to correlate. Zero is the honest answer -- no monotone
    relationship is detectable -- and a p-value of one refuses to call it significant.
    """
    if first.size < MIN_POINTS or np.all(first == first[0]) or np.all(second == second[0]):
        return 0.0, 1.0
    result = stats.spearmanr(first, second)
    return float(result.statistic), float(result.pvalue)
