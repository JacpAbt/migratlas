"""CLI: one entry point per job, so every pipeline stage is reproducible as a single
command rather than a notebook cell someone ran once."""

from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from migratlas import __version__
from migratlas.catalog import loader as catalog
from migratlas.catalog import provenance
from migratlas.config import get_settings
from migratlas.taxonomy import index as taxon_index

app = typer.Typer(
    name="migratlas",
    help="A globe of animal movement, and why it's changing.",
    no_args_is_help=True,
    add_completion=False,
)

catalog_app = typer.Typer(help="Inspect the source registry.", no_args_is_help=True)
ingest_app = typer.Typer(help="Land a source in the lake.", no_args_is_help=True)
taxonomy_app = typer.Typer(help="Resolve names against the GBIF Backbone.", no_args_is_help=True)
app.add_typer(catalog_app, name="catalog")
app.add_typer(ingest_app, name="ingest")
app.add_typer(taxonomy_app, name="taxonomy")


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


if __name__ == "__main__":  # pragma: no cover
    app()
