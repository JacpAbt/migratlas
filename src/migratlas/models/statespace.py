"""A two-state hidden Markov model for animal steps, written rather than imported.

Every dependency here must be a wheel, which rules out the R-derived movement packages, so the
Baum-Welch is written out. It is the standard one: a gamma emission on step length, a von Mises
emission on turning angle, a 2x2 transition matrix, and forward-backward with per-step scaling so
a thousand-step sequence does not underflow.

**States are ordered by mean step length after fitting**, so "encamped" and "travelling" are labels
assigned by size rather than by whichever component the initialisation happened to find. Without
that, two runs of the same data can return the same model with its labels swapped, and every
downstream fraction flips with them.

The M-step uses **weighted moments** for the gamma rather than a full maximum likelihood: shape and
scale from the posterior-weighted mean and variance. It is the standard initialisation for these
models and is kept as the update because it is stable, has no inner solve, and the quantity this
project reads off is a posterior probability rather than a shape parameter.
"""

from dataclasses import dataclass
from typing import Final

import numpy as np

STATES: Final = 2
"""Two. A third would need a registered reason and a way to name it."""

MAX_ITERATIONS: Final = 200
TOLERANCE: Final = 1e-6
FLOOR: Final = 1e-300
"""Densities below this are floored, so a scaled forward pass never divides by zero."""


@dataclass(frozen=True, slots=True)
class Emissions:
    """One state's step-length gamma and turning-angle von Mises."""

    shape: float
    scale: float
    mu: float
    kappa: float

    @property
    def mean_step(self) -> float:
        return self.shape * self.scale


@dataclass(frozen=True, slots=True)
class TwoState:
    """A fitted model: two emissions, a transition matrix, and what it cost to fit."""

    states: tuple[Emissions, Emissions]
    """Ordered by mean step length: index 0 encamped, index 1 travelling."""
    transition: np.ndarray
    start: np.ndarray
    log_likelihood: float
    iterations: int

    @property
    def separation(self) -> float:
        """How many times longer the travelling state's mean step is. Prediction 2's quantity."""
        small = self.states[0].mean_step
        return self.states[1].mean_step / small if small > 0 else float("inf")


def _gamma_logpdf(x: np.ndarray, shape: float, scale: float) -> np.ndarray:
    """Log density of a gamma, without scipy: shape and scale, x strictly positive."""
    from math import lgamma  # noqa: PLC0415 -- one call, and stdlib

    safe = np.maximum(x, FLOOR)
    density = (shape - 1.0) * np.log(safe) - safe / scale - shape * np.log(scale) - lgamma(shape)
    return np.asarray(density, dtype=float)


def _von_mises_logpdf(angle: np.ndarray, mu: float, kappa: float) -> np.ndarray:
    """Log density of a von Mises. `i0` comes from numpy, so no scipy is needed."""
    return kappa * np.cos(angle - mu) - np.log(2.0 * np.pi * np.i0(kappa))


def _emission_logpdf(
    steps: np.ndarray, angles: np.ndarray, emissions: Emissions, *, use_angles: bool
) -> np.ndarray:
    out = _gamma_logpdf(steps, emissions.shape, emissions.scale)
    if use_angles:
        out = out + _von_mises_logpdf(angles, emissions.mu, emissions.kappa)
    return out


def _forward_backward(
    log_density: np.ndarray, transition: np.ndarray, start: np.ndarray
) -> tuple[np.ndarray, np.ndarray, float]:
    """Scaled forward-backward over one sequence.

    Returns the per-step state posteriors, the summed pair posteriors, and the log likelihood.
    Scaling at every step rather than working in logs throughout: the arithmetic is the same and
    the M-step wants probabilities, not log probabilities.
    """
    length = log_density.shape[0]
    density = np.exp(log_density - log_density.max(axis=1, keepdims=True))
    offset = float(log_density.max(axis=1).sum())

    alpha = np.zeros((length, STATES))
    scaling = np.zeros(length)
    alpha[0] = start * density[0]
    scaling[0] = alpha[0].sum()
    if scaling[0] <= 0:
        return np.full((length, STATES), 0.5), np.zeros((STATES, STATES)), float("-inf")
    alpha[0] /= scaling[0]
    for t in range(1, length):
        alpha[t] = (alpha[t - 1] @ transition) * density[t]
        scaling[t] = alpha[t].sum()
        if scaling[t] <= 0:
            return np.full((length, STATES), 0.5), np.zeros((STATES, STATES)), float("-inf")
        alpha[t] /= scaling[t]

    beta = np.zeros((length, STATES))
    beta[-1] = 1.0
    for t in range(length - 2, -1, -1):
        beta[t] = transition @ (density[t + 1] * beta[t + 1]) / scaling[t + 1]

    posterior = alpha * beta
    posterior /= np.maximum(posterior.sum(axis=1, keepdims=True), FLOOR)

    pairs = np.zeros((STATES, STATES))
    for t in range(length - 1):
        joint = (
            transition
            * np.outer(alpha[t], density[t + 1] * beta[t + 1])
            / max(scaling[t + 1], FLOOR)
        )
        pairs += joint
    return posterior, pairs, float(np.log(scaling).sum() + offset)


def _weighted_gamma(values: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    """Shape and scale from the weighted mean and variance. Zero variance gives a tight state."""
    total = float(weights.sum())
    if total <= 0:
        return (1.0, 1.0)
    mean = float((weights * values).sum() / total)
    variance = float((weights * (values - mean) ** 2).sum() / total)
    if mean <= 0 or variance <= 0:
        return (1.0, max(mean, FLOOR))
    return (mean * mean / variance, variance / mean)


def _weighted_von_mises(angles: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    """Circular mean, and concentration by the standard closed-form approximation."""
    total = float(weights.sum())
    if total <= 0:
        return (0.0, 0.1)
    cosine = float((weights * np.cos(angles)).sum() / total)
    sine = float((weights * np.sin(angles)).sum() / total)
    mu = float(np.arctan2(sine, cosine))
    resultant = float(min(np.hypot(cosine, sine), 0.999))
    # Banerjee's approximation to the inverse of I1/I0, which has no closed form.
    kappa = resultant * (2.0 - resultant**2) / max(1.0 - resultant**2, FLOOR)
    return (mu, float(min(max(kappa, 1e-3), 100.0)))


def _initial(steps: np.ndarray) -> tuple[Emissions, Emissions]:
    """Split at the median and take moments from each half. Deterministic, so runs agree."""
    median = float(np.median(steps))
    low = steps[steps <= median]
    high = steps[steps > median]
    if low.size == 0 or high.size == 0:
        low = high = steps
    shape_low, scale_low = _weighted_gamma(low, np.ones_like(low))
    shape_high, scale_high = _weighted_gamma(high, np.ones_like(high))
    return (
        Emissions(shape=shape_low, scale=scale_low, mu=np.pi, kappa=0.5),
        Emissions(shape=shape_high, scale=scale_high, mu=0.0, kappa=1.0),
    )


def fit(
    sequences: list[tuple[np.ndarray, np.ndarray]], *, use_angles: bool = True
) -> TwoState | None:
    """Baum-Welch over a list of (step length, turning angle) sequences.

    Every sequence belongs to one animal and one run of regular intervals; the model is shared and
    the sequences are independent given it, which is what lets a source be fitted at once.
    """
    steps = [s for s, _ in sequences if s.size >= STATES]
    if not steps:
        return None
    pooled = np.concatenate(steps)
    if pooled.size < STATES or not np.all(np.isfinite(pooled)):
        return None

    emissions = list(_initial(pooled))
    transition = np.array([[0.9, 0.1], [0.1, 0.9]])
    start = np.array([0.5, 0.5])
    previous = float("-inf")
    iterations = 0

    for iteration in range(1, MAX_ITERATIONS + 1):
        iterations = iteration
        total_log = 0.0
        pair_sum = np.zeros((STATES, STATES))
        start_sum = np.zeros(STATES)
        weights: list[np.ndarray] = []
        kept: list[tuple[np.ndarray, np.ndarray]] = []
        for step, angle in sequences:
            if step.size < STATES:
                continue
            log_density = np.column_stack(
                [_emission_logpdf(step, angle, e, use_angles=use_angles) for e in emissions]
            )
            posterior, pairs, log_likelihood = _forward_backward(log_density, transition, start)
            if not np.isfinite(log_likelihood):
                continue
            total_log += log_likelihood
            pair_sum += pairs
            start_sum += posterior[0]
            weights.append(posterior)
            kept.append((step, angle))
        if not kept:
            return None

        all_posterior = np.concatenate(weights)
        all_steps = np.concatenate([s for s, _ in kept])
        all_angles = np.concatenate([a for _, a in kept])
        emissions = []
        for state in range(STATES):
            weight = all_posterior[:, state]
            shape, scale = _weighted_gamma(all_steps, weight)
            mu, kappa = _weighted_von_mises(all_angles, weight)
            emissions.append(Emissions(shape=shape, scale=scale, mu=mu, kappa=kappa))
        rows = pair_sum.sum(axis=1, keepdims=True)
        transition = np.where(rows > 0, pair_sum / np.maximum(rows, FLOOR), 0.5)
        start = start_sum / max(start_sum.sum(), FLOOR)

        if abs(total_log - previous) <= TOLERANCE * max(abs(previous), 1.0):
            previous = total_log
            break
        previous = total_log

    order = np.argsort([e.mean_step for e in emissions])
    ordered = (emissions[int(order[0])], emissions[int(order[1])])
    return TwoState(
        states=ordered,
        transition=transition[np.ix_(order, order)],
        start=start[order],
        log_likelihood=previous,
        iterations=iterations,
    )


def decode(
    model: TwoState, steps: np.ndarray, angles: np.ndarray, *, use_angles: bool = True
) -> np.ndarray:
    """Per-step posterior probability of each state, for one sequence."""
    log_density = np.column_stack(
        [_emission_logpdf(steps, angles, e, use_angles=use_angles) for e in model.states]
    )
    posterior, _, _ = _forward_backward(log_density, model.transition, model.start)
    return posterior
