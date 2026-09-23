"""Phase 2e's pieces, on panels whose answer is built in.

The index, the log trends, the within-survey rank correlation and the magnitude control are each
testable without a lake -- and the control is the one that matters: a panel where rarity inflates
both magnitudes must not read as abundance moving centroids.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.reports import phase2e


def test_the_index_divides_by_the_years_events_not_by_the_taxons_rows() -> None:
    """A year the survey worked and the species was scarce must divide by all the hauls."""
    restricted = pl.DataFrame(
        {
            "year": [2000, 2000, 2000, 2001, 2001],
            "site_id": ["h1", "h2", "h3", "h1", "h2"],
            "taxon_key": [1, 1, 2, 1, 2],
            "taxon_label": ["a", "a", "b", "a", "b"],
            "cpue": [2.0, 4.0, 1.0, 3.0, 1.0],
            "cell_longitude": [0.5, 1.5, 0.5, 0.5, 1.5],
            "cell_latitude": [50.5, 50.5, 51.5, 50.5, 51.5],
        }
    )
    index = phase2e.yearly_index(restricted, event_columns=["site_id"]).sort("taxon_key", "year")
    a = index.filter(pl.col("taxon_key") == 1)
    # 2000: (2 + 4) / 3 hauls; 2001: 3 / 2 hauls. Cells: 2 then 1.
    assert a["index"].to_list() == pytest.approx([2.0, 1.5])
    assert a["cells"].to_list() == [2, 1]


def test_log_trends_recover_a_known_decline() -> None:
    years = np.arange(1990, 2020)
    index = 100.0 * np.exp(-0.05 * (years - 1990))  # -5% a year, -0.5 per decade in the log
    cells = np.full(years.size, 20.0)
    per_taxon = pl.DataFrame(
        {
            "taxon_key": [7] * years.size,
            "taxon_label": ["t"] * years.size,
            "year": years,
            "index": index,
            "cells": cells,
        }
    )
    trends = phase2e.log_trends(per_taxon, min_years=15)
    assert trends.height == 1
    assert trends[phase2e.ABUNDANCE][0] == pytest.approx(-0.5, abs=1e-6)
    assert trends[phase2e.EXTENT][0] == pytest.approx(0.0, abs=1e-9)


def test_a_short_series_has_no_trend() -> None:
    per_taxon = pl.DataFrame(
        {
            "taxon_key": [1] * 5,
            "taxon_label": ["t"] * 5,
            "year": list(range(5)),
            "index": [1.0] * 5,
            "cells": [3] * 5,
        }
    )
    assert phase2e.log_trends(per_taxon, min_years=15).is_empty()


def _panel(
    *,
    magnitude_effect: float = 0.0,
    direction_effect: float = 0.0,
    rarity_effect: float = 0.0,
    surveys: int = 12,
    per_survey: int = 30,
) -> pl.DataFrame:
    """Species-survey pairs with a known link between numbers and shift.

    `magnitude_effect` makes |L| grow with |N|; `direction_effect` makes L grow with N;
    `rarity_effect` makes the noisiest L belong to the noisiest N -- the confound the control
    catches -- without any real link between the two.
    """
    rng = np.random.default_rng(23)
    rows: list[dict[str, object]] = []
    for s in range(surveys):
        for t in range(per_survey):
            n = float(rng.normal(0.0, 0.3))
            precision = float(rng.uniform(0.02, 0.2))
            noise = precision * (1.0 + rarity_effect * abs(n) / 0.3)
            shift = (
                direction_effect * n
                + magnitude_effect * abs(n) * float(rng.choice([-1.0, 1.0]))
                + float(rng.normal(0.0, noise))
            )
            rows.append(
                {
                    "survey_unit": f"S{s:02d}",
                    "taxon_key": str(1000 + t),
                    "taxon_label": f"taxon-{t}",
                    "slope": shift,
                    "stderr": noise,
                    phase2e.ABUNDANCE: n,
                    "abundance_se": 0.05,
                    phase2e.EXTENT: 0.5 * n + float(rng.normal(0.0, 0.05)),
                }
            )
    return phase2e._with_axes(pl.DataFrame(rows))


def test_extent_follows_abundance_where_it_is_built_to() -> None:
    result = phase2e.extent_follows(_panel(), draws=100)
    assert result.follows
    assert result.rho > 0.8


def test_a_real_magnitude_link_beats_its_null_and_its_control() -> None:
    result = phase2e.leg("t", _panel(magnitude_effect=0.4), draws=100)
    assert result is not None
    assert result.size.beats_null
    assert result.size_survives_control


def test_rarity_alone_does_not_pass_the_control() -> None:
    """Noisy species have inflated |L| and inflated |N| here with no real link; the precision axis
    must carry as much spread as the abundance axis, and the magnitude must not count."""
    table = _panel(rarity_effect=6.0)
    result = phase2e.leg("t", table, draws=100)
    assert result is not None
    assert not result.size_survives_control


def test_a_direction_link_is_read_on_the_signed_axis() -> None:
    result = phase2e.leg("t", _panel(direction_effect=0.8), draws=100)
    assert result is not None
    assert result.direction_follows


def test_no_link_stays_inside_both_nulls() -> None:
    result = phase2e.leg("t", _panel(), draws=100)
    assert result is not None
    assert not result.size.beats_null
    assert not result.direction_follows
