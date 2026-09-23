"""Phase 2c's arms, on series whose true response is known.

The phase exists because a within-station slope with no time term absorbs a shared trend. That is a
claim about an estimator, so it is testable without a lake: build a panel where passage has *no*
thermal response but both series trend, and the published specification should report one anyway
while the arm with a time term should not.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.constants import CLAIM_BAND
from migratlas.reports import phase2c

UNITS = 40
YEARS = 31
FIRST_YEAR = 1995


def _panel(
    *,
    thermal: float,
    passage_trend: float,
    warming: float = 0.05,
    gap: bool = False,
) -> pl.DataFrame:
    """A synthetic station panel with a known thermal response and a known secular trend.

    `thermal` is days per degree; `passage_trend` is days per year added on top of it. Temperature
    carries real interannual noise on purpose -- without it, year and temperature are collinear and
    the arm that adds a time term would be rank-deficient rather than informative.
    """
    rng = np.random.default_rng(11)
    rows: list[dict[str, object]] = []
    for unit in range(UNITS):
        offsets = [step for step in range(YEARS) if not (gap and step % 3 == 1)]
        for step in offsets:
            temperature = 10.0 + warming * step + float(rng.normal(0.0, 0.5))
            support = float(rng.normal(0.0, 1.0))
            rows.append(
                {
                    "station_id": f"K{unit:03d}",
                    "year": FIRST_YEAR + step,
                    "q50_doy": (
                        250.0
                        + passage_trend * step
                        + thermal * temperature
                        + 0.2 * support
                        + float(rng.normal(0.0, 1.0))
                    ),
                    "temperature": temperature,
                    "support": support,
                    "station_latitude": 40.0,
                    "station_longitude": -95.0,
                }
            )
    return pl.DataFrame(rows)


def _arm(frame: pl.DataFrame, arm: str) -> phase2c.ArmResult:
    fits = phase2c._fit_units(frame, unit_column="station_id", response="q50_doy", arm=arm)
    pooled = phase2c._pool(arm, "test", fits)
    assert pooled is not None, f"arm {arm} fitted nothing"
    return pooled


def test_the_published_specification_reports_a_response_that_is_not_there() -> None:
    """No thermal response, both series trending: arm A finds one and arm B does not.

    This is the phase's premise, and if it does not reproduce here the premise is wrong.
    """
    frame = _panel(thermal=0.0, passage_trend=-0.056)
    arm_a = _arm(frame, "A")
    arm_b = _arm(frame, "B")

    assert arm_a.clears_zero, arm_a
    assert arm_a.per_degree < -0.2, f"arm A absorbed no co-trend: {arm_a.per_degree:+.3f}"
    # Stated as a magnitude rather than as significance: the substantive claim is that the time
    # term recovers the absent response, and a significance assertion on a true null is a coin
    # flip dressed as a test.
    assert abs(arm_b.per_degree) < 0.15, f"arm B kept a response that is not there: {arm_b}"
    assert abs(arm_b.per_degree) < abs(arm_a.per_degree) / 2


def test_a_real_interannual_response_is_recovered_by_both_specifications() -> None:
    """With no secular trend to absorb, the time term costs precision and changes nothing else."""
    frame = _panel(thermal=-0.66, passage_trend=0.0)
    assert _arm(frame, "A").per_degree == pytest.approx(-0.66, abs=0.1)
    assert _arm(frame, "B").per_degree == pytest.approx(-0.66, abs=0.1)


def test_first_differences_recover_a_real_interannual_response() -> None:
    frame = _panel(thermal=-0.66, passage_trend=-0.056)
    assert _arm(frame, "C").per_degree == pytest.approx(-0.66, abs=0.15)


def test_first_differences_ignore_steps_that_span_a_gap() -> None:
    """A difference across a missing year is not a first difference, so it is not used."""
    frame = _panel(thermal=-0.66, passage_trend=0.0, gap=True)
    fits = phase2c._fit_units(frame, unit_column="station_id", response="q50_doy", arm="C")
    assert fits == [], "arm C used differences spanning a gap"
    assert phase2c._fit_units(frame, unit_column="station_id", response="q50_doy", arm="B")


def test_the_secular_pair_is_identical_across_arms() -> None:
    """Amendment D: only `s` changes between arms, so the shares are comparable."""
    frame = _panel(thermal=-0.66, passage_trend=-0.056)
    arm_a = _arm(frame, "A")
    arm_b = _arm(frame, "B")
    assert arm_a.warming == pytest.approx(arm_b.warming)
    assert arm_a.observed == pytest.approx(arm_b.observed)


def test_the_residual_and_the_share_are_the_decomposition() -> None:
    frame = _panel(thermal=-0.66, passage_trend=-0.056)
    arm_b = _arm(frame, "B")
    assert arm_b.explained + arm_b.residual == pytest.approx(arm_b.observed)
    assert arm_b.share == pytest.approx(arm_b.explained / arm_b.observed)


def test_the_claim_band_is_the_band_the_finding_is_published_over() -> None:
    frame = pl.DataFrame(
        {
            "station_latitude": [CLAIM_BAND[0] - 1.0, CLAIM_BAND[0], 45.0, float(CLAIM_BAND[1])],
            "station_id": ["a", "b", "c", "d"],
        }
    )
    assert phase2c.claim_band(frame)["station_id"].to_list() == ["b", "c"]
