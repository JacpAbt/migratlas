"""UKBMS's three silent-error risks, pinned.

Every assertion here is for something that would produce plausible-looking wrong data rather than a
crash: dates ninety days early, a mean flight date that cannot be recovered from what was stored, a
pooled brood row averaged across two generations, or a site entering the lake without the position
its publisher deliberately withheld.
"""

from datetime import UTC, datetime

import polars as pl
import pytest

from migratlas.ingest import ukbms

SPAN = [1995, 1996]


def _phenology(**overrides: object) -> pl.DataFrame:
    """One row of the archive's own shape, with its real column names."""
    row: dict[str, object] = {
        "SITENO": 1,
        "SITENAME": "Woodwalton Farm",
        "GRIDREF": "TL214817",
        "SPECIES_NAME": "Aglais io",
        "COMMON_NAME": "Peacock",
        "YEAR": 1995,
        "NUMBER_OF_BROODS": 1,
        "BROOD": 0,
        "FIRSTDAY": 20,
        "LASTDAY": 180,
        "PEAKDAY": 104,
        "PEAKCOUNT": 7,
        "MEAN_FLIGHT_DATE": 85.67,
        "FLIGHTPERIOD_SD": 42.89,
        "FLIGHTPERIOD_RANGE": 160,
    }
    row.update(overrides)
    return pl.DataFrame([row])


def _positions(site: int = 1) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "site": [site],
            "country": ["England"],
            "site_longitude": [-0.19],
            "site_latitude": [52.42],
        }
    )


KEYS = {"Aglais io": 1898286}


def test_day_numbers_count_from_the_first_of_april() -> None:
    """The archive's example is "20 = 20th April". Read as a day of year it is 20 January.

    This is the defect that would have been invisible: every date about ninety days early, on a
    record whose whole purpose is timing, and every one of them a plausible date for *some*
    butterfly.
    """
    rows = ukbms.to_evidence(_phenology(), _positions(), KEYS)
    start = rows["period_start"].item()
    end = rows["period_end"].item()

    assert start == datetime(1995, 4, 20, tzinfo=UTC), f"day 20 landed on {start}"
    # Day 180 from 1 April: April has 30 days, so 180 is late September.
    assert end == datetime(1995, 9, 27, tzinfo=UTC), f"day 180 landed on {end}"


def test_the_mean_flight_date_is_recoverable_from_what_was_stored() -> None:
    """`count` is days from first appearance, so `period_start + count` is the mean flight date.

    The alternative -- storing the mean flight date as a day number in `count` -- would put a
    coordinate on the time axis into the column `sabap1` fills with a reporting rate, where any
    aggregation would be averaging calendars. This asserts the encoding round-trips exactly.
    """
    rows = ukbms.to_evidence(_phenology(), _positions(), KEYS)
    offset = rows["count"].item()

    assert offset == pytest.approx(85.67 - 20)
    recovered = rows["period_start"].item().timestamp() + offset * 86400
    expected = datetime(1995, 4, 20, tzinfo=UTC).timestamp() + (85.67 - 20) * 86400
    assert recovered == pytest.approx(expected)
    # And it lands inside the flight period it describes, which a day-number would not have.
    assert rows["period_start"].item() <= datetime.fromtimestamp(recovered, UTC)
    assert datetime.fromtimestamp(recovered, UTC) <= rows["period_end"].item()


def test_a_site_with_no_published_position_cannot_enter_the_lake() -> None:
    """The scheme withholds sensitive site locations, and that has to propagate rather than be
    patched around: SURVEY_INDEX requires a position, so the row is simply absent."""
    rows = ukbms.to_evidence(_phenology(SITENO=999), _positions(site=1), KEYS)
    assert rows.height == 0


def test_a_taxon_the_backbone_does_not_know_is_dropped_rather_than_guessed() -> None:
    """A null taxon_key on an `exact` source would claim a precision it does not have."""
    rows = ukbms.to_evidence(_phenology(SPECIES_NAME="Nonexistentia ficta"), _positions(), KEYS)
    assert rows.height == 0


def test_the_brood_carries_into_the_protocol_so_generations_stay_separable() -> None:
    """Two flight periods of one species at one site in one year are two rows differing only in
    their dates, so the protocol names which generation each is."""
    whole = ukbms.to_evidence(_phenology(), _positions(), KEYS)
    second = ukbms.to_evidence(
        _phenology(NUMBER_OF_BROODS=2, BROOD=2, FIRSTDAY=90, LASTDAY=150, MEAN_FLIGHT_DATE=120.5),
        _positions(),
        KEYS,
    )
    assert whole["protocol"].item() == "pollard-walk"
    assert second["protocol"].item() == "pollard-walk/gen2"


@pytest.mark.parametrize(
    ("broods", "brood", "kept"),
    [
        (1, 0, True),  # single-generation species: the pooled row is the only record
        (2, 0, False),  # generations were separated, so the pooled row is a mean of two peaks
        (2, 1, True),
        (2, 2, True),
    ],
)
def test_the_pooled_row_survives_only_where_generations_were_not_split(
    broods: int, brood: int, *, kept: bool
) -> None:
    """`BROOD = 0` means two different things depending on `NUMBER_OF_BROODS`, and one of them is a
    date no animal experienced. Exercises the filter's logic on the archive's own encoding."""
    frame = _phenology(NUMBER_OF_BROODS=broods, BROOD=brood)
    split = frame.filter(pl.col("NUMBER_OF_BROODS") > 1, pl.col("BROOD") > 0)
    whole = frame.filter(pl.col("NUMBER_OF_BROODS") <= 1, pl.col("BROOD") == 0)
    assert (pl.concat([whole, split]).height == 1) is kept


def test_british_national_grid_lands_in_britain() -> None:
    """A projection mistake here would put every site in the sea, and the fourth leg samples
    temperature at these coordinates."""
    pyproj = pytest.importorskip("pyproj", reason="the geo extra")
    to_degrees = pyproj.Transformer.from_crs(ukbms.BNG, "EPSG:4326", always_xy=True)
    # Woodwalton Farm, the archive's own first row: easting 521400, northing 281700.
    longitude, latitude = to_degrees.transform(521400, 281700)

    assert latitude == pytest.approx(52.42, abs=0.05), f"latitude {latitude}"
    assert longitude == pytest.approx(-0.19, abs=0.05), f"longitude {longitude}"
