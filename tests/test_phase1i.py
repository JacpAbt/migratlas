"""The transfer test's arithmetic, against inputs whose answer is known in advance.

Two things are checked here that the lake cannot check. First that `grade` says "these agree" when
handed three samples of one distribution and "this one does not" when handed a displaced one --
the whole claim is a verdict on agreement, and a verdict that could not distinguish those would be
decoration. Second that the aerial conversion, which is the only leg needing one and the reason
note §5 carries a stop condition, returns the ratio the construction was built to have.

The n-dependence of the registered criterion is pinned here too. It is a known weakness rather than
a bug, recorded as a correction in the method note, and a test is how it stays known.
"""

import numpy as np
import polars as pl
import pytest
from scipy import stats

from migratlas.reports import phase1i
from migratlas.reports.phase2a_timing import Sensitivity


def _leg(
    realm: str, centre: float, *, n: int = 400, spread: float = 1.0, seed: int = 3
) -> phase1i.Leg:
    return phase1i.Leg(realm, np.random.default_rng(seed).normal(centre, spread, n))


def test_three_samples_of_one_distribution_are_graded_as_agreeing() -> None:
    """The null case. If this fails, every disagreement the module reports is suspect."""
    legs = tuple(_leg(f"realm-{i}", 0.0, seed=i) for i in range(3))
    verdict = phase1i.grade(legs)

    assert not verdict.realms_disagree, f"p={verdict.kruskal_p}"
    assert len(verdict.indistinguishable) == 3, "every pair should be indistinguishable"
    assert all(held.transfers for held in verdict.held_out)


def test_a_displaced_realm_is_the_one_the_test_names() -> None:
    legs = (_leg("same-a", 0.0, seed=1), _leg("same-b", 0.0, seed=2), _leg("apart", 5.0, seed=3))
    verdict = phase1i.grade(legs)

    assert verdict.realms_disagree
    assert verdict.worst.realm == "apart"
    assert not verdict.worst.transfers
    # The two undisplaced realms still find each other.
    assert {pair.left for pair in verdict.indistinguishable} == {"same-a"}


def test_coverage_finds_half_of_a_realm_it_predicts_correctly() -> None:
    """Note §3 scores on spread and coverage as well as centre, and 50% is what right looks like."""
    legs = tuple(_leg(f"realm-{i}", 0.0, n=2000, seed=i) for i in range(3))
    held = phase1i.grade(legs).held_out[0]

    assert held.coverage == pytest.approx(0.5, abs=0.05)
    assert held.iqr_ratio == pytest.approx(1.0, abs=0.1)


def test_coverage_falls_away_from_a_realm_it_predicts_badly() -> None:
    legs = (_leg("a", 0.0, seed=1), _leg("b", 0.0, seed=2), _leg("apart", 3.0, seed=3))
    apart = next(held for held in phase1i.grade(legs).held_out if held.realm == "apart")

    assert apart.coverage < 0.1, "a realm three sigma away should barely intersect the prediction"


def test_the_registered_criterion_forgives_a_small_sample_the_error_it_fails_a_large_one_for() -> (
    None
):
    """The weakness in note §4 prediction 2, pinned so it cannot quietly change.

    `transfers` compares the error to the standard error of the held-out median, which shrinks with
    n. The same offset therefore passes in a small realm and fails in a large one. This is graded as
    registered anyway -- the method note records why -- and coverage is published beside it.
    """
    offset = 0.1

    def verdict_at(n: int) -> phase1i.HoldOut:
        legs = (
            _leg("a", 0.0, n=400, seed=1),
            _leg("b", 0.0, n=400, seed=2),
            _leg("held", offset, n=n, seed=3),
        )
        return next(h for h in phase1i.grade(legs).held_out if h.realm == "held")

    small, large = verdict_at(30), verdict_at(20_000)

    assert small.error == pytest.approx(large.error, abs=0.15), "same displacement either way"
    assert small.transfers
    assert not large.transfers


def test_holm_never_reports_a_p_value_below_the_raw_one() -> None:
    legs = (_leg("a", 0.0, seed=1), _leg("b", 0.4, seed=2), _leg("c", 5.0, seed=3))
    verdict = phase1i.grade(legs)

    by_realm = {leg.realm: leg for leg in legs}
    for pair in verdict.pairs:
        raw = stats.mannwhitneyu(by_realm[pair.left].tracking, by_realm[pair.right].tracking).pvalue
        assert pair.p_adjusted >= raw - 1e-12, f"{pair.left} vs {pair.right}"
        assert pair.p_adjusted <= 1.0


def test_the_bootstrapped_interval_does_not_move_between_calls() -> None:
    """A published interval that changed on every build would not be an interval."""
    leg = _leg("a", 0.0)
    assert leg.median_se == leg.median_se


def _station_months(
    *, coupling: float = 1.0, cooling: float = -0.1, years: int = 20
) -> pl.DataFrame:
    """A station built so the conversion's answer is arithmetic rather than a fit.

    Autumn month `m` sits `cooling * (day(m) - day(Sep))` below that year's summer temperature, so
    the across-month slope is exactly `cooling` and the year-to-year coupling is exactly `coupling`.
    """
    anchor = phase1i.MID_MONTH[9]
    rows = []
    for index in range(years):
        summer = 20.0 + index * 0.1
        for month in phase1i.SUMMER_MONTHS:
            rows.append({"site_id": "s", "value": summer, "year": 1990 + index, "month": month})
        for month in phase1i.AUTUMN_MONTHS:
            rows.append(
                {
                    "site_id": "s",
                    "value": coupling * summer + cooling * (phase1i.MID_MONTH[month] - anchor),
                    "year": 1990 + index,
                    "month": month,
                }
            )
    return pl.DataFrame(rows)


def _station(per_degree: float) -> Sensitivity:
    return Sensitivity(
        station_id="s",
        latitude=42.0,
        driver_correlation=0.0,
        per_degree=per_degree,
        per_wind=0.0,
        warming_per_decade=0.3,
        observed_per_decade=-0.6,
        years=20,
    )


def test_the_aerial_conversion_returns_the_ratio_it_was_built_to_have() -> None:
    """Coupling 1.0 degC per degC over a 0.1 degC/day cooling is a thermal calendar of 10 days/degC.

    A station advancing 2 days per degree of summer warmth is then tracking -0.2 of it, and that
    number comes out of the construction rather than out of a fit.
    """
    ratios = phase1i._aerial_ratios(
        _station_months(coupling=1.0, cooling=-0.1), [_station(-2.0)], phase1i.AUTUMN_MONTHS
    )

    assert ratios == pytest.approx([-0.2], abs=1e-6)


def test_a_station_whose_autumn_does_not_cool_is_dropped_rather_than_divided_by() -> None:
    """Note §5's wild ratios come from a near-zero denominator, so the denominator is floored."""
    assert (
        phase1i._aerial_ratios(
            _station_months(cooling=-0.0001), [_station(-2.0)], phase1i.AUTUMN_MONTHS
        )
        == []
    )


def test_a_station_whose_autumn_ignores_its_summer_is_dropped() -> None:
    """With no coupling there is no thermal calendar to compare a passage date against."""
    assert (
        phase1i._aerial_ratios(
            _station_months(coupling=0.0), [_station(-2.0)], phase1i.AUTUMN_MONTHS
        )
        == []
    )


def test_a_station_with_too_few_shared_years_is_dropped() -> None:
    assert (
        phase1i._aerial_ratios(
            _station_months(years=phase1i.MIN_SHARED_YEARS - 1),
            [_station(-2.0)],
            phase1i.AUTUMN_MONTHS,
        )
        == []
    )
