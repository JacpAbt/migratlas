"""The seasonal displacement measure, and the one property the whole design rests on.

Phase 1h discards path length and keeps displacement, on the argument that one scales with how often
the collar reported and the other does not. That argument is the note's entire justification for
publishing anything from a record whose fix interval changed 52-fold, so it is demonstrated here
rather than asserted: the same synthetic track is thinned and both measures are recomputed.
"""

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from migratlas.reports import phase1h


def _walk(
    *, days: int = 250, step_hours: float = 1.0, drift_km: float = 60.0, wander_km: float = 3.0
) -> pl.DataFrame:
    """One animal walking from a winter place to a summer place, with daily wandering on top.

    The wandering is what separates the two measures. A straight march would give the same answer
    either way and would prove nothing.
    """
    rng = np.random.default_rng(11)
    start = datetime(2015, 1, 5, tzinfo=UTC)
    steps = int(days * 24 / step_hours)
    degrees = drift_km / 111.0
    rows = []
    for index in range(steps):
        when = start + timedelta(hours=step_hours * index)
        along = index / steps
        rows.append(
            {
                "individual_id": "elk-1",
                "timestamp": when,
                "latitude": 51.7 + along * degrees + rng.normal(0, wander_km / 111.0),
                "longitude": -115.6 + rng.normal(0, wander_km / 111.0),
            }
        )
    return pl.DataFrame(rows)


def test_displacement_survives_thinning_and_path_length_does_not() -> None:
    """The claim Phase 1h is built on, measured on one track at three sampling rates.

    If this failed, the note's escape from the 52-fold fix-interval change would be imaginary and
    nothing in it could be published -- which is exactly what its stop condition says.
    """
    dense = phase1h.from_fixes(_walk(step_hours=1.0))
    assert len(dense) == 1

    displacements = []
    paths = []
    for keep in (1, 6, 24):
        thinned = _walk(step_hours=1.0).gather_every(keep)
        found = phase1h.from_fixes(thinned)
        assert len(found) == 1
        displacements.append(found[0].displacement_km)
        paths.append(found[0].path_km)

    # Displacement is a property of two positions, so thinning must barely touch it.
    spread = (max(displacements) - min(displacements)) / np.mean(displacements)
    assert spread < 0.05, f"displacement moved {spread:.1%} under thinning: {displacements}"

    # Path length is a sum along the track, so thinning must collapse it. Twenty-four-hourly
    # sampling cannot see a day's wandering and reports a much shorter walk.
    assert paths[0] > paths[-1] * 2, f"path length barely moved under thinning: {paths}"


def test_the_two_measures_disagree_about_the_same_animal() -> None:
    """Not a bug: it is the exhibit. One animal, one year, two numbers with different meanings."""
    found = phase1h.from_fixes(_walk())[0]
    assert found.path_km > found.displacement_km * 3
    assert found.displacement_km > 0


def test_a_straight_line_gives_the_true_great_circle_distance() -> None:
    """Units and formula, against a distance that can be checked by hand.

    One degree of latitude is about 111.2 km, so a fifth of a degree is about 22.2.
    """
    start = datetime(2015, 1, 20, tzinfo=UTC)
    rows = [
        {"individual_id": "a", "timestamp": start, "latitude": 50.0, "longitude": 10.0},
        {
            "individual_id": "a",
            "timestamp": datetime(2015, 8, 1, tzinfo=UTC),
            "latitude": 50.2,
            "longitude": 10.0,
        },
    ]
    found = phase1h.from_fixes(pl.DataFrame(rows))[0]
    assert found.displacement_km == pytest.approx(22.24, abs=0.1)


def test_an_animal_missing_a_season_is_not_a_zero() -> None:
    """A winter fix and no summer fix means no measurement, never a displacement of nothing."""
    start = datetime(2015, 1, 20, tzinfo=UTC)
    rows = [
        {"individual_id": "a", "timestamp": start, "latitude": 50.0, "longitude": 10.0},
        {
            "individual_id": "a",
            "timestamp": start + timedelta(days=3),
            "latitude": 50.1,
            "longitude": 10.0,
        },
    ]
    assert phase1h.from_fixes(pl.DataFrame(rows)) == []


def test_the_median_position_ignores_one_wandering_day() -> None:
    """A season is a place the animal was, not wherever it happened to be on one date."""
    base = [
        {
            "individual_id": "a",
            "timestamp": datetime(2015, 1, 20, tzinfo=UTC) + timedelta(days=day),
            "latitude": 50.0,
            "longitude": 10.0,
        }
        for day in range(20)
    ]
    summer = [
        {
            "individual_id": "a",
            "timestamp": datetime(2015, 7, 20, tzinfo=UTC) + timedelta(days=day),
            "latitude": 51.0,
            "longitude": 10.0,
        }
        for day in range(20)
    ]
    excursion = [
        {
            "individual_id": "a",
            "timestamp": datetime(2015, 1, 25, tzinfo=UTC),
            "latitude": 45.0,
            "longitude": 10.0,
        }
    ]
    without = phase1h.from_fixes(pl.DataFrame(base + summer))[0].displacement_km
    with_it = phase1h.from_fixes(pl.DataFrame(base + summer + excursion))[0].displacement_km
    assert with_it == pytest.approx(without, abs=1.0)


# --- The verdict --------------------------------------------------------------
def _season(year: int, animal: str, displacement: float, path: float, gap: float) -> phase1h.Season:
    return phase1h.Season(
        individual_id=animal,
        year=year,
        displacement_km=displacement,
        path_km=path,
        fixes=100,
        median_gap_h=gap,
    )


def test_the_confound_and_the_escape_are_graded_separately() -> None:
    """Prediction 1 must be able to fire while prediction 2 does not, or neither means much."""
    found = [
        _season(
            2010 + index, f"a{index}", displacement=50.0, path=500.0 / (1 + index), gap=1.0 + index
        )
        for index in range(12)
    ]
    verdict = phase1h.grade(found)
    assert verdict.confound_shown, (
        "path length does not track the fix interval in built-to-order data"
    )
    assert verdict.escape_holds, "displacement tracks the fix interval when it was held constant"


def test_a_trend_that_does_not_clear_its_interval_is_not_a_trend() -> None:
    rng = np.random.default_rng(3)
    flat = [
        _season(2005 + (index % 18), f"a{index}", float(rng.normal(40, 12)), 300.0, 2.0)
        for index in range(120)
    ]
    assert not phase1h.grade(flat).moved


def test_a_real_trend_is_found_within_animals_and_not_only_across_them() -> None:
    """Note section 4: a trend carried by which animals were collared is about the collaring."""
    found = [
        _season(year, f"a{animal}", 40.0 - (year - 2005) * 1.5, 300.0, 2.0)
        for animal in range(12)
        for year in range(2005, 2020)
    ]
    verdict = phase1h.grade(found)
    assert verdict.slope_km_per_decade == pytest.approx(-15.0, abs=0.5)
    assert verdict.within_animal_slope == pytest.approx(-15.0, abs=0.5)
