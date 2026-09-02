"""Phase 3k's two decompositions, on panels whose answer is built in.

Estimand A is a weighted fit with a residual heterogeneity; estimand B is a coherence under two
groupings with two bootstraps. Both are testable without a lake, and both have a failure mode that
would look like a result: a residual Q against the wrong bar, or a clustered interval that comes out
narrower than a naive one because nothing in the panel varied between surveys.
"""

import numpy as np
import polars as pl
import pytest
from scipy import stats

from migratlas.reports import phase3k


def _units(
    *, drift_effect: float, warming_effect: float = 0.0, n: int = 18
) -> list[phase3k.DriftUnit]:
    """Eighteen units whose latitude trend is a known multiple of their sampling drift."""
    rng = np.random.default_rng(3)
    out = []
    for index in range(n):
        drift = float(rng.normal(0.0, 0.15))
        warming = float(rng.normal(0.3, 0.1))
        out.append(
            phase3k.DriftUnit(
                survey=f"S{index:02d}",
                latitude_trend=(
                    drift_effect * drift + warming_effect * warming + float(rng.normal(0, 0.02))
                ),
                latitude_ci=0.05,
                warming_trend=warming,
                sampling_drift=drift,
                years=25,
            )
        )
    return out


def test_solve_recovers_a_known_drift_slope_and_a_null_warming() -> None:
    units = _units(drift_effect=0.5)
    drift, drift_ci, warming, warming_ci, _, _ = phase3k.solve(units)

    assert drift == pytest.approx(0.5, abs=0.1), drift
    assert drift - drift_ci > 0
    assert abs(warming) < warming_ci, (warming, warming_ci)


def test_the_residual_q_is_smaller_than_the_plain_q_and_uses_fewer_degrees_of_freedom() -> None:
    units = _units(drift_effect=0.5)
    *_, residual_q, bar = phase3k.solve(units)

    y = np.array([u.latitude_trend for u in units])
    weights = np.array([1.0 / (u.latitude_ci / 1.96) ** 2 for u in units])
    pooled = float(np.sum(weights * y) / np.sum(weights))
    plain_q = float(np.sum(weights * (y - pooled) ** 2))

    assert residual_q < plain_q
    assert bar == pytest.approx(stats.chi2.ppf(0.95, len(units) - phase3k.PARAMETERS))


def test_fit_drift_carries_leverage_on_both_coefficients() -> None:
    fit = phase3k.fit_drift(_units(drift_effect=0.5))
    assert fit is not None
    assert fit.drift_leverage is not None
    assert fit.warming_leverage is not None
    assert fit.drift_leverage.units == 18
    assert fit.drift_positive
    assert not fit.warming_clears


def test_fit_drift_refuses_a_panel_too_small_for_three_parameters() -> None:
    assert phase3k.fit_drift(_units(drift_effect=0.5, n=4)) is None


def _pairs(
    *,
    species_effect: float,
    survey_effect: float,
    surveys: int = 12,
    taxa: int = 40,
    noise: float = 0.02,
) -> pl.DataFrame:
    """Every taxon in every survey, with a tendency per taxon and a tendency per survey.

    `noise` is scatter that belongs to neither grouping. Left at the stated standard error it is
    all estimation error and the corrected coherence has nothing to apportion; the chance-level
    tests raise it so that there is real spread for a shuffled grouping to claim a share of.
    """
    rng = np.random.default_rng(7)
    species = rng.normal(0.0, species_effect, size=taxa) if species_effect else np.zeros(taxa)
    seas = rng.normal(0.0, survey_effect, size=surveys) if survey_effect else np.zeros(surveys)
    rows: list[dict[str, object]] = []
    for s in range(surveys):
        for t in range(taxa):
            rows.append(
                {
                    "per_decade": float(species[t] + seas[s] + rng.normal(0.0, noise)),
                    "stderr": 0.02,
                    "taxon_key": 1000 + t,
                    "survey_unit": f"S{s:02d}",
                }
            )
    return pl.DataFrame(rows)


def test_shared_panel_keeps_only_taxa_in_five_or_more_surveys() -> None:
    pooled = _pairs(species_effect=0.1, survey_effect=0.0, surveys=6, taxa=5)
    # One taxon appears in only four surveys once two of its rows are removed.
    thinned = pooled.filter(
        ~((pl.col("taxon_key") == 1000) & pl.col("survey_unit").is_in(["S00", "S01"]))
    )
    table = phase3k.shared_panel(thinned)
    assert 1000 not in table["species"].cast(pl.Int64).to_list()
    assert table["species"].n_unique() == 4


def test_species_coherence_leads_when_the_tendency_travels_with_the_animal() -> None:
    fit = phase3k.fit_species(_pairs(species_effect=0.2, survey_effect=0.0), draws=100)
    assert fit is not None
    assert fit.by_species.corrected > phase3k.COHERENCE_FLOOR
    assert fit.by_species.corrected > fit.by_survey.corrected
    assert fit.species_leads


def test_survey_coherence_leads_when_the_tendency_belongs_to_the_sea() -> None:
    fit = phase3k.fit_species(_pairs(species_effect=0.0, survey_effect=0.2), draws=100)
    assert fit is not None
    assert fit.by_survey.corrected > fit.by_species.corrected
    assert not fit.species_leads


def test_a_survey_clustered_interval_is_wider_where_surveys_differ() -> None:
    """The lesson Phase 3j paid for: clustering is only wider *because* the surveys disagree."""
    table = phase3k.shared_panel(_pairs(species_effect=0.1, survey_effect=0.2))
    naive = phase3k.bootstrap(table, phase3k.SPECIES, clustered=False, draws=100)
    clustered = phase3k.bootstrap(table, phase3k.SPECIES, clustered=True, draws=100)
    assert clustered[1] - clustered[0] > naive[1] - naive[0]


def test_chance_level_rises_with_the_number_of_groups() -> None:
    """The reason a fixed coherence floor is not one bar.

    With the labels shuffled, a grouping into many small groups scores higher than a grouping
    into few large ones -- a one-way R-squared with k groups over n rows expects about (k-1)/n
    under the null. The permutation and the closed form should agree on that ordering.
    """
    table = phase3k.shared_panel(_pairs(species_effect=0.0, survey_effect=0.0, noise=0.1))
    many = phase3k.chance_level(table, phase3k.SPECIES, draws=100)
    few = phase3k.chance_level(table, phase3k.SURVEY, draws=100)

    assert many.null_median > few.null_median
    assert many.closed_form > few.closed_form
    assert many.null_median == pytest.approx(many.closed_form, abs=0.05)


def test_a_real_species_tendency_beats_its_chance_level() -> None:
    table = phase3k.shared_panel(_pairs(species_effect=0.2, survey_effect=0.0, noise=0.1))
    chance = phase3k.chance_level(table, phase3k.SPECIES, draws=100)
    assert chance.beats_chance
    assert chance.excess > 0.3


def test_no_tendency_stays_inside_its_chance_level() -> None:
    table = phase3k.shared_panel(_pairs(species_effect=0.0, survey_effect=0.0, noise=0.1))
    chance = phase3k.chance_level(table, phase3k.SPECIES, draws=100)
    assert not chance.beats_chance


def test_a_panel_that_is_all_estimation_error_has_no_chance_level() -> None:
    """`_icc` returns NaN where there is no corrected variance, and the diagnostic must say so."""
    table = phase3k.shared_panel(_pairs(species_effect=0.0, survey_effect=0.0))
    chance = phase3k.chance_level(table, phase3k.SPECIES, draws=20)
    assert not np.isfinite(chance.null_median)
    assert not chance.beats_chance


def test_a_bootstrap_is_a_property_of_its_quantity() -> None:
    """Two runs, one seed, one answer.

    To the last bit but one: polars does not fix a group_by's row order, so `_icc` sums the same
    group means in a different order on each call and the two values differ at 1e-16. A test that
    demanded exact equality here failed on that and would have been a test of polars, not of the
    seeding.
    """
    table = phase3k.shared_panel(_pairs(species_effect=0.1, survey_effect=0.1))
    first = phase3k.bootstrap(table, phase3k.SPECIES, clustered=True, draws=50)
    second = phase3k.bootstrap(table, phase3k.SPECIES, clustered=True, draws=50)
    assert first == pytest.approx(second, abs=1e-12)
