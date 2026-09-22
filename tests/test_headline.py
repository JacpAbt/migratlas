"""The headline charts' arithmetic, and the one promise the document makes to the book.

The values themselves come from the analyses and are tested where those are. What can go wrong
here is the drawing's own arithmetic -- a trend anchored off the middle of its points, a histogram
whose bars miss a value or straddle zero -- and a chart published for a claim the ledger does not.
"""

import json
import math
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from migratlas.reports import headline

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "web" / "public" / "headline.json"
LEDGER = ROOT / "web" / "public" / "findings.json"


def test_a_trend_passes_through_the_middle_of_its_points() -> None:
    values = (10, 12, 11, 13, 14)
    points = [headline.Point(year=2000 + i, value=float(v), n=1) for i, v in enumerate(values)]
    trend = headline.anchored(points, per_decade=-5.0)
    # The mean of the points sits at the mean year, and the slope is the published one.
    mid = (trend.start + trend.end) / 2
    assert mid == pytest.approx(12.0)
    assert (trend.end - trend.start) == pytest.approx(-5.0 * 4 / 10)


def test_a_histogram_counts_every_value_inside_its_axis_and_says_how_many_fell_out() -> None:
    rng = np.random.default_rng(7)
    values = np.concatenate([rng.normal(0.0, 1.0, 1000), [40.0, -40.0]])
    bins, clipped = headline.histogram(values, bins=20)
    assert sum(b.count for b in bins) + clipped == values.size
    assert clipped >= 2
    # Zero is an edge, so no bar straddles the mark the pile is read against.
    edges = [b.low for b in bins] + [bins[-1].high]
    assert any(math.isclose(edge, 0.0, abs_tol=1e-9) for edge in edges)
    # Bars tile the axis: each starts where the last ended.
    for earlier, later in pairwise(bins):
        assert earlier.high == pytest.approx(later.low)


def test_a_histogram_of_one_sided_values_still_tiles() -> None:
    values = np.linspace(1.0, 2.0, 50)
    bins, clipped = headline.histogram(values, bins=10)
    assert len(bins) == 10
    assert clipped + sum(b.count for b in bins) == 50


def test_the_document_round_trips_with_its_kinds() -> None:
    drawn = headline.Document(
        schema_version=headline.SCHEMA_VERSION,
        headlines=[
            headline.Headline(
                key="x",
                title="t",
                reading="r",
                chart=headline.Strip(unit="u", bars=[headline.Bar("a", 1.0, None, None)], marks=[]),
            )
        ],
    )
    payload = json.loads(headline.render(drawn))
    assert payload["schema_version"] == headline.SCHEMA_VERSION
    assert payload["headlines"][0]["chart"]["kind"] == "strip"
    assert payload["headlines"][0]["chart"]["bars"][0]["low"] is None


@pytest.mark.skipif(not PUBLISHED.is_file() or not LEDGER.is_file(), reason="documents not built")
def test_every_published_headline_belongs_to_a_published_claim() -> None:
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    keys = {finding["key"] for finding in ledger["findings"]}
    assert document["schema_version"] == headline.SCHEMA_VERSION
    assert document["headlines"], "a document with nothing drawn in it"
    for drawn in document["headlines"]:
        assert drawn["key"] in keys, drawn["key"]
        assert not any(ch.isdigit() for ch in drawn["title"]), drawn["title"]
        assert drawn["chart"]["kind"] in {"years", "histogram", "strip"}
