"""Phase 3a's grading arithmetic, tested without touching the lake or the test era."""

from migratlas.models.skill import Skill
from migratlas.reports.phase3a import StationSkill, binomial_bar, verdicts


def _skill(score: float, *, significant: bool) -> Skill:
    return Skill(
        score=score,
        null_threshold=0.1,
        significant=significant,
        train_years=14,
        test_years=6,
        ridge_lambda=1.0,
    )


def _station(name: str, season: str, score: float, *, significant: bool) -> StationSkill:
    verdict = _skill(score, significant=significant)
    return StationSkill(
        station_id=name,
        season=season,
        years=20,
        full=verdict,
        weather_only=verdict,
        indices_only=verdict,
    )


def test_the_chance_bar_is_the_binomial_95th_percentile() -> None:
    # With 100 units at a 5% false-positive rate, chance alone reaches nine about once in
    # twenty maps; the bar must sit there, not at the mean of five.
    assert binomial_bar(100) == 9
    assert binomial_bar(20) == 3
    assert binomial_bar(0) == 0


def test_verdicts_count_significance_per_season() -> None:
    results = [
        _station("A", "spring", 0.4, significant=True),
        _station("B", "spring", 0.2, significant=True),
        _station("C", "spring", -0.1, significant=False),
        _station("D", "autumn", 0.0, significant=False),
    ]
    by_season = {v.season: v for v in verdicts(results)}
    assert by_season["spring"].stations == 3
    assert by_season["spring"].significant == 2
    assert by_season["spring"].median_skill == 0.2
    assert by_season["autumn"].significant == 0


def test_an_empty_season_reports_rather_than_crashes() -> None:
    only_spring = [_station("A", "spring", 0.3, significant=True)]
    by_season = {v.season: v for v in verdicts(only_spring)}
    assert by_season["autumn"].stations == 0
