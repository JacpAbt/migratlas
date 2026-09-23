"""Phase 3j's clustering, on panels whose answer is built in.

The phase asks whether a driver that shows nothing on average hit a subset. That is a claim about a
clustering, so the pieces that decide it are testable without a lake: a panel where one tercile
genuinely moved must show a spread that beats its null, and a panel where the labels mean nothing
must not.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.reports import phase3j
from migratlas.reports.phase1m import _icc


def _panel(
    *,
    spread: float,
    survey_spread: float = 0.0,
    surveys: int = 12,
    per_survey: int = 20,
) -> pl.DataFrame:
    """A pair-level panel with a known within-survey effect and a known between-survey one.

    `spread` moves the top third of *every* survey, which is what "the warming hit some and not
    others" looks like when the exposure varies inside a survey. `survey_spread` moves whole
    surveys against each other, which is what the real record has -- `seas-disagree` measures it at
    Cochran's Q 235.7 -- and it is the only thing a survey-clustered interval can be wider than a
    naive one *because of*. A panel without it makes clustering look free.
    """
    rng = np.random.default_rng(5)
    rows: list[dict[str, object]] = []
    for survey in range(surveys):
        for index in range(per_survey):
            position = index / (per_survey - 1)
            moved = spread if position > 2 / 3 else 0.0
            offset = survey_spread * (survey - surveys / 2) / surveys
            rows.append(
                {
                    "survey_unit": f"S{survey:02d}",
                    "taxon_label": f"taxon-{index}",
                    "slope": moved + offset + float(rng.normal(0.0, 0.05)),
                    "stderr": 0.05,
                    phase3j.THERMAL: position,
                    phase3j.WARMING: 0.1 + 0.01 * survey,
                    phase3j.DEPTH: 20.0 + 10.0 * survey,
                }
            )
    return pl.DataFrame(rows)


def test_terciles_split_by_rank_rather_than_by_spacing() -> None:
    """One huge value must not empty the middle group, which is what splitting on value would do."""
    index = phase3j._terciles(np.array([0.0, 1.0, 2.0, 3.0, 4.0, 900.0]))
    assert sorted(np.bincount(index, minlength=3).tolist()) == [2, 2, 2]


def test_a_real_subset_effect_beats_its_null() -> None:
    table = phase3j._assign(_panel(spread=0.5), phase3j.THERMAL, within_survey=True)
    observed = phase3j._spread(table)
    bar = phase3j._null_spread(table, phase3j.THERMAL, within_survey=True)

    assert observed == pytest.approx(0.5, abs=0.1), observed
    assert abs(observed) > bar, f"spread {observed:+.3f} inside a null bar of {bar:.3f}"


def test_no_subset_effect_stays_inside_its_null() -> None:
    table = phase3j._assign(_panel(spread=0.0), phase3j.THERMAL, within_survey=True)
    observed = phase3j._spread(table)
    bar = phase3j._null_spread(table, phase3j.THERMAL, within_survey=True)

    assert abs(observed) < bar, f"spread {observed:+.3f} beat a null bar of {bar:.3f}"


def test_a_within_survey_axis_puts_every_survey_in_every_tercile() -> None:
    table = phase3j._assign(_panel(spread=0.0), phase3j.THERMAL, within_survey=True)
    per_group = table.group_by("group").agg(pl.col("survey_unit").n_unique().alias("surveys"))
    assert per_group["surveys"].to_list() == [12, 12, 12]


def test_a_survey_level_axis_puts_each_survey_in_exactly_one_tercile() -> None:
    """Otherwise the axis would be splitting inside a survey on a value that cannot vary there."""
    table = phase3j._assign(_panel(spread=0.0), phase3j.WARMING, within_survey=False)
    per_survey = table.group_by("survey_unit").agg(pl.col("group").n_unique().alias("groups"))
    assert per_survey["groups"].to_list() == [1] * 12


def test_coherence_clears_its_floor_only_when_the_grouping_explains_something() -> None:
    """Phase 1m's lesson: the check that a group is not just a precise measurement of a mixture.

    Written against the floor rather than as `real > noise`, because a panel that is *only*
    estimation error has no corrected variance left to apportion and `_icc` says so by returning
    NaN -- and `NaN > NaN` is False, so the obvious comparison fails for the right reason and looks
    like the wrong one.
    """
    real = _icc(phase3j._assign(_panel(spread=0.5), phase3j.THERMAL, within_survey=True))[1]
    noise = _icc(phase3j._assign(_panel(spread=0.0), phase3j.THERMAL, within_survey=True))[1]

    assert real > phase3j.COHERENCE_FLOOR, real
    assert not (np.isfinite(noise) and noise > phase3j.COHERENCE_FLOOR), noise


def test_a_clustered_interval_is_wider_where_surveys_differ() -> None:
    """Pairs inside one survey share that survey's water, so resampling pairs admits too little.

    `survey_spread` is what makes this true and its absence is what makes it false: with every
    survey drawing slopes from one distribution, drawing whole surveys changes nothing and the
    clustered interval comes out *narrower*. Prediction 5 is justified for the real record because
    `seas-disagree` measured the surveys disagreeing at Q 235.7 against a bar of 27.6 -- not because
    clustering is wider as a matter of arithmetic.
    """
    table = phase3j._assign(
        _panel(spread=0.5, survey_spread=0.6), phase3j.WARMING, within_survey=False
    )
    naive = phase3j._interval(table, clustered=False, axis=phase3j.WARMING)
    clustered = phase3j._interval(table, clustered=True, axis=phase3j.WARMING)
    assert clustered > naive
