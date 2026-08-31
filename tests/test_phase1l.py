"""The decomposition's arithmetic, against constructions whose answer is known in advance.

`protocol-disagreement` is published on the strength of one subtraction: the variance of the paired
differences, less what the two fits' own standard errors say that variance would be with no method
effect at all. Everything the ledger entry claims rests on that being right, and the lake cannot
check it -- the lake has exactly one population pair and no known answer for it.

Two things are pinned. The **null**, which is the load-bearing one: two readings of one truth,
differing only by their stated errors, must leave nothing over. A decomposition that reports a
method effect there would report one everywhere, and the finding would be an artefact of its own
instrument. And the **recovery**, that a method effect deliberately built in comes back at the size
it was built at -- a null-only test passes just as well for a function that always returns None.

The sign-flip count is pinned too, because it is the softening clause in the published caveat: if it
over-counts, the caveat understates a real disagreement.
"""

import numpy as np
import pytest

from migratlas.reports import phase1l


def _readings(
    method_sd: float, *, n: int = 400, species_sd: float = 0.2, error_sd: float = 0.1, seed: int = 7
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Two programmes reading `n` species, with the method effect set by construction.

    Each species has a true trend drawn at `species_sd`. Each programme reads it with its own
    independent error at `error_sd`, and one programme's target is displaced per species at
    `method_sd` -- which is the quantity the decomposition has to recover.
    """
    rng = np.random.default_rng(seed)
    truth = rng.normal(0.0, species_sd, n)
    displacement = rng.normal(0.0, method_sd, n) if method_sd else np.zeros(n)
    se = np.full(n, error_sd)
    return (
        truth + rng.normal(0.0, error_sd, n),
        truth + displacement + rng.normal(0.0, error_sd, n),
        se,
        se.copy(),
    )


def test_two_readings_of_one_truth_leave_no_method_effect() -> None:
    """The null. If this fails, every method effect this module reports is its own noise."""
    split = phase1l.split_difference(*_readings(0.0))

    assert split.noise_share == pytest.approx(1.0, abs=0.12), (
        f"noise share {split.noise_share:.3f} on a construction with no method effect at all"
    )
    assert split.method_sd is None or split.method_sd < 0.04, (
        f"invented a method effect of {split.method_sd} where none was built in"
    )


def test_a_method_effect_that_was_built_in_comes_back_at_its_own_size() -> None:
    """The complement. A null-only test is also passed by a function that never finds anything."""
    built = 0.25
    split = phase1l.split_difference(*_readings(built))

    assert split.method_sd is not None, "found nothing in a construction built to contain 0.25"
    assert split.method_sd == pytest.approx(built, rel=0.15), (
        f"recovered {split.method_sd:.3f} from a built-in {built}"
    )
    assert split.noise_share < 0.5, (
        f"attributed {split.noise_share:.0%} of a real displacement to estimation error"
    )


def test_the_species_denominator_is_corrected_the_same_way_as_the_numerator() -> None:
    """The comparison is a ratio, so a correction applied to one side only would flatter it.

    Built with no method effect and a species spread of 0.2: the corrected between-species scatter
    has to come back at 0.2, not at the inflated raw figure that carries each fit's error.
    """
    split = phase1l.split_difference(*_readings(0.0, species_sd=0.2, error_sd=0.1))

    assert split.species_sd is not None
    assert split.species_sd == pytest.approx(0.2, rel=0.15), (
        f"corrected species scatter {split.species_sd:.3f} against a built-in 0.2"
    )


def test_a_sign_flip_is_only_excused_where_an_estimate_really_does_straddle_zero() -> None:
    """The softening clause in the caveat, which understates the finding if it over-counts.

    Four pairs, hand-built: two that flip with a slope inside its own error, one that flips with
    both slopes far outside it, and one that does not flip at all.
    """
    slope_one = np.array([0.01, -0.02, 0.90, 0.50])
    slope_two = np.array([-0.01, 0.30, -0.90, 0.60])
    se = np.array([0.10, 0.10, 0.10, 0.10])

    split = phase1l.split_difference(slope_one, slope_two, se, se.copy())

    assert split.flips == 3, f"counted {split.flips} sign flips in a construction holding 3"
    assert split.flips_explained == 2, (
        f"excused {split.flips_explained} of them; only 2 have an estimate straddling zero"
    )


def test_the_signal_figure_is_a_slope_over_its_own_error_and_not_the_reverse() -> None:
    """One transposition away from a number that reads the opposite of what it means.

    Slopes at 0.4 with errors of 0.1 are four standard errors from zero, which is the direction that
    licenses reading a single species. Inverted it would be 0.25 and the caveat would say these
    networks measure well.
    """
    slopes = np.full(50, 0.4)
    se = np.full(50, 0.1)

    split = phase1l.split_difference(slopes, slopes.copy(), se, se.copy())

    assert split.slope_vs_stderr == pytest.approx(4.0), (
        f"reported {split.slope_vs_stderr:.2f} where slope over error is 4.0"
    )
