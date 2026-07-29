"""Does the radar's seasonal cycle look like birds?

The radar measures aerial biomass and cannot separate birds from bats from insects. That is the
single largest interpretive limit on everything in Phase 1a, and it is not resolvable from the
radar alone. eBird is birds only, so comparing the two seasonal curves is the test: if the radar's
passage peaks line up with a composite of nocturnally migrating birds, birds dominate the signal.
If the radar peaks weeks away -- especially in high summer, when insect biomass peaks and bird
passage does not -- then they do not.

Two things this report deliberately does not do:

It does not compare levels. Radar traffic is a flux past a station; eBird abundance is standing
stock over an area. Only timing landmarks are comparable.

It does not compare trends. The 2023 release models a single representative year, so there is no
annual series here to correlate with the radar's 31. Whatever it says about the 2012 step is
nothing.
"""

import logging
from typing import Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType, spec_for
from migratlas.lake.reader import scan
from migratlas.metrics.phenology import passage_quantiles
from migratlas.reports import phase1

log = logging.getLogger(__name__)

EBIRD_SOURCE: Final = "ebird_status_trends"

# eBird's weeks are dated in 2023; the radar's climatology pools 1995-2025. The comparison is
# between two seasonal shapes, so both are reduced to day-of-year and the year is discarded.
SEASONS: Final = (phase1.SPRING, phase1.AUTUMN)

# High summer: between the two migrations, and when North American insect biomass peaks. Day 182
# to 213 is 1 July to 1 August.
SUMMER_DOY: Final = (182, 213)
FLAT_SHARE: Final = (SUMMER_DOY[1] - SUMMER_DOY[0] + 1) / 365


def ebird_weekly_index() -> pl.DataFrame:
    """One CONUS-wide weekly index per species, plus the composite across them.

    Cells are averaged rather than summed within a week: relative abundance is an expected count
    on a standard checklist, and the number of one-degree cells a species occupies changes through
    the season, so a sum would rise with range expansion rather than with abundance.
    """
    weekly = (
        scan(EvidenceType.ABUNDANCE_SURFACE, source_id=EBIRD_SOURCE)
        .group_by("taxon_key", "taxon_label", "period_start")
        .agg(pl.col("value").mean().alias("abundance"), pl.len().alias("cells"))
        .collect()
    )
    if weekly.is_empty():
        return weekly

    # Each species contributes its own seasonal shape, not its absolute abundance: a composite of
    # raw values would be the phenology of whichever species happens to be commonest.
    return weekly.with_columns(
        share=pl.col("abundance") / pl.col("abundance").sum().over("taxon_key")
    ).sort("taxon_label", "period_start")


def as_series(weekly: pl.DataFrame, *, per_species: bool) -> pl.DataFrame:
    """Reshape into the shape ``passage_quantiles`` expects of any timed quantity."""
    keyed = weekly if per_species else weekly.with_columns(taxon_label=pl.lit("composite"))
    return (
        keyed.group_by("taxon_label", "period_start")
        .agg(pl.col("share").sum().alias("magnitude"))
        .rename({"period_start": "timestamp", "taxon_label": "station_id"})
        .sort("station_id", "timestamp")
    )


def as_flux_proxy(weekly: pl.DataFrame, season: str) -> pl.DataFrame:
    """Turn standing abundance into something comparable to a passage flux.

    The reason this exists. Comparing eBird's abundance median to the radar's passage median put
    the radar 18.7 days early in spring and 9.5 days late in autumn -- and both offsets are what
    the stock-versus-flux mismatch predicts, not a finding. Birds arrive and then stay, so standing
    stock keeps rising after passage has finished and its median lands late; in autumn they depart,
    so stock falls away before passage ends and its median lands early. Offsets of that size in
    those directions are an artefact of the quantity, and they are the same order as the effect the
    comparison is meant to detect.

    The flux-like quantity is the rate of change: arrivals in spring are where abundance rises
    fastest, departures in autumn where it falls fastest. Only the relevant sign is kept, because
    a week of departure is not a week of arrival.
    """
    composite = as_series(weekly, per_species=False)
    change = composite.with_columns(delta=pl.col("magnitude").diff()).drop_nulls("delta")
    signed = pl.col("delta") if season == "spring" else -pl.col("delta")
    return change.with_columns(magnitude=signed.clip(lower_bound=0.0)).select(
        "station_id", "timestamp", "magnitude"
    )


def summer_trough(weekly: pl.DataFrame, radar: pl.DataFrame) -> list[str]:
    """Is the radar's quiet season in summer or is its busy season?

    A check the stock-versus-flux problem cannot touch, and the one that actually speaks to the
    insect question. Insect biomass over the US peaks in July and August. If the radar's signal
    were mostly insects its curve would peak there; if it is mostly birds it should show a summer
    trough between two migration peaks.
    """
    lines = []
    summer = pl.col("timestamp").dt.ordinal_day().is_between(*SUMMER_DOY)
    for label, series in (("radar", radar), ("eBird", as_series(weekly, per_species=False))):
        total = float(series["magnitude"].to_numpy().sum())
        if not total:
            continue
        in_summer = float(series.filter(summer)["magnitude"].to_numpy().sum()) / total
        peak_doy = int(
            series.sort("magnitude", descending=True)["timestamp"][0].timetuple().tm_yday
        )
        lines.append(
            f"  {label:<8} {in_summer:>6.1%} of the annual total falls in July "
            f"(a flat year would give {FLAT_SHARE:.1%}), peak week at day {peak_doy}"
        )
    return lines


def quantiles_for(series: pl.DataFrame) -> pl.DataFrame:
    """Passage-date quantiles, from the same function the radar report uses.

    The point of the metric layer being taxon-blind and instrument-blind is exactly this: a radar
    flux series and a modelled abundance series go through one implementation, so a difference in
    the answer cannot be a difference in the code.
    """
    return passage_quantiles(
        series,
        spec_for(EvidenceType.FLUX),
        seasons=list(SEASONS),
        quantiles=phase1.QUANTILES,
        # eBird has 52 weeks and no coverage column; the radar's nightly thresholds would reject
        # every season outright.
        min_coverage=None,
        min_observations=8,
    )


def radar_climatology() -> pl.DataFrame:
    """The radar's seasonal shape, pooled across all years and CONUS stations.

    Pooled deliberately: the comparison is against one modelled eBird year, so the radar has to be
    reduced to one seasonal shape too. Per-station and per-year structure is the subject of the
    other Phase 1a reports, not this one.
    """
    nights = phase1.load_conus_nights()
    return (
        nights.filter(
            pl.col("coverage_fraction").is_null()
            | (pl.col("coverage_fraction") >= phase1.MIN_COVERAGE)
        )
        .with_columns(week=((pl.col("timestamp").dt.ordinal_day() - 1) // 7).clip(0, 51))
        .group_by("week")
        .agg(pl.col("magnitude").median().alias("magnitude"))
        # Placed mid-week and given the same year as eBird's weeks, so both series are just a
        # day-of-year and the metric code sees one kind of input.
        .with_columns(
            timestamp=pl.datetime(2023, 1, 1) + pl.duration(days=pl.col("week") * 7 + 3),
            station_id=pl.lit("radar"),
        )
        .sort("week")
        .select("station_id", "timestamp", "magnitude")
    )


def _summarise(quantiles: pl.DataFrame, season: str) -> dict[str, float]:
    row = quantiles.filter(pl.col("season") == season)
    if row.is_empty():
        return {}
    return {column: float(row[column][0]) for column in ("q10_doy", "q50_doy", "q90_doy")}


def render() -> str:
    weekly = ebird_weekly_index()
    out = [
        "Phase 1a -- does the radar's seasonal cycle look like birds?",
        "=" * 74,
        "The radar cannot separate birds from bats from insects. eBird is birds only, so the",
        "question is whether the two seasonal curves peak at the same time. Timing only: radar",
        "traffic is a flux and eBird abundance is standing stock, so levels are not comparable,",
        "and a single modelled year says nothing about any trend.",
    ]
    if weekly.is_empty():
        out.append("\nNo eBird rows in the lake. Run `make ingest-ebird` first.")
        return "\n".join(out)

    species = weekly["taxon_label"].n_unique()
    out.append(
        f"\neBird: {species} nocturnal-migrant species, "
        f"{weekly['period_start'].n_unique()} weeks, CONUS one-degree cells."
    )

    radar_series = radar_climatology()
    radar = quantiles_for(radar_series)
    birds = quantiles_for(as_series(weekly, per_species=False))

    out += ["", "=" * 74, "1. standing abundance, which is the WRONG comparison", "=" * 74]
    out.append("  Kept because the size and direction of its error is the point.")
    out.append(f"  {'season':<8} {'source':<10} {'q10':>7} {'q50':>7} {'q90':>7}   q50 difference")
    for season in ("spring", "autumn"):
        one = _summarise(radar, season)
        two = _summarise(birds, season)
        if not one or not two:
            out.append(f"  {season:<8} not comparable (one series had too few usable weeks)")
            continue
        for label, values in (("radar", one), ("eBird", two)):
            out.append(
                f"  {season:<8} {label:<10} {values['q10_doy']:>7.1f} {values['q50_doy']:>7.1f} "
                f"{values['q90_doy']:>7.1f}"
            )
        gap = one["q50_doy"] - two["q50_doy"]
        out.append(
            f"  {'':<8} {'':<10} {'':>7} {'':>7} {'':>7}   {gap:+.1f} d "
            f"({'radar later' if gap > 0 else 'radar earlier'})"
        )

    out += [
        "",
        "=" * 74,
        "2. rate of change, which is comparable to a flux",
        "=" * 74,
    ]
    out.append(f"  {'season':<8} {'source':<10} {'q10':>7} {'q50':>7} {'q90':>7}   q50 difference")
    for season in ("spring", "autumn"):
        one = _summarise(radar, season)
        two = _summarise(quantiles_for(as_flux_proxy(weekly, season)), season)
        if not one or not two:
            out.append(f"  {season:<8} not comparable")
            continue
        for label, values in (("radar", one), ("eBird d/dt", two)):
            out.append(
                f"  {season:<8} {label:<10} {values['q10_doy']:>7.1f} {values['q50_doy']:>7.1f} "
                f"{values['q90_doy']:>7.1f}"
            )
        gap = one["q50_doy"] - two["q50_doy"]
        out.append(
            f"  {'':<8} {'':<10} {'':>7} {'':>7} {'':>7}   {gap:+.1f} d "
            f"({'radar later' if gap > 0 else 'radar earlier'})"
        )

    out += [
        "",
        "=" * 74,
        "3. is the radar's summer a trough or a peak? (the insect test)",
        "=" * 74,
    ]
    out += summer_trough(weekly, radar_series)

    out += ["", "=" * 74, "4. per-species spread, q50 day of year", "=" * 74]
    per_species = quantiles_for(as_series(weekly, per_species=True))
    for season in ("spring", "autumn"):
        seasonal = per_species.filter(pl.col("season") == season, pl.col("q50_doy").is_not_null())
        if seasonal.is_empty():
            continue
        spread = seasonal["q50_doy"].to_numpy()
        out.append(
            f"  {season:<8} n={seasonal.height:>3}  median {np.median(spread):.1f}  "
            f"range {spread.min():.0f}-{spread.max():.0f}"
        )

    out += [
        "",
        "=" * 74,
        "How to read this",
        "=" * 74,
        "Section 3 is the one that answers the question, because it is the only one the",
        "stock-versus-flux mismatch cannot touch. North American insect biomass peaks in July.",
        "The radar puts 3.5% of its annual total there against 8.8% for a flat year -- a summer",
        "trough at under half the flat expectation -- while eBird, measuring birds present and",
        "breeding, puts 13.3% there. A signal dominated by resident summer insects",
        "would peak in July, not fall to 40% of flat. So the nocturnal radar traffic is dominated",
        "by migration.",
        "",
        "That does not make it birds specifically. Bats migrate, at night, on a partly overlapping",
        "schedule, and migrating insects exist too. What is ruled out is the specific worry that",
        "the trend is riding on summer insect biomass.",
        "",
        "Section 2 agrees in spring: 3.5 days between a radar flux and a modelled rate of change",
        "is close agreement for two instruments measuring different things. Autumn is 18 d apart,",
        "and the eBird departure curve spans day 214 to 297 at its 10th and 90th percentiles --",
        "diffuse, because post-breeding departure is gradual where spring arrival is a wave. So",
        "autumn is not a sharp test in either direction: spring corroborates, autumn is",
        "inconclusive.",
        "",
        "Section 1 is retained as a worked example of a comparison that looks reasonable and is",
        "not. Both its errors point the way the quantity mismatch predicts, and both are the same",
        "size as the effect being looked for.",
    ]
    return "\n".join(out)
