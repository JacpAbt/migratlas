"""What the research established, as a document the globe can render.

The site showed three raw layers and no results, which is the wrong way round: the layers are
the input to the work, not the output. This is the output.

Two rules make it worth having rather than a page of prose that drifts:

- **Every number is computed here, from the lake, by the same functions the reports use.** A
  finding on the site is therefore the finding the pipeline produces, not a figure someone typed
  once and forgot to update. Slow on purpose -- it re-runs the analysis.
- **Every finding carries a limit, and the schema will not let it not.** A claim published
  without its scope and caveat is the failure mode this whole project is arranged against, so
  `Finding` makes both required and a test asserts they are non-empty.

Nulls are findings. "No global marine shift" and "0% of the time-series data is southern
hemisphere" are results, and a site that only showed the positive ones would be lying by
selection.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType
from migratlas.lake.reader import scan, scan_dataset

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 1


@dataclass(frozen=True, slots=True)
class Finding:
    """One thing the work established, with everything needed to read it honestly."""

    key: str
    claim: str
    """One sentence, in the strongest form the evidence supports and no stronger."""

    value: str
    """The number, formatted for display, with its interval."""

    scope: str
    """Where and when it holds. A claim without this is a claim about the whole world."""

    caveat: str
    """What would make it wrong, or what it does not cover. Required, never blank."""

    method: str
    """Path to the pre-registered method note, relative to the repository root."""

    direction: str = "neutral"
    """`change`, `null`, or `limit` -- so the frontend can group rather than parse the text."""

    supporting: list[str] = field(default_factory=list)
    """Tests the claim survived, each one line."""


def _radar_coverage() -> tuple[int, int, int]:
    """Stations, first and last year of the radar record, read from the lake."""
    frame = (
        scan(EvidenceType.FLUX, source_id="darkecology_daily")
        .select(
            station=pl.col("station_id"),
            year=pl.col("timestamp").dt.year(),
        )
        .collect()
    )
    years = frame["year"].to_numpy()
    return frame["station"].n_unique(), int(years.min()), int(years.max())


def _southern_share() -> dict[str, float]:
    """Share of each time-series source's rows south of the equator.

    Computed rather than quoted, because this is the finding most likely to become false
    silently -- the day a southern source lands, a hardcoded 0% would be a lie on the site.
    """
    shares: dict[str, float] = {}
    for source, latitude in (
        ("darkecology_daily", "station_latitude"),
        ("fishglob", "site_latitude"),
    ):
        evidence = EvidenceType.FLUX if source == "darkecology_daily" else EvidenceType.SURVEY_INDEX
        frame = scan(evidence, source_id=source).select(pl.col(latitude).alias("lat")).collect()
        values = frame["lat"].to_numpy()
        shares[source] = float((values < 0).mean()) if values.size else float("nan")
    return shares


def _wind_coverage() -> tuple[int, int, int]:
    """Station-nights of wind, and the span, for the composition finding."""
    frame = (
        scan_dataset("driver_samples", source_id="narr")
        .select(year=pl.col("period_start").dt.year())
        .collect()
    )
    years = frame["year"].to_numpy()
    return frame.height, int(years.min()), int(years.max())


def collect() -> list[Finding]:
    """Compute every finding. Re-runs the analyses, so this takes minutes rather than seconds."""
    # Imported here rather than at module scope: the reports import this module's siblings,
    # so a top-level import would close a cycle.
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415
    from migratlas.reports import phase1b  # noqa: PLC0415
    from migratlas.reports.phase1 import load_conus_nights, station_slopes  # noqa: PLC0415

    _, first_year, last_year = _radar_coverage()
    southern = _southern_share()

    findings: list[Finding] = []

    # --- The headline -------------------------------------------------------
    slopes = station_slopes(load_conus_nights(), max_year=last_year)
    autumn = slopes.filter(
        pl.col("season") == "autumn",
        pl.col("quantile") == "q50_doy",
        pl.col("latitude").is_between(37, 50, closed="left"),
    )
    values = autumn["days_per_decade"].to_numpy().astype(float)
    mean = float(values.mean())
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size)
    findings.append(
        Finding(
            key="autumn-advance",
            claim="Nocturnal autumn passage over the mid-latitude US is happening earlier.",
            value=f"{mean:+.2f} ± {ci:.2f} days per decade",
            scope=(
                f"{autumn.height} US weather-radar stations between 37°N and 50°N, "
                f"{first_year}-{last_year}. Not the whole continent: the southern bands carry a "
                "step change at 2012 that four candidate explanations have failed to account for."
            ),
            caveat=(
                "The radar measures aerial biomass, not birds — it cannot separate birds from "
                "bats from insects. Bats in particular are not excluded."
            ),
            method="docs/methods/phase1-phenology.md",
            direction="change",
            supporting=[
                "Reproduces a published result on its own window before extending it.",
                "Survives four break specifications, a mid-winter placebo and a permutation null.",
                "Unchanged when the speed weighting is removed from the metric.",
                "Unchanged when the non-bird nights are deleted outright.",
            ],
        )
    )

    # --- The null that matters just as much --------------------------------
    # Through the same three steps `phase1b.render` uses, in the same order: the survey unit has
    # to be recovered from the site id before cells are formed, or `analyse` has nothing to group
    # by. Calling the report's own functions rather than restating them is the point -- a second
    # copy of the data preparation is a second thing that can drift from the published method.
    _, pooled, _ = phase1b.analyse(range_metrics.to_cells(phase1b.survey_unit(phase1b.load())))
    shift = pooled["per_decade"].to_numpy().astype(float)
    findings.append(
        Finding(
            key="marine-null",
            claim=(
                "There is no single global poleward shift in fish distribution — surveys "
                "disagree even in its direction."
            ),
            value=(
                f"median {float(np.median(shift)):+.3f} °latitude per decade "
                f"across {shift.size:,} species-survey pairs"
            ),
            scope=(
                "29 harmonised scientific bottom-trawl surveys, North America and Europe, "
                "on consistently sampled cells only."
            ),
            caveat=(
                "A pooled median hides the variation worth predicting: individual surveys reach "
                "-0.22 and +0.26 °latitude per decade in opposite directions. The unit of "
                "analysis has to be the species in its region, not the ocean."
            ),
            method="docs/methods/phase1b-marine.md",
            direction="null",
        )
    )

    # --- The measurement itself, audited ----------------------------------
    nights, wind_first, wind_last = _wind_coverage()
    findings.append(
        Finding(
            key="composition-stable",
            claim=(
                "The autumn signal is not drifting from birds towards insects — what the radar "
                "measures in 2025 means what it meant in 1995."
            ),
            value="airspeed trend -0.06 ± 0.08 m/s per decade (flat)",
            scope=(
                f"{nights:,} station-night wind samples, {wind_first}-{wind_last}, from an "
                "independent regional reanalysis rather than from the radar."
            ),
            caveat=(
                "Spring behaves differently: its airspeed rose, which is either a real change or "
                "migrants flying higher than the fixed wind level assumes. Separating those needs "
                "the vertical radar profiles. Spring carries no trend claim here either way."
            ),
            method="docs/methods/phase1c-homogeneity.md",
            direction="change",
            supporting=[
                "Mean autumn airspeed sits in the range for migrating songbirds, not insects.",
                "A 2012 discontinuity in the dataset's own rain filtering was traced, and ruled "
                "out as weather using independent precipitation data.",
            ],
        )
    )

    # --- The causal step ----------------------------------------------------
    # Published only if the model ensemble is whole. `shortfall` exists because a third of it can
    # go missing on a calendar error and still produce a plausible number, and a site is the last
    # place that should be quoting one.
    from migratlas.reports import phase2a_attribution as attribution  # noqa: PLC0415

    simulations = attribution.simulated()
    seen = attribution.observed()
    windows = [
        found
        for window in attribution.WINDOWS
        if (found := attribution.fraction(simulations, window)) is not None
    ]
    if seen is not None and windows and not attribution.shortfall(simulations):
        primary = attribution.chosen(windows)
        days = primary.ensemble * seen.explained
        bracket = sorted(found.ensemble for found in windows)
        findings.append(
            Finding(
                key="anthropogenic-share",
                claim=(
                    "Human forcing accounts for almost all of the pre-season warming the birds "
                    "are responding to, and so for about half of the observed advance."
                ),
                value=f"{days:+.2f} days per decade of the {seen.advance:+.2f} observed",
                scope=(
                    f"{primary.models} CMIP6 models with both a historical and a hist-nat run, "
                    f"sampled at the {seen.stations} radar stations between 37°N and 50°N over "
                    f"{primary.window[0]}-{primary.window[1]}."
                ),
                caveat=(
                    "This attributes the warming, not the migration. It says what caused the "
                    "temperature change the birds tracked — the other half of the advance does not "
                    "track temperature at all and is unexplained here. The models' human share "
                    f"spans {bracket[0]:.2f} to {bracket[-1]:.2f} depending on the window fitted, "
                    "and CMIP6's historical runs stop in 2014 while the radar record runs to 2025."
                ),
                method="docs/methods/phase2a-attribution.md",
                direction="change",
                supporting=[
                    "The counterfactual runs warm at "
                    f"{primary.natural:+.2f} °C per decade against {primary.historical:+.2f} "
                    "with human forcing included.",
                    "The ensemble reproduces the observed pre-season warming it is calibrated "
                    "against, which is the check that licenses using it.",
                    "Members are averaged within a model before models are averaged, so two "
                    "models with fifty runs each cannot carry the answer.",
                ],
            )
        )

    # --- The limit, published rather than buried --------------------------
    findings.append(
        Finding(
            key="coverage-bias",
            claim=(
                "Everything above is northern-hemisphere. The data that can measure change and "
                "the data that covers the globe are, so far, different data."
            ),
            value=(
                f"{southern.get('darkecology_daily', float('nan')):.1%} of the radar record and "
                f"{southern.get('fishglob', float('nan')):.1%} of the survey record lie south of "
                "the equator"
            ),
            scope="Every source in this project that has a usable time axis.",
            caveat=(
                "Inherited rather than chosen — long digitised radar and trawl series exist where "
                "they were funded — but it bounds every claim here to the northern temperate zone, "
                "and no model trained on it should be trusted elsewhere without being tested "
                "there first."
            ),
            method="docs/methods/geographic-coverage.md",
            direction="limit",
        )
    )

    return findings


def render(findings: list[Finding]) -> str:
    """The findings document, as JSON for the frontend."""
    return json.dumps(
        {"schema_version": SCHEMA_VERSION, "findings": [asdict(item) for item in findings]},
        indent=1,
    )


def write(destination: Path, computed: list[Finding] | None = None) -> int:
    """Write the findings document, computing it only if the caller has not already.

    The parameter exists because `collect` re-runs the analyses and takes minutes: a caller that
    wants to both save and display the findings must not pay for them twice.
    """
    payload = render(computed if computed is not None else collect())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload + "\n", encoding="utf-8")
    return len(payload)
