from datetime import UTC, datetime

import polars as pl
import pytest

from migratlas.drivers import insitu
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind


def hauls(*, sst: object = "12.4", sbt: object = "8.1", depth: float = 90.0) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "site_id": ["NEUS-Fall:h1"],
            "period_start": [datetime(2015, 9, 1, tzinfo=UTC)],
            "longitude": [-70.5],
            "latitude": [42.5],
            "depth": [depth],
            "sst": [sst],
            "sbt": [sbt],
        }
    )


def test_temperatures_become_one_row_per_variable() -> None:
    """Long format, because the set of drivers is open and a wide table needs a migration."""
    frame = pl.from_arrow(insitu.to_samples(hauls(), "fishglob"))
    assert isinstance(frame, pl.DataFrame)
    assert sorted(frame["variable"].to_list()) == [
        "sea_bottom_temperature",
        "sea_surface_temperature",
    ]
    assert frame["kind"].unique().to_list() == [DriverKind.MEASURED.value]


def test_a_surface_reading_sits_at_the_surface_and_a_bottom_one_at_depth() -> None:
    frame = pl.from_arrow(insitu.to_samples(hauls(depth=137.0), "fishglob"))
    assert isinstance(frame, pl.DataFrame)
    by_variable = dict(zip(frame["variable"], frame["depth_m"], strict=True))
    assert by_variable["sea_surface_temperature"] == 0.0
    assert by_variable["sea_bottom_temperature"] == 137.0


def test_sentinel_values_are_refused_not_averaged() -> None:
    """A single -9999 would wreck any weighted mean it entered."""
    frame = pl.from_arrow(insitu.to_samples(hauls(sst="-9999", sbt="8.1"), "fishglob"))
    assert isinstance(frame, pl.DataFrame)
    assert frame["variable"].to_list() == ["sea_bottom_temperature"]


def test_unparseable_text_is_dropped_rather_than_zeroed() -> None:
    frame = pl.from_arrow(insitu.to_samples(hauls(sst="n/a"), "fishglob"))
    assert isinstance(frame, pl.DataFrame)
    assert "sea_surface_temperature" not in frame["variable"].to_list()


def test_the_table_matches_its_schema() -> None:
    table = insitu.to_samples(hauls(), "fishglob")
    assert table.schema.equals(DRIVER_SAMPLES.schema)
    DRIVER_SAMPLES.validate(table)


def test_the_spec_refuses_a_wrong_type() -> None:
    """Checks rather than casts, exactly as the evidence specs do."""
    table = insitu.to_samples(hauls(), "fishglob")
    broken = table.set_column(
        table.schema.get_field_index("value"),
        "value",
        table.column("value").cast("float32"),
    )
    with pytest.raises(ValueError, match="has type float"):
        DRIVER_SAMPLES.validate(broken)


# --- The reason the table is shaped this way --------------------------------
def test_a_driver_can_be_another_taxons_index() -> None:
    """The trophic pathway made concrete.

    Warmer water pushes plankton deeper, forage fish leave, a seabird has nothing to eat. The
    driver of the bird's movement is a fish abundance, and the schema has to be able to say so --
    with `derived_from` recording where it came from, so a pathway is traceable rather than
    asserted.
    """
    derived = pl.DataFrame(
        {
            "source_id": ["fishglob"],
            "site_id": ["NEUS-Fall:h1"],
            "period_start": [datetime(2015, 9, 1, tzinfo=UTC)],
            "longitude": [-70.5],
            "latitude": [42.5],
            "depth_m": [None],
            "variable": ["forage_fish_cpue"],
            "value": [3.4],
            "unit": ["num_per_km2"],
            "kind": [DriverKind.DERIVED.value],
            "derived_from": ["fishglob:Ammodytes dubius"],
        },
        schema_overrides={"depth_m": pl.Float64},
    )
    table = derived.select(DRIVER_SAMPLES.schema.names).to_arrow().cast(DRIVER_SAMPLES.schema)
    DRIVER_SAMPLES.validate(table)
    assert table.column("derived_from").to_pylist() == ["fishglob:Ammodytes dubius"]


def test_the_three_kinds_are_distinguishable() -> None:
    """An in-situ reading, a raster sample and a derived index are three different things.

    Mixing them in one regression without saying so turns its residuals into a story about
    interpolation, or about our own aggregation choices.
    """
    assert len({DriverKind.MEASURED, DriverKind.GRIDDED, DriverKind.DERIVED}) == 3
