"""Phase 1o's grouping rules, on panels whose answer is built in.

The registration named one way this phase could fail to answer its own question: a temperate
survey is mostly one order, and a grouping where one group holds the panel has almost no
between-group variance available to it whatever the taxonomy is worth. So a near-zero coherence
there means nothing, and the code has to know the difference between "low" and "unreadable".
"""

import numpy as np
import polars as pl

from migratlas.reports import phase1o


def _panel(sizes: dict[str, int], *, spread: float) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Slopes and a rank table where each family's mean is offset by `spread` times its index."""
    rng = np.random.default_rng(4)
    slopes: list[dict[str, object]] = []
    ranks: list[dict[str, object]] = []
    key = 0
    for index, (family, members) in enumerate(sizes.items()):
        for _ in range(members):
            key += 1
            slopes.append(
                {
                    "taxon_key": str(key),
                    "slope": spread * index + float(rng.normal(0.0, 0.05)),
                    "stderr": 0.05,
                }
            )
            ranks.append({"taxon_key": str(key), phase1o.FAMILY: family, phase1o.ORDER: "one"})
    return pl.DataFrame(slopes), pl.DataFrame(ranks)


def test_a_group_below_the_member_floor_is_dropped() -> None:
    slopes, ranks = _panel({"big": 10, "also-big": 10, "tiny": 2}, spread=0.4)
    result = phase1o._axis("test", slopes, ranks, phase1o.FAMILY)

    assert result is not None
    assert result.groups == 2, "the two-species family entered a grouping"
    assert result.dropped == 2


def test_one_group_holding_the_panel_is_unreadable_rather_than_low() -> None:
    """The registered guard. A coherence near zero here is arithmetic, not evidence."""
    slopes, ranks = _panel({"dominant": 90, "small": 10}, spread=0.0)
    result = phase1o._axis("test", slopes, ranks, phase1o.FAMILY)

    assert result is not None
    assert result.largest_share > phase1o.DOMINANT_SHARE
    assert not result.interpretable


def test_an_even_panel_is_readable() -> None:
    slopes, ranks = _panel({"a": 20, "b": 20, "c": 20}, spread=0.0)
    result = phase1o._axis("test", slopes, ranks, phase1o.FAMILY)

    assert result is not None
    assert result.interpretable, result.largest_share


def test_coherence_rises_when_families_genuinely_differ() -> None:
    """And clears the floor only then, which is the whole point of reporting it."""
    real = phase1o._axis("test", *_panel({"a": 20, "b": 20, "c": 20}, spread=0.4), phase1o.FAMILY)
    noise = phase1o._axis("test", *_panel({"a": 20, "b": 20, "c": 20}, spread=0.0), phase1o.FAMILY)

    assert real is not None
    assert noise is not None
    assert real.clears_floor, real.coherence_corrected
    assert not noise.clears_floor, noise.coherence_corrected
