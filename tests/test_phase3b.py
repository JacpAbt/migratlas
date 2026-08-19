"""Phase 3b's segment selection and regression arithmetic, no lake required."""

import numpy as np

from migratlas.reports.phase3b import (
    MIN_SEGMENT_YEARS,
    Segment,
    Unit,
    longest_segment,
    regression,
)


def test_a_single_gear_record_is_one_segment() -> None:
    record = [(year, "GOV") for year in range(1990, 2020)]
    segment = longest_segment(record)
    assert segment is not None
    assert (segment.start, segment.end, segment.years) == (1990, 2019, 30)


def test_the_longest_segment_wins_and_ties_go_earlier() -> None:
    record = [(y, "A") for y in range(1980, 2005)] + [(y, "B") for y in range(2005, 2030)]
    segment = longest_segment(record)
    assert segment is not None
    # Both runs are 25 years; the earlier one is the registered choice.
    assert segment.gear == "A"
    assert segment.start == 1980


def test_a_skipped_year_does_not_break_a_segment() -> None:
    years = [y for y in range(1990, 2020) if y != 2001]
    segment = longest_segment([(y, "GOV") for y in years])
    assert segment is not None
    assert segment.years == len(years)


def test_a_fragmented_record_yields_nothing() -> None:
    record = [(year, "A" if year % 2 else "B") for year in range(1990, 2020)]
    assert longest_segment(record) is None
    assert longest_segment([]) is None
    short = [(year, "GOV") for year in range(2010, 2010 + MIN_SEGMENT_YEARS - 1)]
    assert longest_segment(short) is None


def _unit(lat: float, ci: float, temp: float, depth: float) -> Unit:
    return Unit(
        segment=Segment(survey="S", gear="G", start=1990, end=2019, years=30),
        species=20,
        latitude_trend=lat,
        latitude_ci=ci,
        temperature_trend=temp,
        bottom_trend=None,
        median_depth_m=depth,
    )


def test_homogeneous_units_fail_the_q_test_and_a_spread_passes() -> None:
    rng = np.random.default_rng(2)
    same = [_unit(0.1 + rng.normal(scale=0.005), 0.2, 0.3 + i * 0.01, 100.0 + i) for i in range(15)]
    assert not regression(same).heterogeneous
    spread = [_unit((-1.0) ** i * 0.5, 0.05, 0.3 + i * 0.01, 100.0 + i) for i in range(15)]
    assert regression(spread).heterogeneous


def test_a_planted_warming_slope_is_recovered() -> None:
    rng = np.random.default_rng(7)
    units = []
    for i in range(20):
        temp = float(rng.normal(0.3, 0.2))
        units.append(
            _unit(0.05 + 0.8 * temp + float(rng.normal(scale=0.02)), 0.1, temp, 150.0 + i * 10)
        )
    fit = regression(units)
    assert abs(fit.temp_slope - 0.8) < 0.1
    assert fit.temp_slope - fit.temp_ci > 0
