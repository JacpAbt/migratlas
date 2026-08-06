"""The occupancy model, checked against data whose answer is known.

`docs/TASKS.md` #9 makes this the gate: the model must recover parameters it was given from
simulated data before it is allowed near SABAP. Nothing downstream of it is trustworthy otherwise,
and a detection model that is quietly wrong is worse than no detection model — it would licence the
exact claim the naive comparison cannot support.

Every test here simulates from the model's own generative story: a cell is occupied with
probability psi, and an occupied cell records the species on each of its n cards with probability p.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from migratlas.models import occupancy


def simulate(
    psi: float,
    p: float,
    *,
    cells: int = 400,
    cards: int = 12,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Cards recording the species, and cards submitted, for one species in one epoch."""
    rng = np.random.default_rng(seed)
    n = rng.integers(1, cards + 1, size=cells).astype(np.float64)
    occupied = rng.random(cells) < psi
    k = np.where(occupied, rng.binomial(n.astype(int), p), 0).astype(np.float64)
    return k, n


@pytest.mark.parametrize(
    ("psi", "p"),
    [
        (0.70, 0.50),
        (0.30, 0.30),
        (0.90, 0.20),
        (0.50, 0.80),
        (0.20, 0.60),
    ],
)
def test_the_model_recovers_the_parameters_it_was_given(psi: float, p: float) -> None:
    """The gate. Four hundred cells is a realistic footprint, and the tolerance is what the
    likelihood can actually deliver at that size rather than a number chosen to pass."""
    estimates = [occupancy.fit(*simulate(psi, p, seed=seed)) for seed in range(8)]
    mean_psi = float(np.mean([fit.psi for fit in estimates]))
    mean_p = float(np.mean([fit.p for fit in estimates]))

    assert mean_psi == pytest.approx(psi, abs=0.05), f"psi recovered as {mean_psi:.3f}"
    assert mean_p == pytest.approx(p, abs=0.05), f"p recovered as {mean_p:.3f}"
    assert all(fit.converged for fit in estimates)


def test_the_naive_estimate_is_biased_low_and_the_model_is_not() -> None:
    """The entire reason this model exists, as a measurement rather than an assertion.

    A species detected imperfectly is missed in some occupied cells, so the share of cells where it
    was *seen* understates occupancy. If the corrected estimate were no better than the naive one
    there would be nothing to publish.
    """
    psi, p = 0.75, 0.25
    fits = [occupancy.fit(*simulate(psi, p, cards=6, seed=seed)) for seed in range(12)]

    naive = float(np.mean([fit.naive for fit in fits]))
    corrected = float(np.mean([fit.psi for fit in fits]))

    assert naive < psi - 0.05, f"naive {naive:.3f} should understate psi={psi}"
    assert corrected == pytest.approx(psi, abs=0.06), f"corrected {corrected:.3f}"
    assert abs(corrected - psi) < abs(naive - psi), "the correction has to help"


def test_the_profile_interval_covers_the_truth_about_as_often_as_it_claims() -> None:
    """A 95% interval that covers 60% of the time would make every published Δψ meaningless.

    Forty replicates, so the check is coarse; the floor is set where a genuinely broken interval
    fails and sampling noise does not.
    """
    psi, p = 0.6, 0.4
    covered = sum(
        fit.psi_low <= psi <= fit.psi_high
        for fit in (occupancy.fit(*simulate(psi, p, seed=seed)) for seed in range(40))
    )
    assert covered >= 32, f"covered {covered}/40, which is not a 95% interval"


def test_more_cards_per_cell_pin_occupancy_harder() -> None:
    """Effort should buy precision, and if it does not the interval is not reading the data."""
    thin = occupancy.fit(*simulate(0.6, 0.3, cards=3, seed=1))
    thick = occupancy.fit(*simulate(0.6, 0.3, cards=30, seed=1))
    assert (thick.psi_high - thick.psi_low) < (thin.psi_high - thin.psi_low)


def test_a_species_seen_in_every_cell_is_reported_as_pinned_not_as_precise() -> None:
    """`phase1e-atlas.md` §3: where a species is detected everywhere, p is at its boundary and psi
    is unidentifiable from below. That has to be visible to the caller rather than returned as a
    confident 1.0."""
    n = np.full(200, 10.0)
    k = np.full(200, 10.0)
    fit = occupancy.fit(k, n)

    assert fit.psi > 0.99
    assert fit.at_boundary, "a pinned estimate must announce itself"


def test_a_species_never_recorded_returns_absence_rather_than_raising() -> None:
    """A real answer, and the caller should not have to catch an exception to hear it."""
    fit = occupancy.fit(np.zeros(50), np.full(50, 8.0))
    assert fit.psi == 0.0
    assert fit.detections == 0
    assert math.isnan(fit.p)


def test_silence_over_many_cards_means_more_than_silence_over_two() -> None:
    """What the map needs and a reporting rate cannot give.

    A cell with two cards and a cryptic species stays probably occupied; the same silence over
    eighty cards does not. Monotone in effort, which is the property that makes it usable.
    """
    probability = occupancy.occupied_given_silence(0.8, 0.3, np.array([1, 2, 10, 80]))
    assert list(probability) == sorted(probability, reverse=True)
    assert probability[0] > 0.7
    assert probability[-1] < 0.01


def test_the_likelihood_peaks_at_the_estimate() -> None:
    """Cheap, and it catches an optimiser that returned the starting point."""
    k, n = simulate(0.65, 0.45, seed=3)
    fit = occupancy.fit(k, n)
    peak = occupancy.loglik(k, n, fit.psi, fit.p)
    for dpsi, dp in ((0.05, 0.0), (-0.05, 0.0), (0.0, 0.05), (0.0, -0.05)):
        assert occupancy.loglik(k, n, fit.psi + dpsi, fit.p + dp) < peak


@pytest.mark.parametrize(
    ("k", "n", "message"),
    [
        (np.array([1.0, 2.0]), np.array([3.0]), "disagree"),
        (np.array([]), np.array([]), "no cells"),
        (np.array([0.0]), np.array([0.0]), "no cards"),
        (np.array([5.0]), np.array([3.0]), "more cards than were submitted"),
    ],
)
def test_an_impossible_input_is_refused_rather_than_fitted(
    k: np.ndarray, n: np.ndarray, message: str
) -> None:
    """Each of these makes the binomial meaningless rather than merely unlikely."""
    with pytest.raises(ValueError, match=message):
        occupancy.fit(k, n)
