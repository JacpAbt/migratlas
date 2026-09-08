"""Phase 2f's pieces, on panels whose answer is built in.

A within-site fit with several drivers, a leave-one-year-out error, and the improvement one arm
earns over another -- each testable without a lake, and each with a failure that would read as a
result: an added driver that improves nothing must show no gain, and one that matters must.
"""

import numpy as np
import pytest

from migratlas.reports import phase2f

SITES = 25
YEARS = 30


def _panel(
    *,
    temperature: float = -4.0,
    rain: float = 0.0,
    green: float = 0.0,
    shared_residual: float = 2.0,
    single_site: bool = False,
) -> phase2f.Panel:
    """Sites with their own intercepts and one national spring; a known response to each driver.

    `shared_residual` is a national year effect on the response that no driver explains. Over
    thirty years it correlates with a national driver by chance, and the driver's coefficient
    absorbs that -- which is the real record's problem too, and why the intervals are clustered on
    year. The recovery test switches it off to test the estimator; the interval tests keep it.
    """
    rng = np.random.default_rng(29)
    sites = 1 if single_site else SITES
    intercepts = rng.normal(150.0, 10.0, size=sites)
    national_t = rng.normal(0.0, 1.0, size=YEARS)
    national_p = rng.normal(0.0, 1.0, size=YEARS)
    national_g = rng.normal(0.0, 5.0, size=YEARS)
    year_effect = (
        rng.normal(0.0, shared_residual, size=YEARS) if shared_residual else np.zeros(YEARS)
    )
    site_col: list[int] = []
    year_col: list[int] = []
    y: list[float] = []
    t: list[float] = []
    p: list[float] = []
    g: list[float] = []
    r: list[float] = []
    for s in range(sites):
        for k in range(YEARS):
            tt = 10.0 + national_t[k] + rng.normal(0.0, 0.3)
            pp = 2.0 + national_p[k] + rng.normal(0.0, 0.3)
            gg = 100.0 + national_g[k] + rng.normal(0.0, 1.0)
            flight = (
                intercepts[s]
                + temperature * (tt - 10.0)
                + rain * (pp - 2.0)
                + green * (gg - 100.0)
                + year_effect[k]
                + rng.normal(0.0, 1.5)
            )
            site_col.append(s)
            year_col.append(1990 + k)
            y.append(float(flight))
            t.append(float(tt))
            p.append(float(pp))
            g.append(float(gg))
            r.append(150.0 + float(rng.normal(0.0, 5.0)))
    return phase2f.Panel(
        site=np.array(site_col, dtype=int),
        year=np.array(year_col, dtype=int),
        response=np.array(y),
        drivers={
            phase2f.T: np.array(t),
            phase2f.P: np.array(p),
            phase2f.G: np.array(g),
            phase2f.R: np.array(r),
        },
        fixed={},
    )


def test_the_fit_recovers_every_drivers_coefficient() -> None:
    panel = _panel(temperature=-4.0, rain=1.5, green=0.3, shared_residual=0.0)
    solution = phase2f.fit(panel, (phase2f.T, phase2f.P, phase2f.G))
    assert solution is not None
    assert solution[0] == pytest.approx(-4.0, abs=0.3)
    assert solution[1] == pytest.approx(1.5, abs=0.3)
    assert solution[2] == pytest.approx(0.3, abs=0.1)


def test_a_driver_that_matters_improves_the_held_out_error_and_one_that_does_not_does_not() -> None:
    panel = _panel(temperature=-4.0, rain=1.5)
    base = phase2f.held_out_rmse(panel, (phase2f.T,))
    with_rain = phase2f.held_out_rmse(panel, (phase2f.T, phase2f.P))
    with_green = phase2f.held_out_rmse(panel, (phase2f.T, phase2f.G))
    assert with_rain < base * 0.9, (base, with_rain)
    assert with_green == pytest.approx(base, rel=0.05), (base, with_green)


def test_unit_result_marks_the_added_driver_and_its_interval() -> None:
    panel = _panel(temperature=-4.0, rain=1.5)
    result = phase2f.unit_result(panel, phase2f.Key("u", "u"), phase2f.BUTTERFLY_SPEC, draws=60)
    assert result.arms["T"].added is None
    assert result.arms["TP"].added == phase2f.P
    assert result.arms["TP"].added_clear
    assert not result.arms["TG"].added_clear
    assert result.arms["all"].added is None
    assert result.improvement("TP") > 0.05


def test_a_single_site_unit_gets_an_ordinary_least_squares_interval() -> None:
    panel = _panel(temperature=-1.0, rain=2.0, shared_residual=0.0, single_site=True)
    result = phase2f.unit_result(panel, phase2f.Key("s", "s"), phase2f.RADAR_SPEC, draws=10)
    low, high = result.arms["TP"].added_interval
    assert np.isfinite(low)
    assert np.isfinite(high)
    assert result.arms["TP"].added_clear


def test_the_full_arm_is_the_records_own_drivers() -> None:
    """A radar station never carries R. The first run's shared arm all asked for it, and no station
    fitted a full model, so the radar's full-model gain came out NaN."""
    assert phase2f.RADAR_SPEC.drivers_of("all") == (phase2f.T, phase2f.P, phase2f.G)
    assert phase2f.BUTTERFLY_SPEC.drivers_of("all") == (
        phase2f.T,
        phase2f.P,
        phase2f.R,
        phase2f.G,
    )
    full = _panel(temperature=-1.0, rain=2.0, shared_residual=0.0, single_site=True)
    panel = phase2f.Panel(
        site=full.site,
        year=full.year,
        response=full.response,
        drivers={name: values for name, values in full.drivers.items() if name != phase2f.R},
        fixed={},
    )
    result = phase2f.unit_result(panel, phase2f.Key("s", "s"), phase2f.RADAR_SPEC, draws=10)
    assert "all" in result.arms
    assert np.isfinite(result.improvement("all"))


def test_the_green_up_cell_id_matches_the_drivers_own() -> None:
    assert phase2f._cell_of(51.7, -1.3) == "51.5,-1.5"
    assert phase2f._cell_of(42.0, -96.2) == "42.5,-96.5"


def test_a_record_pools_counts_against_the_chance_bar() -> None:
    spec = phase2f.Spec(
        name="t", arms=("T", "TP", "all"), target=-4.0, improvement_bar=0.1, clustered=True
    )
    units = [
        phase2f.unit_result(
            _panel(temperature=-4.0, rain=1.5), phase2f.Key(f"u{i}", f"u{i}"), spec, draws=30
        )
        for i in range(3)
    ]
    rec = phase2f.record(spec, units, calibration=-4.0, draws=30)
    assert rec.calibrated
    assert rec.drivers[0].driver == phase2f.P
    assert rec.drivers[0].clear == 3
    assert rec.drivers[0].median_improvement > 0.05
