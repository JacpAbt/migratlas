"""CLI: one entry point per job, so every pipeline stage is reproducible as a single
command rather than a notebook cell someone ran once."""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from migratlas import __version__
from migratlas.catalog import loader as catalog
from migratlas.catalog import provenance
from migratlas.config import get_settings
from migratlas.drivers import attrici, cmip6, era5, narr
from migratlas.ingest import (
    bbs,
    darkecology,
    ebird_st,
    fishglob,
    megamove,
    movebank,
    obis,
    sabap1,
    sabap2,
)
from migratlas.lake import check as lake_check
from migratlas.lake import purge as lake_purge
from migratlas.reports import (
    counterfactual,
    detectability,
    findings,
    phase1,
    phase1_ebird,
    phase1_hierarchical,
    phase1_robustness,
    phase1b,
    phase1c,
    phase1d,
    phase2a_attribution,
    phase2a_attrici,
    phase2a_thermal,
    phase2a_timing,
    sandbox,
)
from migratlas.tiles import layers as tile_layers
from migratlas.tiles import species as tile_species

DRIFT_SAMPLE = 5
"""How many drifted files to name before summarising the rest."""

app = typer.Typer(
    name="migratlas",
    help="A globe of animal movement, and why it's changing.",
    no_args_is_help=True,
    add_completion=False,
)

catalog_app = typer.Typer(help="Inspect the source registry.", no_args_is_help=True)
ingest_app = typer.Typer(help="Land a source in the lake.", no_args_is_help=True)
taxonomy_app = typer.Typer(help="Resolve names against the GBIF Backbone.", no_args_is_help=True)
report_app = typer.Typer(help="Reproducible analysis reports.", no_args_is_help=True)
app.add_typer(catalog_app, name="catalog")
app.add_typer(ingest_app, name="ingest")
app.add_typer(taxonomy_app, name="taxonomy")
app.add_typer(report_app, name="report")


@ingest_app.command("darkecology")
def ingest_darkecology(
    *,
    force: Annotated[bool, typer.Option(help="Re-download even if already present.")] = False,
) -> None:
    """Land the Dark Ecology daily time series (FLUX, aerial)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    result = darkecology.ingest(force=force)
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@ingest_app.command("megamove")
def ingest_megamove() -> None:
    """Land the MegaMove 1-degree grids (ABUNDANCE_SURFACE, marine).

    Requires operator-placed archives; the command names the path if they are absent.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    result = megamove.ingest()
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@ingest_app.command("obis")
def ingest_obis() -> None:
    """Land the OBIS speciesgrids marine slice (ABUNDANCE_SURFACE, marine)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    result = obis.ingest()
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@ingest_app.command("ebird-st")
def ingest_ebird_st(
    limit: Annotated[int | None, typer.Option(help="Land only the first N species.")] = None,
) -> None:
    """Land eBird Status and Trends weekly abundance (ABUNDANCE_SURFACE, aerial).

    Analysis only: this source's licence forbids redistribution, the registry says so, and the
    gate refuses to publish it. Fifty species, which is the Terms' cap.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    result = ebird_st.ingest(limit=limit)
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@ingest_app.command("fishglob")
def ingest_fishglob() -> None:
    """Land the FISHGLOB bottom-trawl surveys (SURVEY_INDEX, marine).

    The first source where effort is fixed by design rather than corrected after the fact.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    result = fishglob.ingest()
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@ingest_app.command("bbs")
def ingest_bbs() -> None:
    """Land the North American Breeding Bird Survey (SURVEY_INDEX, terrestrial).

    A second instrument on the continent Phase 1a measured, with effort fixed by design since 1966.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    result = bbs.ingest()
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@ingest_app.command("sabap2")
def ingest_sabap2() -> None:
    """Land the second Southern African Bird Atlas (SURVEY_INDEX, terrestrial).

    Streams a 7.4 GiB Darwin Core archive rather than extracting the 53 GB inside it, then caches a
    projection, so the first run is slow and later ones reuse it.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    result = sabap2.ingest()
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@ingest_app.command("sabap1")
def ingest_sabap1() -> None:
    """Land the first Southern African Bird Atlas (SURVEY_INDEX, terrestrial).

    The first source that is neither northern nor marine, and the first terrestrial one. Two
    gigabytes unpacked, so the first run is slow and later ones reuse the extracted core.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    result = sabap1.ingest()
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@ingest_app.command("movebank")
def ingest_movebank(
    source: Annotated[
        str, typer.Option(help="One registered study source id, or 'all' for every one.")
    ] = "all",
) -> None:
    """Land terrestrial mammal tracks (TRACK, terrestrial). The lake's first individual data.

    Seven Movebank studies, five species, about 6 million locations. Each study is an
    all-or-nothing download behind a licence handshake -- Movebank ignores request limits -- so the
    responses are cached and the accepted terms are stored beside them.

    Two of the seven publish nothing: `high` sensitivity at individual granularity withholds the
    data entirely. They still land in the lake, because a trend computed from them may be reported
    even where a map may not. See docs/methods/phase1d-tracks.md.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    wanted = [study.source_id for study in movebank.STUDIES] if source == "all" else [source]
    for source_id in wanted:
        result = movebank.ingest_study(source_id)
        print(f"{result.rows:,} rows -> {result.path}")
        print(f"run {result.run_id}")


@app.command("ingest-narr")
def ingest_narr(
    start: Annotated[int, typer.Option(help="First year, inclusive.")] = 1995,
    end: Annotated[int, typer.Option(help="Last year, inclusive.")] = 2025,
    months: Annotated[
        str, typer.Option(help="Comma-separated calendar months, or 'all'.")
    ] = "3,4,5,6,8,9,10,11",
    # A CLI flag, which is what typer builds from a boolean parameter -- the readability
    # objection FBT guards against does not apply to an argv-facing signature.
    resume: Annotated[  # noqa: FBT002
        bool, typer.Option(help="Fetch only the years holding an incomplete month.")
    ] = False,
) -> None:
    """Land NARR night winds at the radar stations (driver samples, gridded).

    Months default to the two migration windows the phenology uses, because a month outside them
    costs the same to fetch and answers nothing. See adr/0006 for why this is NARR over OPeNDAP
    rather than ARCO-ERA5.

    `--resume` closes a gap without refetching what already landed. It works by year rather than
    by month because the lake partitions by year, so a write holding one month would replace that
    whole year.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    only = None if months == "all" else tuple(int(part) for part in months.split(","))
    points = narr.stations_from(phase1.load_conus_nights())
    result = narr.ingest(points, date(start, 1, 1), date(end, 12, 31), only=only, resume=resume)
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@app.command("ingest-era5")
def ingest_era5(
    start: Annotated[int, typer.Option(help="First year, inclusive.")] = 1995,
    end: Annotated[int, typer.Option(help="Last year, inclusive.")] = 2025,
    months: Annotated[
        str, typer.Option(help="Comma-separated calendar months.")
    ] = "3,4,5,6,7,8,9,10,11",
    fields: Annotated[
        str, typer.Option(help="Comma-separated fields: precipitation, temperature.")
    ] = "precipitation,temperature",
) -> None:
    """Land ERA5 monthly fields at the radar stations (driver samples, gridded).

    An independent precipitation record, which is what separates weather from instrument in the
    2012 screening step -- see docs/methods/phase1c-homogeneity.md, Test D.

    Needs MIGRATLAS_CRED_CDS_TOKEN and a one-off acceptance of the dataset's `cc-by` licence.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    points = narr.stations_from(phase1.load_conus_nights())
    result = era5.ingest(
        points,
        list(range(start, end + 1)),
        [int(part) for part in months.split(",")],
        fields=tuple(part.strip() for part in fields.split(",")),
    )
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@app.command("ingest-attrici")
def ingest_attrici(
    start: Annotated[int, typer.Option(help="First year, inclusive.")] = 1995,
    end: Annotated[
        int, typer.Option(help="Last year, inclusive. The counterfactual ends in 2019.")
    ] = attrici.LAST_YEAR,
) -> None:
    """Land ISIMIP3a factual and counterfactual daily temperature at the radar stations.

    The second counterfactual, asking a different question of different data: DAMIP asks what if
    there had been no human forcing, ATTRICI asks what if there had been no warming, and answers it
    by detrending observations rather than by running a model. Both halves land together, since the
    factual one is the control that licenses using the other.

    No account needed. See docs/methods/phase2a-attrici.md.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    if end > attrici.LAST_YEAR:
        # Clamped loudly rather than silently returning fewer years: a shrunken window that nobody
        # announced is how a claim quietly starts covering something else.
        print(f"counterclim ends in {attrici.LAST_YEAR}; clamping --end from {end}")
        end = attrici.LAST_YEAR
    points = narr.stations_from(phase1.load_conus_nights())
    result = attrici.ingest(points, list(range(start, end + 1)))
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@app.command("ingest-cmip6")
def ingest_cmip6() -> None:
    """Land CMIP6 historical and DAMIP hist-nat pre-season temperature at the radar stations.

    The counterfactual: hist-nat is the climate the models say we would have had without human
    forcing. Landed with kind=simulated, never mixed with an observation. See
    docs/methods/phase2a-attribution.md.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    points = narr.stations_from(phase1.load_conus_nights())
    result = cmip6.ingest(points)
    print(f"{result.rows:,} rows -> {result.path}")
    print(f"run {result.run_id}")


@app.command("build-ribbon")
def build_ribbon(
    out: Annotated[Path, typer.Option(help="Where to write the counterfactual ribbon.")] = Path(
        "web/public/counterfactual.json"
    ),
) -> None:
    """Observed passage dates against each counterfactual, drawn as two ribbons.

    Two questions, one chart each: what if there had been no human forcing, and what if there had
    been no warming. They disagree by a factor of about 2.4 and both are right, which is why this is
    not one chart with four lines -- four would invite averaging, and averaging is meaningless here.

    Neither counterfactual is flat. Each removes only what it attributes, and about half the
    observed advance does not track temperature at all.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    comparison = counterfactual.collect()
    size = counterfactual.write(out, comparison)
    for ribbon in comparison.ribbons:
        print(f"\n{ribbon.key}: {ribbon.question}")
        print(f"  {ribbon.window[0]}-{ribbon.window[1]}, {len(ribbon.years)} years")
        for line in ribbon.lines:
            print(f"  {line.label:<28} {line.per_decade:+.3f} days per decade")
        print(f"  the two part by {ribbon.divergence:.2f} days across the window")
    # Printed rather than counted: the text says whether the second ribbon is there and why, so a
    # run that lost it to its own control reads as a result instead of as a shorter list.
    print(f"\n{comparison.disagreement}")
    print(f"\nribbons -> {out} ({size / 1024:.1f} KiB)")


@app.command("build-detectability")
def build_detectability(
    out: Annotated[Path, typer.Option(help="Where to write the detectability grid.")] = Path(
        "web/public/detectability.json"
    ),
) -> None:
    """Where a change could ever be measured, and where it could not, as a one-degree grid."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    found = detectability.collect()
    size = detectability.write(out, found)
    total = sum(found.summary.values())
    for status, cells in found.summary.items():
        print(f"  {status:<22} {cells:>6,} cells  {cells / total:>5.1%}")
    print(f"detectability -> {out} ({size / 1024:.1f} KiB)")


@app.command("build-sandbox")
def build_sandbox(
    out: Annotated[Path, typer.Option(help="Where to write the sandbox document.")] = Path(
        "web/public/sandbox.json"
    ),
) -> None:
    """Recompute the analysis with each safeguard switched off, and write the variants.

    Slow on purpose: it re-runs the analyses, the marine one once per effort threshold. Nothing here
    is a new metric -- every setting is a parameter of a function the reports already call.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    computed = sandbox.collect()
    size = sandbox.write(out, computed)
    knobs = ", ".join(knob.key for knob in computed.knobs)
    print(f"{len(computed.knobs)} knobs ({knobs}), {len(computed.refusals)} refusal(s)")
    print(f"sandbox -> {out} ({size / 1024:.1f} KiB)")


@app.command("build-findings")
def build_findings(
    out: Annotated[Path, typer.Option(help="Where to write the findings document.")] = Path(
        "web/public/findings.json"
    ),
) -> None:
    """Compute what the research established, for the globe to render.

    Re-runs the analyses rather than reading a written-down number, so a finding on the site is
    the one the pipeline produces. Minutes, not seconds.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    computed = findings.collect()
    size = findings.write(out, computed)
    for item in computed:
        print(f"{item.direction:<7} {item.key:<20} {item.value}")
    print(f"findings -> {out} ({size / 1024:.1f} KiB)")


@app.command("build-layers")
def build_layers(
    out: Annotated[Path, typer.Option(help="Destination directory for layer files.")] = Path(
        "web/public/layers"
    ),
) -> None:
    """Export the globe's published layers from the lake, through the ethics gate."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    results = tile_layers.build_all(out)
    for result in results:
        size = Path(result.path).stat().st_size / 1024
        print(f"{result.features:>7,} features  {size:>8.0f} KiB  {result.path}")
        print(f"          {result.generalization}")

    manifest_path = out / "manifest.json"
    payload = json.dumps(tile_layers.manifest(), indent=1)
    manifest_path.write_text(payload + "\n", encoding="utf-8")
    print(f"manifest -> {manifest_path}")

    # Per-taxon surfaces and the search index that points at them, built here rather than in a
    # separate command so a search hit can never reference a surface that was not rebuilt.
    species = tile_layers.build_all_species(out)
    index = out.parent / "taxon-index.json"
    size = tile_species.write_index(species, index)
    print(f"{len(species.entries):,} taxon surfaces across {species.shards} shards")
    if species.withheld:
        print(f"  {len(species.withheld)} withheld by the gate")
    if species.too_small:
        print(f"  {species.too_small} below the {tile_species.MIN_CELLS}-cell floor")
    print(f"search index -> {index} ({size / 1024:.0f} KiB)")


@report_app.command("phase1d-tracks")
def report_phase1d() -> None:
    """Terrestrial mammal movement timing, and whether the tracks can carry a trend.

    Screens per-cell coverage first and fits nothing if no cell clears fifteen years, which is the
    stop condition docs/methods/phase1d-tracks.md pre-registered.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    print(phase1d.render())


@report_app.command("phase1")
def report_phase1() -> None:
    """Replicate Horton et al. 2020 passage phenology, then extend to 2025."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase1.render())


@report_app.command("phase1-hierarchical")
def report_phase1_hierarchical() -> None:
    """Station random effects rather than averaged per-station OLS."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase1_hierarchical.render())


@report_app.command("phase1-ebird")
def report_phase1_ebird() -> None:
    """Compare the radar's seasonal cycle against birds-only eBird abundance."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase1_ebird.render())


@report_app.command("phase1-robustness")
def report_phase1_robustness() -> None:
    """Break-specification sensitivity, daytime placebo and permutation null."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase1_robustness.render())


@report_app.command("phase1c")
def report_phase1c() -> None:
    """Speed-weighting control and screening test on the 1995-2025 radar record."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase1c.render())


@report_app.command("phase2a-thermal")
def report_phase2a_thermal() -> None:
    """Thermal tracking: did a species keep its temperature or keep its place?"""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase2a_thermal.render())


@report_app.command("phase2a-timing")
def report_phase2a_timing() -> None:
    """Does warming explain the autumn advance? Sensitivity times warming against observed."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase2a_timing.render())


@report_app.command("phase2a-attrici")
def report_phase2a_attrici() -> None:
    """The second counterfactual: ATTRICI against DAMIP, and the control that licenses it.

    Prints the stop condition first. If ISIMIP's factual half does not reproduce the ERA5 warming
    already in the lake, no comparison is reported. See docs/methods/phase2a-attrici.md.
    """
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase2a_attrici.render())


@report_app.command("phase2a-attribution")
def report_phase2a_attribution() -> None:
    """The causal step: the human share of the autumn advance, from CMIP6 DAMIP."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase2a_attribution.render())


@report_app.command("phase1b")
def report_phase1b() -> None:
    """Marine distribution shift from the FISHGLOB bottom-trawl surveys."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase1b.render())


@catalog_app.command("list")
def list_sources() -> None:
    """Show every registered source."""
    for source in catalog.load().values():
        # A driver-only source has no evidence type, and saying so beats a blank column.
        kind = str(source.evidence_type) if source.provides_evidence else "driver"
        print(f"{source.id:<14} {kind:<18} {source.realm:<12} {source.licence}")


@catalog_app.command("provenance")
def write_provenance(
    out: Annotated[Path, typer.Option(help="Destination Markdown file.")] = Path(
        "docs/data/PROVENANCE.md"
    ),
) -> None:
    """Regenerate the credit and provenance document from the registry."""
    size = provenance.write(out)
    print(f"{len(catalog.load())} sources -> {out} ({size / 1024:.1f} KiB)")


@taxonomy_app.command("warm-names")
def warm_names() -> None:
    """Resolve display names for every published taxon into the cache. Resumable.

    Separate from build-layers on purpose: this is thousands of GBIF requests, and a build should
    be offline and deterministic. Run it once, then rebuilds pick the names up from the cache.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    export = tile_layers.build_all_species(Path("web/public/layers"))
    added = tile_species.warm_names(sorted({e.taxon_key for e in export.entries}))
    print(
        f"{added:,} taxa resolved; "
        f"{len(tile_species.vernaculars()):,} common and "
        f"{len(tile_species.canonical_names()):,} scientific names cached"
    )


@app.command()
def version() -> None:
    """Print the version."""
    print(__version__)


@app.command()
def paths() -> None:
    """Show where the data lake lives and whether it exists yet."""
    settings = get_settings()
    rows = [
        ("data", settings.data_dir),
        ("raw", settings.raw_dir),
        ("lake", settings.lake_dir),
        ("derived", settings.derived_dir),
        ("tiles", settings.tiles_dir),
        ("cache", settings.cache_dir),
        ("duckdb", settings.duckdb_path),
    ]
    for label, path in rows:
        marker = "ok " if path.exists() else "-- "
        print(f"{marker}{label:<8} {path}")


@app.command("init")
def init_lake() -> None:
    """Create the data lake skeleton."""
    settings = get_settings()
    settings.ensure_dirs()
    print(f"lake ready at {settings.data_dir}")


@app.command("lake-check")
def lake_check_command() -> None:
    """Report schema drift in the lake.

    A schema change must be followed by re-ingesting affected sources; a mixed directory
    is read by silently intersecting schemas, so new columns vanish without an error.
    """
    drifts = lake_check.check_all()
    if not drifts:
        print("lake schemas consistent")
        return
    for evidence_type, items in drifts.items():
        print(f"{evidence_type}: {len(items)} file(s) drifted")
        for drift in items[:DRIFT_SAMPLE]:
            print(f"  {drift}")
        if len(items) > DRIFT_SAMPLE:
            print(f"  ... and {len(items) - DRIFT_SAMPLE} more")
    raise typer.Exit(1)


@app.command("lake-floor")
def lake_floor(
    # A CLI flag, which is what typer builds from a boolean parameter.
    apply: Annotated[  # noqa: FBT002
        bool, typer.Option(help="Actually delete the rows. Reports and exits 1 without it.")
    ] = False,
) -> None:
    """Report, or delete, rows the ingest floor would refuse today.

    Deleting data is not a thing to do by default, so the report is the default and `--apply` is
    the deliberate act. Exits 1 when rows are found and not removed, so this can gate a build.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    found = lake_purge.floor_rows()
    if not found:
        print("no floor taxa in the lake")
        return

    for item in found:
        print(
            f"{item.evidence_type.value}/{item.source_id}: {item.rows:,} rows "
            f"({', '.join(item.labels)}) across {len(item.partitions)} partitions"
        )
    if not apply:
        print("\nnot removed. Re-run with --apply.")
        raise typer.Exit(1)

    for purged in lake_purge.purge_floor_taxa():
        print(
            f"{purged.evidence_type.value}/{purged.source_id}: "
            f"{purged.removed:,} removed, {purged.kept:,} kept in the partitions touched"
        )
    remaining = lake_purge.floor_rows()
    if remaining:
        print(f"\n{sum(item.rows for item in remaining):,} rows still present")
        raise typer.Exit(1)
    print("\nnone remain. Rebuild any artifact that was exported before this.")


if __name__ == "__main__":  # pragma: no cover
    app()
