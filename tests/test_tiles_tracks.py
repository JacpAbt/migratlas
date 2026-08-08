"""The journeys layer's refusal and its segmenting, tested at the seams.

The identified-product refusal fires before the lake is read, so CI can prove a de-identifying
clearance cannot produce a line without holding any track data at all.
"""

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from migratlas.evidence import Realm
from migratlas.tiles.tracks import TrackSpec, _segments, _simplify, build_tracks


def test_a_deidentifying_clearance_cannot_draw_lines(tmp_path: Path) -> None:
    """MODERATE drops identifiers, and a journeys layer is an identified product by definition."""
    spec = TrackSpec(
        name="test-journeys",
        source_id="movebank_yahatinda_elk",
        realm=Realm.TERRESTRIAL,
        title="t",
        description="d",
        popup_caveat="c",
    )
    with pytest.raises(ValueError, match="de-identifies"):
        build_tracks(spec, tmp_path)


def _path(rows: list[tuple[str, float, float]]) -> pl.DataFrame:
    """Days as (iso date, lon, lat)."""
    return pl.DataFrame(
        {
            "day": [date.fromisoformat(r[0]) for r in rows],
            "lon": [r[1] for r in rows],
            "lat": [r[2] for r in rows],
        }
    )


def test_a_silence_splits_the_line_rather_than_being_drawn_across() -> None:
    segments = _segments(
        _path(
            [
                ("2020-01-01", 10.0, 50.0),
                ("2020-01-02", 10.1, 50.1),
                ("2020-02-01", 10.5, 50.5),
                ("2020-02-02", 10.6, 50.6),
            ]
        )
    )
    assert len(segments) == 2
    assert segments[0] == [(10.0, 50.0), (10.1, 50.1)]


def test_days_in_the_same_cell_collapse_to_one_vertex() -> None:
    segments = _segments(
        _path(
            [
                ("2020-01-01", 10.0, 50.0),
                ("2020-01-02", 10.0, 50.0),
                ("2020-01-03", 10.0, 50.0),
                ("2020-01-04", 10.1, 50.1),
            ]
        )
    )
    assert segments == [[(10.0, 50.0), (10.1, 50.1)]]


def test_a_lone_day_after_a_silence_is_not_a_line() -> None:
    segments = _segments(
        _path(
            [
                ("2020-01-01", 10.0, 50.0),
                ("2020-01-02", 10.1, 50.1),
                ("2020-03-01", 11.0, 51.0),
            ]
        )
    )
    assert len(segments) == 1


def test_a_straight_staircase_simplifies_to_its_endpoints() -> None:
    """Days walking a line are a staircase of cells carrying nothing the endpoints do not."""
    run = [(10.0 + i * 0.01, 50.0 + i * 0.01) for i in range(20)]
    assert _simplify(run, 0.01) == [run[0], run[-1]]


def test_a_real_turn_survives_simplification() -> None:
    """The excursion's farthest point is the journey; simplification must never eat it."""
    out_and_back = [(10.0, 50.0), (10.2, 50.0), (10.4, 50.2), (10.2, 50.4), (10.0, 50.4)]
    kept = _simplify(out_and_back, 0.01)
    assert (10.4, 50.2) in kept
