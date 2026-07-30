"""The DAMIP fraction, on simulations whose warming rates were planted.

A fraction is a ratio of two fitted trends across a nested ensemble, and every step -- averaging
members before models, dropping a model whose own warming vanishes, taking the ratio on the ensemble
means rather than on each model -- changes the answer without changing its plausibility. So each
case here plants the trends and asserts the arithmetic that must follow.
"""

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from migratlas.drivers import cmip6
from migratlas.features.annotate import Point
from migratlas.reports import phase2a_attribution as attribution
from migratlas.reports.phase2a_timing import Sensitivity

YEARS = range(1980, 2015)

STATIONS = (("KAAA", 42.0), ("KBBB", 44.0))
"""Both inside the 37-50N claim band."""


def _simulated(
    plan: dict[tuple[str, str, str], float], *, latitude: float | None = None
) -> pl.DataFrame:
    """One row per simulation-station-year, warming at the rate the plan names.

    Keys are (experiment, model, member); values are degC per year.
    """
    rows = []
    for (experiment, model, member), per_year in plan.items():
        for station, station_latitude in STATIONS:
            for offset, year in enumerate(YEARS):
                rows.append(
                    {
                        "station_id": station,
                        "latitude": latitude if latitude is not None else station_latitude,
                        "year": year,
                        "experiment": experiment,
                        "model": model,
                        "member": member,
                        "value": 10.0 + per_year * offset,
                    }
                )
    return pl.DataFrame(rows)


WINDOW = (1980, 2014)


def test_trend_recovers_the_planted_rate() -> None:
    frame = _simulated({("historical", "M", "r1"): 0.03})
    (fitted,) = attribution.trends(frame, WINDOW)
    assert fitted.per_decade == pytest.approx(0.3)
    assert fitted.stations == len(STATIONS)


def test_fraction_is_one_when_the_counterfactual_is_flat() -> None:
    frame = _simulated({("historical", "M", "r1"): 0.03, ("hist-nat", "M", "r1"): 0.0})
    found = attribution.fraction(frame, WINDOW)
    assert found is not None
    assert found.ensemble == pytest.approx(1.0)
    assert found.per_model == pytest.approx([1.0])


def test_fraction_is_zero_when_the_counterfactual_warms_as_much() -> None:
    """No human share to find: the two experiments do the same thing."""
    frame = _simulated({("historical", "M", "r1"): 0.03, ("hist-nat", "M", "r1"): 0.03})
    found = attribution.fraction(frame, WINDOW)
    assert found is not None
    assert found.ensemble == pytest.approx(0.0)


def test_fraction_is_half_when_the_counterfactual_warms_half_as_much() -> None:
    frame = _simulated({("historical", "M", "r1"): 0.04, ("hist-nat", "M", "r1"): 0.02})
    found = attribution.fraction(frame, WINDOW)
    assert found is not None
    assert found.ensemble == pytest.approx(0.5)


def test_members_are_averaged_before_models() -> None:
    """The whole reason the ensemble is nested.

    One model brings three members warming at 0.01, another brings one at 0.05. Pooling members
    would weight the first model three times and give 0.02; averaging members first gives 0.03.
    """
    plan = {
        ("historical", "MANY", "r1"): 0.01,
        ("historical", "MANY", "r2"): 0.01,
        ("historical", "MANY", "r3"): 0.01,
        ("historical", "ONE", "r1"): 0.05,
    }
    plan |= {("hist-nat", model, member): 0.0 for _, model, member in plan}
    found = attribution.fraction(_simulated(plan), WINDOW)
    assert found is not None
    assert found.models == 2
    assert found.historical == pytest.approx(0.3)


def test_a_model_without_both_experiments_is_dropped() -> None:
    plan = {
        ("historical", "PAIRED", "r1"): 0.03,
        ("hist-nat", "PAIRED", "r1"): 0.0,
        ("historical", "LONELY", "r1"): 0.9,
    }
    found = attribution.fraction(_simulated(plan), WINDOW)
    assert found is not None
    assert found.models == 1
    assert found.historical == pytest.approx(0.3)


def test_a_model_that_barely_warms_leaves_the_per_model_spread_but_is_counted() -> None:
    """Its ratio would be arbitrary in size and sign, so it must not enter the spread."""
    plan = {
        ("historical", "WARM", "r1"): 0.03,
        ("hist-nat", "WARM", "r1"): 0.0,
        ("historical", "FLAT", "r1"): 0.0001,
        ("hist-nat", "FLAT", "r1"): -0.002,
    }
    found = attribution.fraction(_simulated(plan), WINDOW)
    assert found is not None
    assert found.models == 2
    assert found.dropped == 1
    assert found.per_model == pytest.approx([1.0])
    # The headline ratio still uses both, because its denominator is the ensemble's warming.
    assert np.isfinite(found.ensemble)


def test_stations_outside_the_claim_band_are_excluded() -> None:
    frame = _simulated({("historical", "M", "r1"): 0.03}, latitude=25.0)
    assert attribution.trends(frame, WINDOW) == []
    assert attribution.fraction(frame, WINDOW) is None


def test_a_short_series_is_refused() -> None:
    frame = _simulated({("historical", "M", "r1"): 0.03}).filter(pl.col("year") < 1990)
    assert attribution.trends(frame, WINDOW) == []


def test_the_window_bounds_which_years_are_fitted() -> None:
    """A series that only warms after 2000 shows nothing in a window that ends before it."""
    frame = _simulated({("historical", "M", "r1"): 0.0}).with_columns(
        value=pl.when(pl.col("year") >= 2000)
        .then(10.0 + (pl.col("year") - 2000) * 0.1)
        .otherwise(10.0)
    )
    (early,) = attribution.trends(frame, (1980, 1999))
    (late,) = attribution.trends(frame, (2000, 2014))
    assert early.per_decade == pytest.approx(0.0)
    assert late.per_decade == pytest.approx(1.0)


def test_spread_reports_the_extremes_and_survives_an_empty_ensemble() -> None:
    plan = {
        ("historical", "A", "r1"): 0.04,
        ("hist-nat", "A", "r1"): 0.0,
        ("historical", "B", "r1"): 0.04,
        ("hist-nat", "B", "r1"): 0.02,
    }
    found = attribution.fraction(_simulated(plan), WINDOW)
    assert found is not None
    low, high = found.spread
    assert (low, high) == pytest.approx((0.5, 1.0))

    empty = attribution.Fraction(
        window=WINDOW,
        models=0,
        historical=float("nan"),
        historical_ci=float("nan"),
        natural=float("nan"),
        natural_ci=float("nan"),
        ensemble=float("nan"),
        per_model=[],
        dropped=0,
    )
    assert all(np.isnan(value) for value in empty.spread)


def test_shortfall_names_the_models_that_failed_to_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """The guard that would have caught nine models vanishing on a calendar decode error."""
    offered = [
        cmip6.Store(experiment, model, "r1", f"gs://{model}")
        for experiment in cmip6.EXPERIMENTS
        for model in ("LANDED", "LOST", "ALSO-LOST")
    ]
    monkeypatch.setattr(cmip6, "catalogue", pl.DataFrame)
    monkeypatch.setattr(cmip6, "stores", lambda _: offered)

    landed = pl.DataFrame({"model": ["LANDED", "LANDED"]})
    assert attribution.shortfall(landed) == ["ALSO-LOST", "LOST"]
    assert attribution.shortfall(pl.DataFrame({"model": [m for _, m, _, _ in offered]})) == []


def test_the_attribution_scales_the_published_s_times_w_not_a_product_of_means(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S x W is averaged per station, and the product of the two band means is a different number.

    Planted so the two disagree: one station is sensitive and barely warming, the other the reverse.
    Per station the average is (-2*0.1 + -0.1*2)/2 = -0.2; the product of means is -1.05*1.05 =
    -1.1. `phase2a-timing.md` published the first, so the attribution has to scale the first.
    """
    planted = [
        Sensitivity("KAAA", 42.0, 0.0, -2.0, 0.0, 0.1, -1.0, 20),
        Sensitivity("KBBB", 44.0, 0.0, -0.1, 0.0, 2.0, -1.0, 20),
    ]
    monkeypatch.setattr(attribution, "sensitivities", lambda: planted)

    seen = attribution.observed()
    assert seen is not None
    assert seen.explained == pytest.approx(-0.2)
    assert seen.sensitivity * seen.warming == pytest.approx(-1.1025)


def test_the_synthetic_null_finds_no_difference_when_members_agree() -> None:
    """Two halves of one experiment differ only by initial condition, so the difference is zero."""
    plan = {
        ("hist-nat", "M", "r1"): 0.02,
        ("hist-nat", "M", "r2"): 0.02,
        ("hist-nat", "M", "r3"): 0.02,
        ("historical", "M", "r1"): 0.05,
    }
    found = attribution.placebo(_simulated(plan), WINDOW)
    assert found is not None
    assert found.difference == pytest.approx(0.0)


def test_the_synthetic_null_is_read_as_a_difference_because_its_ratio_is_meaningless() -> None:
    """Its denominator is a near-zero warming by construction, so the fraction explodes.

    That is what the first version of this control got wrong: it compared the null's *fraction*
    against zero and read +8.67 as the method being broken, when the difference was 3% of the
    forced one. The difference is the statistic; the ratio here is an artefact of dividing by
    almost nothing.
    """
    plan = {
        # r1 becomes the pseudo-historical side and barely warms, so it is the denominator.
        ("hist-nat", "M", "r1"): 0.00001,
        ("hist-nat", "M", "r2"): 0.002,
        ("hist-nat", "M", "r3"): 0.002,
    }
    found = attribution.placebo(_simulated(plan), WINDOW)
    assert found is not None
    assert found.difference == pytest.approx(-0.0199)
    assert abs(found.ensemble) > 100.0


def test_the_synthetic_null_would_catch_a_difference_manufactured_from_spread() -> None:
    """If members disagreed as much as the experiments do, the null would report it."""
    plan = {
        ("hist-nat", "M", "r1"): 0.04,
        ("hist-nat", "M", "r2"): 0.0,
        ("hist-nat", "M", "r3"): 0.0,
    }
    found = attribution.placebo(_simulated(plan), WINDOW)
    assert found is not None
    assert found.difference == pytest.approx(0.4)


def test_a_fraction_above_one_is_counted_rather_than_treated_as_an_error() -> None:
    """A counterfactual that cools is physical: aerosols and volcanoes without greenhouse gases."""
    plan = {
        ("historical", "COOLS", "r1"): 0.03,
        ("hist-nat", "COOLS", "r1"): -0.01,
        ("historical", "WARMS", "r1"): 0.03,
        ("hist-nat", "WARMS", "r1"): 0.01,
    }
    found = attribution.fraction(_simulated(plan), WINDOW)
    assert found is not None
    assert found.above_one == 1
    assert max(found.per_model) > 1.0


def test_the_synthetic_null_ignores_the_real_historical_runs() -> None:
    """It must not accidentally compare against the forced experiment, which is the whole point."""
    plan = {
        ("hist-nat", "M", "r1"): 0.02,
        ("hist-nat", "M", "r2"): 0.02,
        ("historical", "M", "r1"): 0.9,
        ("historical", "M", "r2"): 0.9,
    }
    found = attribution.placebo(_simulated(plan), WINDOW)
    assert found is not None
    assert found.historical == pytest.approx(0.2)
    assert found.natural == pytest.approx(0.2)


def test_the_windows_the_report_uses_end_where_historical_does() -> None:
    """The window problem the method note names: `historical` stops in 2014, so the windows do."""
    assert all(end == cmip6.COMMON_END for _, end in attribution.WINDOWS)
    assert cmip6.COMMON_END == 2014


@pytest.mark.parametrize("calendar", ["360_day", "365_day", "standard"])
def test_a_store_is_read_whatever_calendar_it_uses(tmp_path: Path, calendar: str) -> None:
    """Climate models do not all use a real calendar, and the difference is not cosmetic.

    In HadGEM3's 360-day calendar every month has thirty days, so a slice bound of 31 December
    raises instead of clamping -- and because an unreadable store is only logged, that cost the
    model its place in the ensemble with no symptom but a smaller model count.
    """
    xr = pytest.importorskip("xarray")
    pytest.importorskip("cftime")

    time = xr.date_range("1995-01-01", "2014-12-01", freq="MS", calendar=calendar, use_cftime=True)
    grid = {"lat": [40.0, 44.0], "lon": [285.0, 289.0]}
    values = np.full((time.size, 2, 2), 283.15)
    store = tmp_path / f"{calendar}.zarr"
    xr.Dataset(
        {cmip6.VARIABLE: (("time", "lat", "lon"), values)},
        coords={"time": time, **grid},
        # v2 because that is what the Pangeo CMIP6 mirror publishes, so the fixture exercises the
        # same reader path. v3 also warns about consolidated metadata, which pytest treats as error.
    ).to_zarr(store, zarr_format=2)

    frame = cmip6.pre_season(
        cmip6.Store("historical", "M", "r1", str(store)),
        [Point(site_id="KAAA", longitude=-73.0, latitude=42.0)],
    )
    assert frame.height == 20
    assert frame["value"].to_list() == pytest.approx([10.0] * 20)


def test_the_pinatubo_control_window_starts_earlier_than_the_radar() -> None:
    starts = [start for start, _ in attribution.WINDOWS]
    assert min(starts) < 1991 < max(starts)


def test_derived_from_carries_the_experiment_model_and_member() -> None:
    """`simulated()` splits derived_from on ':' by position, so the format is load-bearing."""
    frame = pl.DataFrame(
        {
            "site_id": ["KAAA"],
            "year": [2000],
            "value": [10.0],
            "longitude": [-75.0],
            "latitude": [42.0],
            "experiment": ["hist-nat"],
            "model": ["MIROC6"],
            "member": ["r3i1p1f1"],
        }
    )
    table = cmip6.to_samples(frame)
    assert table.column("derived_from").to_pylist() == ["cmip6:hist-nat:MIROC6:r3i1p1f1"]
    assert table.column("variable").to_pylist() == ["air_temperature_2m_junjul_hist-nat"]
    assert table.column("kind").to_pylist() == ["simulated"]


def test_the_counterfactual_is_never_filed_as_an_observation() -> None:
    """The reason DriverKind gained a fourth member. A hist-nat temperature did not happen."""
    frame = pl.DataFrame(
        {
            "site_id": ["KAAA", "KAAA"],
            "year": [2000, 2000],
            "value": [10.0, 9.0],
            "longitude": [-75.0, -75.0],
            "latitude": [42.0, 42.0],
            "experiment": ["historical", "hist-nat"],
            "model": ["M", "M"],
            "member": ["r1", "r1"],
        }
    )
    kinds = set(cmip6.to_samples(frame).column("kind").to_pylist())
    assert kinds == {"simulated"}


def test_stores_pairs_experiments_and_caps_members() -> None:
    rows = []
    for experiment, activity in cmip6.EXPERIMENTS.items():
        for model, members in (("PAIRED", 5), ("LONELY", 2)):
            if model == "LONELY" and experiment == "hist-nat":
                continue
            for index in range(members):
                rows.append(
                    {
                        "activity_id": activity,
                        "experiment_id": experiment,
                        "table_id": cmip6.TABLE,
                        "variable_id": cmip6.VARIABLE,
                        "source_id": model,
                        "member_id": f"r{index}i1p1f1",
                        "zstore": f"gs://{model}/{experiment}/{index}",
                    }
                )
    found = cmip6.stores(pl.DataFrame(rows))

    assert {store.model for store in found} == {"PAIRED"}
    for experiment in cmip6.EXPERIMENTS:
        kept = [store.member for store in found if store.experiment == experiment]
        assert len(kept) == cmip6.MAX_MEMBERS
        assert len(set(kept)) == cmip6.MAX_MEMBERS


def test_duplicate_versions_of_one_member_count_once() -> None:
    """A model can publish the same member twice; taking both would double-weight it."""
    rows = []
    for experiment, activity in cmip6.EXPERIMENTS.items():
        for version in ("v20190101", "v20200202"):
            rows.append(
                {
                    "activity_id": activity,
                    "experiment_id": experiment,
                    "table_id": cmip6.TABLE,
                    "variable_id": cmip6.VARIABLE,
                    "source_id": "M",
                    "member_id": "r1i1p1f1",
                    "zstore": f"gs://M/{experiment}/{version}",
                }
            )
    found = cmip6.stores(pl.DataFrame(rows))
    assert len(found) == len(cmip6.EXPERIMENTS)


def test_the_box_covers_every_station_in_model_longitude() -> None:
    points = [
        Point(site_id="W", longitude=-124.0, latitude=37.5),
        Point(site_id="E", longitude=-70.0, latitude=48.0),
    ]
    latitudes, longitudes = cmip6._box(points)
    assert latitudes.start < min(point.latitude for point in points)
    assert latitudes.stop > max(point.latitude for point in points)
    assert longitudes.start < min(point.longitude % 360 for point in points)
    assert longitudes.stop > max(point.longitude % 360 for point in points)
