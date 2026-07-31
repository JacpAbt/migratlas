"""The ISIMIP3a driver, and the two mistakes here that would not announce themselves.

Labelling the counterfactual as factual is the one error here that no downstream check would catch:
every number would be plausible, the units right, the dates right, and the attribution computed
against a climate that did happen. So the scenario is read off the filename rather than off position
in a list, and that is what most of these assert.

The other is a window mistake. `counterclim` ends in 2019 and the radar record runs to 2025, so a
request that quietly returns fewer years than asked for would shrink the claim without saying so.
"""

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from migratlas.catalog import loader
from migratlas.drivers import attrici
from migratlas.drivers.schema import DriverKind


def test_the_source_is_registered_with_both_halves_of_the_pair() -> None:
    source = loader.get(attrici.SOURCE_ID)
    assert source.redistribution.allowed, "a driver we cannot republish is not worth a panel"
    # No animal in it, and for the counterfactual no place either.
    assert source.evidence_type is None
    assert source.taxon_scope is None


def test_the_factual_half_is_gridded_and_the_counterfactual_is_simulated() -> None:
    """The distinction the DriverKind enum exists for, applied to the one case that tests it.

    `obsclim` is an estimate of what the atmosphere did. `counterclim` is what it would have done
    without the warming -- a climate that never happened, though no climate model made it. Filing
    the second as GRIDDED would put an observation and a counterfactual in one bucket.
    """
    assert attrici.SCENARIOS["obsclim"].kind is DriverKind.GRIDDED
    assert attrici.SCENARIOS["counterclim"].kind is DriverKind.SIMULATED


def test_the_two_climates_get_different_variable_names() -> None:
    """So "which climate is this" is a join condition, not a string match on free text.

    DRIVER_SAMPLES has no scenario column. The alternative was filtering `derived_from`, which is
    prose and would break the first time someone reworded it.
    """
    names = {scenario.canonical for scenario in attrici.SCENARIOS.values()}
    assert len(names) == 2, names
    assert "air_temperature_2m" in names, "the factual half must keep the canonical name"


def test_only_the_decade_files_that_cover_the_request_are_asked_for() -> None:
    spans = attrici.spans_for([1995, 1996, 2019])
    assert [span[0] for span in spans] == ["1991_2000", "2011_2019"]
    # Not the eight decades before 1991, which would be 300 MB of the 1900s for nothing.
    assert all(span[2] >= 1991 for span in spans)


def test_a_request_past_the_counterfactual_refuses_rather_than_returning_less() -> None:
    """The window mistake, made loud.

    `counterclim` ends in 2019. A request for 2020-2025 returning an empty frame would shrink the
    claim's window silently -- the same failure `phase2a-attribution.md` records for the nine CMIP6
    models that vanished without complaint.
    """
    with pytest.raises(attrici.RetrievalError, match=str(attrici.LAST_YEAR)):
        attrici.paths_for([2020, 2021], ("counterclim",))


def test_the_paths_name_the_scenario_they_carry() -> None:
    paths = attrici.paths_for([1995], ("obsclim", "counterclim"))
    assert len(paths) == 2
    assert sum("_obsclim_" in path for path in paths) == 1
    assert sum("_counterclim_" in path for path in paths) == 1
    # The scenario appears in the directory *and* the filename, and the ingest matches on the
    # filename because that is what ISIMIP names its output after.
    for path in paths:
        scenario = "counterclim" if "counterclim" in path else "obsclim"
        assert Path(path).name.count(scenario) == 1


def test_the_bounding_box_is_the_order_cdo_takes() -> None:
    """West, east, south, north. Passing a point as [lon, lat] is what the API rejects loudly."""
    west, east, south, north = attrici.CONUS_BBOX
    assert west < east
    assert south < north
    assert -180 <= west <= 180
    assert -90 <= south <= 90
    # The same box era5 samples, so the two driver panels describe the same footprint.
    from migratlas.drivers.era5 import CONUS_AREA  # noqa: PLC0415

    era5_north, era5_west, era5_south, era5_east = CONUS_AREA
    assert (west, east, south, north) == (era5_west, era5_east, era5_south, era5_north)


def test_samples_land_in_celsius_with_the_scenario_recorded(tmp_path: Path) -> None:
    """Kelvin comes in and celsius goes out, converted at the boundary rather than downstream."""
    days = pl.DataFrame(
        {
            "site_id": ["KBGM", "KBGM"],
            # `datetime.date`, not `pl.date`: the latter builds an expression, and one of those in
            # a DataFrame literal gives an Object column that will not cast.
            "period_start": [date(2015, 6, 1), date(2015, 6, 2)],
            "longitude": [-75.98, -75.98],
            "latitude": [42.2, 42.2],
            "value": [18.5, 19.25],
        }
    )

    for name, scenario in attrici.SCENARIOS.items():
        table = attrici.to_samples(scenario, days)
        frame = pl.from_arrow(table)
        assert isinstance(frame, pl.DataFrame)
        assert frame.height == 2
        assert frame["unit"].unique().to_list() == ["degC"]
        assert frame["variable"].unique().to_list() == [scenario.canonical]
        assert frame["kind"].unique().to_list() == [scenario.kind.value]
        # `derived_from` names the scenario, so a row read on its own says which climate it is.
        assert name in frame["derived_from"][0]
        assert frame["source_id"].unique().to_list() == [attrici.SOURCE_ID]

    assert tmp_path.exists()


def test_asking_for_one_scenario_warns_that_nothing_can_check_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Not forbidden -- there are reasons to refetch one half -- but never silent.

    The factual half is the control that licenses the counterfactual. Landing a climate that never
    happened with nothing to compare it against is the shape of a mistake worth a line in the log.
    """
    import logging  # noqa: PLC0415

    # Fails at the network, which is fine: the warning is emitted before the request goes out.
    with (
        caplog.at_level(logging.WARNING, logger="migratlas.drivers.attrici"),
        pytest.raises(Exception, match=r".*"),
    ):
        attrici.ingest([], [1995], scenarios=("counterclim",), root=Path("/nonexistent"))

    assert any("cannot be validated" in record.message for record in caplog.records), (
        "requesting one half alone must say so"
    )
