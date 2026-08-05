"""Single-season occupancy with binomial detection, per `docs/methods/phase1e-atlas.md` §5.

The model that separates "the birds changed" from "the observers changed", which is the whole
reason the atlas comparison is worth doing rather than differencing two reporting rates.

An atlas row says a species was recorded on *k* of the *n* cards submitted for a cell in a period.
A cell is occupied or it is not; if it is, each card detects the species independently with
probability *p*. So a cell with `k > 0` is certainly occupied, and a cell with `k = 0` is either
unoccupied or occupied and missed *n* times running:

    L(psi, p) = prod_c [ psi * Binom(k_c ; n_c, p)  +  (1 - psi) * 1{k_c = 0} ]

That second branch is the entire content of the model. Without it `k / n` is the estimate, and it
falls when a species declines *and* when observers get worse -- which across thirty years of atlas
history is the confound that sinks the comparison.

**Nothing here knows what a bird is.** It takes two integer arrays and returns two probabilities,
which is what lets `tests/test_occupancy.py` hand it simulated data with known parameters and check
they come back. That test is the gate: the model does not touch SABAP until it can recover what it
was given.

Fitted on the logit scale so the optimiser is unconstrained and the boundaries are reachable only in
the limit, and reported with a profile-likelihood interval rather than a Wald one -- psi is bounded
and its likelihood is skewed near 1, where a symmetric interval would run past the boundary and
claim probabilities above one.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Final

import numpy as np
from scipy import optimize
from scipy.special import expit, gammaln, logit

log = logging.getLogger(__name__)

_HALF_CHI2_1_95: Final = 1.920729410347062
"""Half the 95th percentile of chi-square on one degree of freedom.

The drop in log-likelihood that bounds a profile interval. Written out rather than called from
`scipy.stats` at fit time, because it is a constant and this runs once per species per epoch.
"""

BOUNDARY: Final = 0.01
"""How close to 0 or 1 an estimate has to be before it is called a boundary rather than a value.

`phase1e-atlas.md` §8 makes this a stop condition: if detection sits at a boundary for more than a
third of species the model is not identified on the data and only the naive comparison is reported.
"""

_FLOOR: Final = 1e-12
"""Keeps a log finite at the boundary. Small enough not to move any estimate that is not already
pinned there, large enough that `log` never sees a true zero."""


@dataclass(frozen=True, slots=True)
class Occupancy:
    """One species in one epoch."""

    psi: float
    """Probability a footprint cell is occupied."""

    p: float
    """Probability one card of an occupied cell records the species."""

    psi_low: float
    psi_high: float
    """Profile-likelihood interval on `psi` at 95%."""

    cells: int
    """Cells the fit used."""

    detections: int
    """Cells with at least one detection. `psi` can never be below this share."""

    loglik: float
    converged: bool

    @property
    def naive(self) -> float:
        """The share of cells where the species was seen at all.

        What an uncorrected analysis would report as occupancy, and a lower bound on `psi`: every
        cell with a detection is occupied, and some of the silent ones are too.
        """
        return self.detections / self.cells if self.cells else float("nan")

    @property
    def at_boundary(self) -> bool:
        """Whether either parameter is pinned, which makes the estimate a statement about the data
        rather than about the species."""
        return (
            self.p < BOUNDARY
            or self.p > 1 - BOUNDARY
            or self.psi > 1 - BOUNDARY
            or self.psi < BOUNDARY
        )


def _binom_logpmf(k: np.ndarray, n: np.ndarray, p: float) -> np.ndarray:
    """log C(n, k) + k log p + (n - k) log(1 - p), without SciPy's per-call overhead.

    `gammaln` rather than `math.comb`: the coefficient is constant in `p`, but the optimiser calls
    this a few hundred times and the array form is what makes the whole fit cheap.
    """
    coefficient = gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)
    log_p = math.log(max(p, _FLOOR))
    log_q = math.log(max(1 - p, _FLOOR))
    return np.asarray(coefficient + k * log_p + (n - k) * log_q, dtype=np.float64)


def loglik(k: np.ndarray, n: np.ndarray, psi: float, p: float) -> float:
    """Log-likelihood of the whole cell set at one (psi, p).

    Split by whether the cell ever detected the species, because the two branches are different
    expressions rather than one expression with a zero in it: a detected cell contributes only the
    occupied term, and a silent cell contributes the mixture.
    """
    psi = min(max(psi, _FLOOR), 1 - _FLOOR)
    seen = k > 0
    total = 0.0

    if seen.any():
        total += float(np.sum(math.log(psi) + _binom_logpmf(k[seen], n[seen], p)))
    if (~seen).any():
        # log( psi (1-p)^n + (1-psi) ), by log-sum-exp so a long run of cards cannot underflow.
        occupied_and_missed = math.log(psi) + n[~seen] * math.log(max(1 - p, _FLOOR))
        total += float(np.sum(np.logaddexp(occupied_and_missed, math.log(1 - psi))))
    return total


def _fit_free(k: np.ndarray, n: np.ndarray) -> tuple[float, float, float, bool]:
    """Maximise over both parameters. Returns (psi, p, loglik, converged)."""

    def negative(theta: np.ndarray) -> float:
        psi, p = expit(theta)
        value = loglik(k, n, float(psi), float(p))
        # The optimiser will walk into the boundary; a finite penalty steers it back without the
        # discontinuity that `inf` would introduce into the simplex.
        return -value if math.isfinite(value) else 1e18

    # Started from the naive estimates rather than from 0.5: the naive occupancy is a lower bound on
    # psi and the observed detection share is close to p whenever p is not tiny, so this begins in
    # the right region and Nelder-Mead does not have to find it.
    detections = int((k > 0).sum())
    psi0 = min(max(detections / len(k), 0.05), 0.95)
    effort = float(n[k > 0].sum()) if detections else 0.0
    p0 = min(max(float(k.sum()) / effort, 0.05), 0.95) if effort > 0 else 0.5

    result = optimize.minimize(
        negative,
        x0=np.array([logit(psi0), logit(p0)]),
        method="Nelder-Mead",
        options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 2000},
    )
    psi, p = (float(v) for v in expit(result.x))
    return psi, p, -float(result.fun), bool(result.success)


def _profile(k: np.ndarray, n: np.ndarray, psi: float, peak: float) -> tuple[float, float]:
    """Profile-likelihood interval on psi: where the likelihood, maximised over p, drops by 1.92.

    Bisection rather than a root finder with a derivative, because the profile is flat wherever psi
    is weakly identified and a Newton step there lands anywhere at all.
    """

    def profiled(value: float) -> float:
        """Best log-likelihood attainable with psi held at `value`."""
        if value <= 0 or value >= 1:
            return -math.inf

        def negative(theta: float) -> float:
            return -loglik(k, n, value, float(expit(theta)))

        best = optimize.minimize_scalar(negative, bounds=(-12, 12), method="bounded")
        return -float(best.fun)

    target = peak - _HALF_CHI2_1_95

    def edge(low: float, high: float) -> float:
        """Bisect for the psi where the profile crosses `target`, between a point inside the
        interval and one outside it."""
        for _ in range(60):
            middle = (low + high) / 2
            if profiled(middle) > target:
                low = middle
            else:
                high = middle
        return (low + high) / 2

    # Outward from the estimate. If the profile never drops before the boundary the interval runs to
    # it, which is the honest answer for a species detected in every cell.
    below = edge(psi, _FLOOR) if profiled(_FLOOR) < target else 0.0
    above = edge(psi, 1 - _FLOOR) if profiled(1 - _FLOOR) < target else 1.0
    return below, above


def fit(k: np.ndarray, n: np.ndarray) -> Occupancy:
    """Fit one species in one epoch.

    Args:
        k: cards recording the species, per cell.
        n: cards submitted, per cell. Must be positive and at least `k`.

    Raises:
        ValueError: if the arrays disagree, or a cell has no cards, or `k` exceeds `n` -- each of
            which would make the binomial meaningless rather than merely unlikely.
    """
    k = np.asarray(k, dtype=np.float64)
    n = np.asarray(n, dtype=np.float64)
    if k.shape != n.shape:
        msg = f"k and n disagree: {k.shape} against {n.shape}"
        raise ValueError(msg)
    if k.size == 0:
        msg = "no cells to fit"
        raise ValueError(msg)
    if np.any(n <= 0):
        msg = "a cell with no cards carries no information and must be excluded upstream"
        raise ValueError(msg)
    if np.any(k > n):
        msg = "a species cannot be recorded on more cards than were submitted"
        raise ValueError(msg)

    detections = int((k > 0).sum())
    if detections == 0:
        # Never seen: psi is zero at the maximum and p is undefined. Returned rather than raised,
        # because "absent from the footprint" is a real answer and the caller should not have to
        # catch an exception to hear it.
        return Occupancy(
            psi=0.0,
            p=float("nan"),
            psi_low=0.0,
            psi_high=0.0,
            cells=int(k.size),
            detections=0,
            loglik=0.0,
            converged=True,
        )

    psi, p, peak, converged = _fit_free(k, n)
    low, high = _profile(k, n, psi, peak)
    return Occupancy(
        psi=psi,
        p=p,
        psi_low=low,
        psi_high=high,
        cells=int(k.size),
        detections=detections,
        loglik=peak,
        converged=converged,
    )


def occupied_given_silence(psi: float, p: float, n: np.ndarray) -> np.ndarray:
    """Pr(occupied | recorded on none of `n` cards), per `phase1e-atlas.md` §5.

    What the map needs and the reporting rate cannot give: a cell where a species was never recorded
    is not the same as a cell where it is absent, and this is by how much. A cell with two cards and
    a hard-to-detect species stays likely occupied; the same silence over eighty cards does not.
    """
    n = np.asarray(n, dtype=np.float64)
    missed = psi * (1 - p) ** n
    return missed / (missed + (1 - psi))
