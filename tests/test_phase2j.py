"""Phase 2j's plumbing, on tracks whose geometry is built in.

The state model has its own tests; these cover what this module adds to it -- the step geometry,
the interval filter that stands in for Phase 1h's refusal, and the decoding into animal-years.
"""

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from migratlas.models import statespace
from migratlas.reports import phase2j


def _track(  # noqa: PLR0913 -- one knob per geometry the filter has to handle
    *,
    animal: str = "a1",
    year: int = 2010,
    n: int = 400,
    hours: float = 1.0,
    step_deg: float = 0.01,
    irregular_every: int = 0,
) -> pl.DataFrame:
    """A straight walk north at a fixed interval, optionally with a long gap every so often."""
    rows = []
    when = datetime(year, 2, 1, tzinfo=UTC)
    latitude = 51.0
    for index in range(n):
        rows.append(
            {
                "individual_id": animal,
                "timestamp": when,
                "latitude": latitude,
                "longitude": -115.0,
            }
        )
        gap = hours * 5 if irregular_every and index % irregular_every == 0 else hours
        when += timedelta(hours=gap)
        latitude += step_deg
    return pl.DataFrame(rows)


def test_the_step_length_is_the_great_circle_distance() -> None:
    frame = _track(n=3, step_deg=1.0)
    steps = phase2j.steps_of(frame, 1.0)
    # One degree of latitude is about 111 km anywhere on the sphere.
    assert steps["km"].to_numpy() == pytest.approx(np.full(2, 111.19), rel=0.01)


def test_a_step_at_the_wrong_interval_is_dropped() -> None:
    """The interval filter is what makes two steps comparable, and Phase 1h's reason for it."""
    frame = _track(n=40, hours=1.0, irregular_every=5)
    steps = phase2j.steps_of(frame, 1.0)
    gaps = steps["gap"].to_numpy()
    assert gaps.size > 0
    assert np.all(np.abs(gaps - 1.0) <= phase2j.INTERVAL_TOLERANCE)
    assert steps.height < 39


def test_steps_do_not_join_across_two_animals() -> None:
    frame = pl.concat([_track(animal="a1", n=30), _track(animal="a2", n=30)])
    steps = phase2j.steps_of(frame, 1.0)
    assert set(steps["individual_id"].to_list()) == {"a1", "a2"}
    # 29 within-animal steps each, and none bridging the two.
    assert steps.height == 58


def test_the_modal_interval_is_read_from_the_fixes() -> None:
    assert phase2j.modal_interval(_track(n=50, hours=2.0)) == pytest.approx(2.0)
    assert phase2j.modal_interval(_track(n=50, hours=0.5)) == pytest.approx(0.5)


def test_a_turning_angle_is_zero_on_a_straight_walk() -> None:
    steps = phase2j.steps_of(_track(n=30), 1.0)
    sequences = phase2j.sequences_of(steps)
    assert len(sequences) == 1
    _, turns = sequences[0]
    assert turns[1:] == pytest.approx(np.zeros(turns.size - 1), abs=1e-6)


def test_a_short_run_is_not_a_sequence() -> None:
    steps = phase2j.steps_of(_track(n=5), 1.0)
    assert phase2j.sequences_of(steps) == []


def test_an_animal_year_needs_its_two_hundred_steps() -> None:
    model = statespace.fit(phase2j.sequences_of(phase2j.steps_of(_track(n=400), 1.0)))
    assert model is not None
    short = phase2j.steps_of(_track(n=50), 1.0)
    assert phase2j.animal_years(short, model, "s") == []
    long_enough = phase2j.steps_of(_track(n=400), 1.0)
    rows = phase2j.animal_years(long_enough, model, "s")
    assert len(rows) == 1
    assert rows[0].steps >= phase2j.MIN_STEPS_PER_YEAR
    assert 0.0 <= rows[0].travelling_fraction <= 1.0


def test_a_walk_that_alternates_dawdling_and_striding_splits_into_two_states() -> None:
    """End to end on one animal: the fraction must be neither zero nor one."""
    rng = np.random.default_rng(5)
    rows = []
    when = datetime(2010, 2, 1, tzinfo=UTC)
    latitude, longitude = 51.0, -115.0
    for index in range(1200):
        striding = (index // 60) % 2 == 1
        rows.append(
            {
                "individual_id": "a1",
                "timestamp": when,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
        size = 0.05 if striding else 0.002
        latitude += size + float(rng.normal(0, size / 10))
        longitude += float(rng.normal(0, size / 10))
        when += timedelta(hours=1)
    frame = pl.DataFrame(rows)
    steps = phase2j.steps_of(frame, 1.0)
    model = statespace.fit(phase2j.sequences_of(steps))
    assert model is not None
    assert model.separation > phase2j.SEPARATION_BAR
    decoded = phase2j.animal_years(steps, model, "s")
    assert len(decoded) == 1
    assert 0.2 < decoded[0].travelling_fraction < 0.8
