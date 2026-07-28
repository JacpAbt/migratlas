"""CLI: one entry point per job, so every pipeline stage is reproducible as a single
command rather than a notebook cell someone ran once."""

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from migratlas import __version__
from migratlas.catalog import loader as catalog
from migratlas.catalog import provenance
from migratlas.config import get_settings
from migratlas.ingest import darkecology, megamove, obis
from migratlas.lake import check as lake_check
from migratlas.reports import phase1, phase1_robustness
from migratlas.taxonomy import index as taxon_index
from migratlas.tiles import layers as tile_layers

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
        print(f"{result.rows_out:>7,} features  {size:>8.0f} KiB  {result.path}")
        print(f"          {result.generalization}")

    manifest_path = out / "manifest.json"
    payload = json.dumps(tile_layers.manifest(), indent=1)
    manifest_path.write_text(payload + "\n", encoding="utf-8")
    print(f"manifest -> {manifest_path}")


@report_app.command("phase1")
def report_phase1() -> None:
    """Replicate Horton et al. 2020 passage phenology, then extend to 2025."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase1.render())


@report_app.command("phase1-robustness")
def report_phase1_robustness() -> None:
    """Break-specification sensitivity, daytime placebo and permutation null."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s %(message)s")
    print(phase1_robustness.render())


@catalog_app.command("list")
def list_sources() -> None:
    """Show every registered source."""
    for source in catalog.load().values():
        print(f"{source.id:<14} {source.evidence_type:<18} {source.realm:<12} {source.licence}")


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
