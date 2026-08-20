"""Phase 3h's pooling and its calibration gate, on constructed units.

Three things here could be wrong in a way no run would reveal. The pooling could average the wrong
axis and still return plausible numbers. The null could depend on iteration order, which is the
defect Phase 3f published and only found by measuring twice. And the calibration gate could pass
when arm A does not reproduce Phase 3a, which would let an uncalibrated ladder be interpreted.
"""

import numpy as np
import pytest

from migratlas.reports.phase3f import ALL_COLUMNS, SHARE, WIND, Unit
from migratlas.reports.phase3h import (
    LADDER,
    PROJECTABLE,
    ArmResult,
    calibration_verdict,
    regional_units,
    unit_seed,
)

CENTRAL = (40.0, -96.0)
"""Inside `central 37-42N`, per test_response_floor's own pinning of the crossing."""


def _unit(name: str, years: list[int], dates: list[float], fill: float) -> Unit:
    """A station unit whose covariates are all one constant, so pooling is checkable by eye."""
    return Unit(
        station_id=name,
        season="autumn",
        years=np.array(years),
        y=np.array(dates, dtype=float),
        x=np.full((len(years), len(ALL_COLUMNS)), fill, dtype=float),
        train=np.arange(len(years) - 2),
        test=np.arange(len(years) - 2, len(years)),
    )


def _sites(names: list[str]) -> dict[str, tuple[float, float]]:
    return dict.fromkeys(names, CENTRAL)


def test_a_region_is_the_mean_of_its_members_year_by_year() -> None:
    """The pooling must average across stations within a year, never across years."""
    span = list(range(1995, 2026))
    members = [
        _unit("KAAA", span, [250.0] * len(span), fill=1.0),
        _unit("KBBB", span, [260.0] * len(span), fill=3.0),
        _unit("KCCC", span, [270.0] * len(span), fill=5.0),
        _unit("KDDD", span, [280.0] * len(span), fill=7.0),
    ]
    built, dropped = regional_units(members, _sites([m.station_id for m in members]))

    assert [unit.station_id for unit in built] == ["central 37-42N"]
    assert not dropped
    region = built[0]
    assert region.y == pytest.approx([265.0] * len(span))
    assert region.x == pytest.approx(np.full((len(span), len(ALL_COLUMNS)), 4.0))


def test_a_year_only_some_members_reported_averages_only_those() -> None:
    """A gap at one station must not drag the regional mean toward zero or drop the year."""
    span = list(range(1995, 2026))
    short = [year for year in span if year != 2000]
    members = [
        _unit("KAAA", span, [250.0] * len(span), fill=1.0),
        _unit("KBBB", short, [270.0] * len(short), fill=1.0),
        _unit("KCCC", span, [250.0] * len(span), fill=1.0),
        _unit("KDDD", span, [250.0] * len(span), fill=1.0),
    ]
    built, _ = regional_units(members, _sites([m.station_id for m in members]))
    region = built[0]
    at_2000 = float(region.y[region.years.tolist().index(2000)])
    at_2001 = float(region.y[region.years.tolist().index(2001)])

    assert at_2000 == pytest.approx(250.0), "the absent station must not enter the mean"
    assert at_2001 == pytest.approx(255.0), "3 x 250 + 1 x 270 over four stations"
    assert region.years.size == len(span), "a year one station missed is still a region-year"


def test_a_region_under_the_station_floor_is_dropped_with_its_reason() -> None:
    """Three stations cannot support a regional mean, and silence about it would be worse."""
    span = list(range(1995, 2026))
    members = [_unit(f"K{i}", span, [250.0] * len(span), fill=1.0) for i in range(3)]
    built, dropped = regional_units(members, _sites([m.station_id for m in members]))

    assert not built
    assert any("under the floor" in line for line in dropped)


def test_a_station_with_no_position_is_dropped_rather_than_assumed() -> None:
    """A missing site would otherwise become a silent absence from every region."""
    span = list(range(1995, 2026))
    members = [_unit(f"K{i}", span, [250.0] * len(span), fill=1.0) for i in range(4)]
    sites = _sites([m.station_id for m in members])
    del sites["K0"]
    built, dropped = regional_units(members, sites)

    assert not built, "three remaining stations are under the floor"
    assert any("K0: no position" in line for line in dropped)


def test_a_units_null_stream_is_a_property_of_the_unit() -> None:
    """Phase 3f's published null moved between runs because its seeds came from list positions."""
    names = ["central 37-42N", "eastern 42-50N", "western 32-37N"]
    assert len({unit_seed(name) for name in names}) == len(names)
    assert unit_seed(names[0]) == unit_seed(names[0])
    # The same names in a different order give the same seeds, which is the whole point.
    assert [unit_seed(n) for n in names] == [unit_seed(n) for n in names[::-1]][::-1]


def test_arm_c_restricted_to_projectable_columns_is_exactly_arm_b() -> None:
    """Prediction 5's internal consistency check, pinned as a property of the ladder itself.

    If this ever fails the run's own consistency check becomes untrustworthy, because the two
    quantities it compares would no longer be the same fit under two names.
    """
    arm_b = next(arm for arm in LADDER if arm.key == "B")
    arm_c = next(arm for arm in LADDER if arm.key == "C")
    restricted = tuple(name for name in arm_c.columns if name in PROJECTABLE)

    assert restricted == arm_b.columns
    assert {WIND, SHARE} & set(arm_c.columns) == {WIND, SHARE}
    assert not {WIND, SHARE} & set(PROJECTABLE), "a wind term must never count as projectable"


def _arm_a(season: str, median: float) -> ArmResult:
    return ArmResult(
        arm="A",
        label="per station",
        season=season,
        scope="all",
        units=143,
        significant=20,
        bar=12,
        median_skill=median,
        skills={},
    )


def test_the_calibration_gate_passes_only_on_phase3as_own_medians() -> None:
    """The gate has to be able to fail, and by the amount that matters rather than any amount."""
    good = [_arm_a("autumn", 0.0055), _arm_a("spring", -0.0308)]
    passed, lines = calibration_verdict(good)
    assert passed
    assert all("reproduces" in line for line in lines)

    # Off in the fourth decimal: this is exactly the size of discrepancy the gate exists to catch,
    # since Phase 3a's own medians are of order 0.01.
    drifted = [_arm_a("autumn", 0.0061), _arm_a("spring", -0.0308)]
    failed, lines = calibration_verdict(drifted)
    assert not failed
    assert any("OFF by" in line for line in lines)


def test_a_missing_arm_a_fails_calibration_rather_than_passing_vacuously() -> None:
    """An empty result list must not read as agreement."""
    passed, lines = calibration_verdict([])
    assert not passed
    assert all("did not run" in line for line in lines)
