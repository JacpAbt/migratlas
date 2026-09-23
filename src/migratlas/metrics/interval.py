"""One mean-and-interval estimator, because six reports had each copied it.

Changing this moves every published number computed through it. `phase2a_attrici` keeps its own on
purpose: at a single unit it returns a null interval where this returns zero, and the two
conventions are a real disagreement rather than a duplicate.
"""

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence


def mean_ci(values: Sequence[float] | np.ndarray) -> tuple[float, float]:
    """Mean and the half-width of a 95% normal-approximation interval; `(nan, nan)` when empty."""
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return (float("nan"), float("nan"))
    ci = 1.96 * float(array.std(ddof=1)) / np.sqrt(array.size) if array.size > 1 else 0.0
    return (float(array.mean()), ci)
