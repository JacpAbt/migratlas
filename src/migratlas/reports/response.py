"""The response dial: what the fitted response function says a different world would look like.

The owner's founding question has a second half — not only what changed and why, but *what would
happen if an input changed*. This publishes that, and it is careful about what it is not.

**It is not a forecast, and it does not need to be.** Phase 3a found interannual skill at 20 of 143
stations and Phase 3d's rehearsal refused the standing prediction its licence. A dial is a different
object: it reports the *fitted sensitivity* — a degree warmer in the pre-season is followed by
passage this many days earlier, measured within station across thirty years — and says nothing about
whether next year can be predicted. Both refusals appear on the same panel as the dial, because a
reader who takes a sensitivity for a prediction has been misled by the presentation and not by the
number.

**Two things bound it, and both are drawn rather than described.** The fitted envelope: no dial
position outside the range of within-station anomalies the record actually contains gets a number,
because the line has never been tested there — `DATASETS.md`'s novelty mask, at reader scale. And
the band: `S` is published for 37-50°N, and `transfer-fails` measured hold-one-out error at 0.68
across realms, so the dial is scoped where the claim is.

**No new science.** Every number here comes from `phase2a_timing.sensitivities()`, the fit that
`anthropogenic-share` already rests on, aggregated by the same `_mean_ci` over the same claim band.
The dial reads that fit; it does not re-estimate it. If it did, the dial and the ledger would be
free to disagree.

The types are `sandbox.py`'s, deliberately. A second control vocabulary would mean two ways to
render the same idea, and the sandbox's `Refusal` is already the right shape for "we will not answer
that, and here is the measurement that says why".
"""

import json
import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.reports.sandbox import Knob, Refusal, Variant

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 1

# The dial positions, in the driver's own units. Symmetric and round, fixed here rather than chosen
# from the envelope, so the envelope can *reject* one -- a set of positions picked to all fit inside
# the observed range would make the refusal below unreachable and the bound invisible.
TEMPERATURE_SETTINGS: Final[tuple[float, ...]] = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5)
WIND_SETTINGS: Final[tuple[float, ...]] = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5)

# The position whose value is the published sensitivity itself, so the sandbox's own rule carries
# over: the default reproduces the published number and a test asserts it.
BASELINE_KEY: Final = "plus-1"

# The first position outside the envelope, and so the one the panel refuses. Two degrees is a
# question a reader would actually ask, which makes it a better refusal than a number chosen to be
# obviously absurd.
BEYOND_TEMPERATURE: Final = 2.0

# All four are reported as evidence; the middle pair *bound the dial*.
ENVELOPE_QUANTILES: Final[tuple[float, ...]] = (0.0, 0.05, 0.95, 1.0)

# Why the band and not the extremes. Pooled min and max are the most permissive envelope there is:
# measured on the claim band they run -3.57 to +3.97 degC, so one station-year at one station would
# license the whole dial for all seventy-eight. The 5th-95th band is the range the fit is actually
# informed over, and a bound that a single observation can move is not a bound.
ENVELOPE_BAND: Final[tuple[float, float]] = (0.05, 0.95)


@dataclass(frozen=True, slots=True)
class Response:
    """The dials, and the questions they refuse."""

    schema_version: int
    knobs: list[Knob]
    refusals: list[Refusal]


def _key(setting: float) -> str:
    if setting == 0:
        return "unchanged"
    return f"{'plus' if setting > 0 else 'minus'}-{abs(setting):g}".replace(".", "-")


def _label(setting: float, unit: str, warmer: str, cooler: str) -> str:
    if setting == 0:
        return "as it was"
    direction = warmer if setting > 0 else cooler
    return f"{abs(setting):g} {unit} {direction}"


def anomaly_envelope(series: pl.DataFrame, column: str) -> dict[float, float]:
    """The range of within-station anomalies the record actually contains.

    Within station, because that is how the response was fitted: `S` is what happens when *this*
    station's pre-season departs from *its own* usual, not what happens between a cold station and
    a warm one. An envelope computed across stations would be far wider and would license dial
    positions the fit has never seen.
    """
    anomalies = (
        series.with_columns(
            anomaly=pl.col(column) - pl.col(column).mean().over("station_id"),
        )["anomaly"]
        .to_numpy()
        .astype(float)
    )
    return {share: float(np.quantile(anomalies, share)) for share in ENVELOPE_QUANTILES}


def _dial(  # noqa: PLR0913 -- every argument is a published choice, and a config object would hide it
    *,
    key: str,
    question: str,
    why: str,
    plain_why: str,
    source: str,
    settings: tuple[float, ...],
    sensitivity: float,
    ci95: float,
    stations: int,
    envelope: dict[float, float],
    unit: str,
    warmer: str,
    cooler: str,
) -> Knob:
    """One driver, its dial positions, and the response the fit implies at each.

    Linear, because the fitted response *is* a linear coefficient — this reads the model rather
    than extending it. Whether the true response is linear was not tested: Phase 3f's spline arm
    exists and its result is unread behind a fired stop condition, and the note says so rather
    than letting the straight line imply it was checked.
    """
    low, high = envelope[ENVELOPE_BAND[0]], envelope[ENVELOPE_BAND[1]]
    variants = [
        Variant(
            key=_key(setting),
            label=_label(setting, unit, warmer, cooler),
            value=sensitivity * setting if setting else 0.0,
            ci95=ci95 * abs(setting),
            unit="days",
            n=stations,
            note=(
                "The published sensitivity itself."
                if setting == 1
                else "No change asked for, so no shift implied."
                if setting == 0
                else f"The fitted response, read at {abs(setting):g} {unit}. Inside the range "
                f"the fit is informed over, {low:+.2f} to {high:+.2f} {unit}."
            ),
        )
        for setting in settings
        if low <= setting <= high
    ]
    return Knob(
        key=key,
        question=question,
        why=why,
        plain_why=plain_why,
        claim="anthropogenic-share",
        source=source,
        default=BASELINE_KEY,
        variants=variants,
    )


def _envelope_evidence(envelope: dict[float, float], unit: str) -> list[Variant]:
    labels = {
        0.0: "the least any station's season departed from its own usual",
        0.05: "5th percentile of departures",
        0.95: "95th percentile of departures",
        1.0: "the most any station's season departed from its own usual",
    }
    return [
        Variant(
            key=f"q{share:g}",
            label=labels[share],
            value=value,
            unit=unit,
            n=0,
            note="",
        )
        for share, value in envelope.items()
    ]


def collect() -> Response:
    """Read the published fit, measure its envelope, and build the dials. Reads the lake."""
    # Private names, imported rather than duplicated: the dial has to aggregate the fit exactly the
    # way the published table does, and two copies of an aggregation are two things that drift.
    from migratlas.reports.phase2a_timing import (  # noqa: PLC0415 -- heavy, and only here
        CLAIM_BAND,
        _mean_ci,
        pre_season_temperature,
        sensitivities,
        wind_support,
    )

    fitted = [item for item in sensitivities() if CLAIM_BAND[0] <= item.latitude < CLAIM_BAND[1]]
    if not fitted:
        log.warning("no stations in the claim band; the dial cannot be built")
        return Response(schema_version=SCHEMA_VERSION, knobs=[], refusals=[])

    stations = len(fitted)
    in_band = {item.station_id for item in fitted}
    thermal, thermal_ci = _mean_ci(np.array([item.per_degree for item in fitted]))
    wind, wind_ci = _mean_ci(np.array([item.per_wind for item in fitted]))

    temperature_envelope = anomaly_envelope(
        pre_season_temperature().filter(pl.col("station_id").is_in(in_band)), "temperature"
    )
    wind_envelope = anomaly_envelope(
        wind_support().filter(pl.col("station_id").is_in(in_band)), "support"
    )
    log.info(
        "%d claim-band stations; thermal %+.3f+-%.3f, wind %+.3f+-%.3f",
        stations,
        thermal,
        thermal_ci,
        wind,
        wind_ci,
    )

    knobs = [
        _dial(
            key="pre-season-warmth",
            question="What if the June-July before migration were warmer?",
            why=(
                "This is the response function `anthropogenic-share` is built on, read forwards. "
                "It was fitted within station across thirty years, with wind support alongside it "
                "so the thermal term is not credited with the wind's work, and it is the S in the "
                "S x W arithmetic that attributes half the observed advance to human forcing. "
                "Reading it forwards is not predicting: it says what a warmer pre-season has been "
                "followed by, not what next year will bring."
            ),
            plain_why=(
                "Warmer Junes have been followed by earlier autumn migration. This says by how "
                "much -- not what will happen next year."
            ),
            source="reports.phase2a_timing.sensitivities().per_degree",
            settings=TEMPERATURE_SETTINGS,
            sensitivity=thermal,
            ci95=thermal_ci,
            stations=stations,
            envelope=temperature_envelope,
            unit="°C",
            warmer="warmer",
            cooler="cooler",
        ),
        _dial(
            key="wind-support",
            question="What if the season's winds were more favourable?",
            why=(
                "The obvious mechanism, and it measures nothing. Wind support is the wind's "
                "component along each station's own migration heading, and its fitted coefficient "
                "is indistinguishable from zero -- while being essentially uncorrelated with "
                "temperature within station, so this is a real null rather than the thermal term "
                "having absorbed it. The dial is published *because* it is flat: a panel that only "
                "carried drivers that worked would be a panel selecting for the story."
            ),
            plain_why=(
                "Helpful winds are the obvious explanation, and in this record they do nothing "
                "measurable. The dial shows a driver that turned out flat."
            ),
            source="reports.phase2a_timing.sensitivities().per_wind",
            settings=WIND_SETTINGS,
            sensitivity=wind,
            ci95=wind_ci,
            stations=stations,
            envelope=wind_envelope,
            unit="m/s",
            warmer="more favourable",
            cooler="less favourable",
        ),
    ]

    refusals = [
        Refusal(
            key="beyond-the-envelope",
            question=(f"What if the pre-season were {BEYOND_TEMPERATURE:g} °C warmer than usual?"),
            naive=(
                f"The fitted line continues, and would read "
                f"{thermal * BEYOND_TEMPERATURE:+.2f} days."
            ),
            evidence=_envelope_evidence(temperature_envelope, "°C"),
            verdict=(
                "Withheld, and the number above is shown only to say why it is not published. "
                "Ninety per cent of the departures this response was fitted over lie between "
                f"{temperature_envelope[ENVELOPE_BAND[0]]:+.2f} and "
                f"{temperature_envelope[ENVELOPE_BAND[1]]:+.2f} °C from a station's own usual, and "
                f"{BEYOND_TEMPERATURE:g} °C is outside that. The record does reach "
                f"{temperature_envelope[1.0]:+.2f} °C once, at one station in one year -- which is "
                "the reason the bound is the band, not the extreme: a limit one observation "
                "can move is not a limit. A straight line extended past its data is arithmetic "
                "rather than evidence, and it is the most common way a range-shift projection goes "
                "wrong, which is why every forecast this project plans carries a novelty mask."
            ),
            method="docs/methods/phase2a-timing.md",
        ),
        Refusal(
            key="not-a-forecast",
            question="So will this coming autumn be early?",
            naive=(
                "A sensitivity plus a seasonal weather forecast looks like it should answer that."
            ),
            evidence=[
                Variant(
                    key="stations-with-skill",
                    label="radar stations where autumn timing beats chance",
                    value=20.0,
                    unit="of 143",
                    n=143,
                    note="Phase 3a, era-split against a per-station year-shuffle null.",
                ),
                Variant(
                    key="rehearsal",
                    label="blind years the full pipeline was graded on",
                    value=8.0,
                    unit="years",
                    n=8,
                    note=(
                        "Phase 3d stood at June 1st of 2017-2024 with the forecast actually issued "
                        "that month. The forecast half carried real signal; the pipeline still "
                        "failed to beat chance."
                    ),
                ),
            ],
            verdict=(
                "Not published, and the refusal is this project's own. The pipeline that would "
                "answer it was built, graded on eight blind years, and refused its licence: "
                "seasonal forecasts do carry temperature signal, and the migration prediction on "
                "top of them still did not beat chance. A sensitivity says what warmth has been "
                "followed by. It does not say what next year holds, and the difference between "
                "those two sentences is the whole reason this panel exists."
            ),
            method="docs/methods/phase3d-rehearsal.md",
        ),
    ]
    return Response(schema_version=SCHEMA_VERSION, knobs=knobs, refusals=refusals)


def render(response: Response) -> str:
    return json.dumps(asdict(response), indent=1)


def write(destination: Path, computed: Response | None = None) -> int:
    """Write the response document, computing it only if the caller has not already."""
    payload = render(computed if computed is not None else collect())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload + "\n", encoding="utf-8")
    return len(payload)
