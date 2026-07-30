"""CLI: one entry point per job, so every pipeline stage is reproducible as a single
command rather than a notebook cell someone ran once."""

import json
import logging
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from migratlas import __version__
from migratlas.catalog import loader as catalog
from migratlas.catalog import provenance
from migratlas.config import get_settings
from migratlas.drivers import cmip6, era5, narr
from migratlas.ingest import (
    bbs,
    darkecology,
    ebird_st,
    fishglob,
    megamove,
    obis,
    sabap1,
    sabap2,
)
from migratlas.lake import check as lake_check
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
    phase2a_attribution,
    phase2a_thermal,
    phase2a_timing,
    sandbox,
)
from migratlas.taxonomy import index as taxon_index
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
    """Observed passage dates against the counterfactual without human forcing.

    The counterfactual removes only what was attributed, so it still advances: about half the
    observed advance does not track temperature and was never attributed to anything.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    ribbon = counterfactual.collect()
    size = counterfactual.write(out, ribbon)
    print(f"{ribbon.window[0]}-{ribbon.window[1]}, {len(ribbon.years)} years")
    for line in ribbon.lines:
        print(f"  {line.label:<34} {line.per_decade:+.3f} days per decade")
    print(f"  the two part by {ribbon.divergence:.2f} days across the window")
    print(f"ribbon -> {out} ({size / 1024:.1f} KiB)")


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


@taxonomy_app.command("build-index")
def build_taxon_index(
    out: Annotated[Path, typer.Option(help="Destination JSON file.")] = Path(
        "web/public/taxon-index.json"
    ),
    limit: Annotated[int | None, typer.Option(help="Resolve only the first N seed taxa.")] = None,
) -> None:
    """Build the static species index the frontend searches."""
    report = taxon_index.build(limit=limit)
    size = taxon_index.write(report, out)

    by_realm = Counter(entry.realm for entry in report.entries)
    print(f"{len(report.entries)} taxa -> {out} ({size / 1024:.1f} KiB)")
    for realm, count in sorted(by_realm.items()):
        print(f"  {realm:<12} {count}")

    if report.unresolved:
        print(f"\n{len(report.unresolved)} unresolved:")
        for name, reason in report.unresolved:
            print(f"  {name}: {reason}")
        raise typer.Exit(1)


@taxonomy_app.command("warm-names")
def warm_names() -> None:
    """Resolve common names for every published taxon into the cache. Resumable.

    Separate from build-layers on purpose: this is thousands of GBIF requests, and a build should
    be offline and deterministic. Run it once, then rebuilds pick the names up from the cache.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    export = tile_layers.build_all_species(Path("web/public/layers"))
    added = tile_species.warm_vernaculars(sorted({e.taxon_key for e in export.entries}))
    print(f"{added:,} names resolved; {len(tile_species.vernaculars()):,} cached in total")


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


if __name__ == "__main__":  # pragma: no cover
    app()
