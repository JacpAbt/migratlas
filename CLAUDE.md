# Working on Migratlas

What the README does not say, because it is addressed to a reader rather than to whoever is next at
the keyboard. `README.md` is the project; this is how to work on it without breaking something quiet.

## The two rules that outrank the rest

**Animal safety and legality come first.** Not a disclaimer — `src/migratlas/redact.py` is a
capability, and a tile builder that has no `PublicationClearance` does not compile. Do not route
around it, do not add a write path that does not take one, and do not reclassify a taxon to make a
layer draw. `docs/ETHICS.md` is the procedure.

**This is not a bird project.** It drifts bird-ward on its own and the correction is structural:
`realm` is required on every source and every schema, and `tests/test_taxon_agnostic.py` parses the
syntax tree of the core packages and fails on taxon words in identifiers. If you need to know what a
source measures, you are in `ingest/` or `models/`, which are exempt for that reason.

## Standing rules

- **Sole commit authorship.** Never add `Co-Authored-By`, never add a tool footer.
- **Credentials live in `.env` as `MIGRATLAS_CRED_*`** and are read through `Settings.credential()`.
  Never paste one into a chat, a commit, a log line or a test fixture.
- **One change at a time.** Land it, run the gate, commit, then look back at it before starting the
  next. Batching untested changes is how the 89% garbage ingest survived a run.
- **Prose is part of the code.** Terse docstrings that say what is true and non-obvious; no comment
  that restates its line; current language features. A comment earns its place by naming a bug it
  prevents or a decision it records.
- **Say what actually happened.** If a suite failed, quote it. Truncated output that looks green has
  been reported as green here twice; scripts should end with a single verdict line so reading the
  tail is enough.

## Where things are

Windows host, WSL Ubuntu for Python. Git and `gh` run on **Windows** — WSL git has no credential
helper and `git push` blocks forever. `gh` is not on PowerShell's PATH: use
`/c/Program Files/GitHub CLI/gh.exe`.

**`gh pr merge --auto` does not wait here.** This repository has no *required* status checks
configured, and auto-merge only waits for checks that are required — with none, it merges on the
spot. It was used once to mean "merge when green" and merged onto a red build within the second.
Watch the run and merge explicitly, or make the checks required first.

| Thing | Path |
| --- | --- |
| venv | `~/.venvs/migratlas` (outside the tree, deliberately) |
| lake | `~/migratlas-data` |
| raw archives | `/mnt/a` |
| uv | `~/.local/bin/uv` |

Always go through `make`. A bare `uv run` creates a stray `./.venv` in the working tree that then
outranks the real one. Long commands go through a `.sh` in a temp dir invoked as
`wsl -d Ubuntu -- bash <path>`; write the script with an editor rather than a heredoc, which breaks
on quoting. Machine-specific notes are in the gitignored `docs/DEVELOPMENT.local.md`.

**No sudo.** Every dependency must be a wheel. That rules out tippecanoe and system GDAL, and it is
the reason the geospatial stack looks the way it does.

## Conventions that are load-bearing

**Pre-register before you fetch.** A method note in `docs/methods/` is written *before the download*,
not merely before the analysis: an H1 question, a status line naming what specifically has not yet
been looked at, the estimand and unit with their known problems stated up front, numbered
falsifiable predictions, stop conditions, and "what this cannot establish". Results are appended to
the same file afterwards with every prediction graded, and a pre-registration that turned out wrong
is recorded as a correction rather than edited away. This convention is the most valuable thing in
the repository.

**Every published number is computed from the lake on every build.** `reports/findings.py` re-runs
the analysis; it is slow on purpose. A figure typed once is a figure that goes stale silently. Every
`Finding` carries a scope and a caveat and the schema will not let it not, and nulls and limits are
published beside changes — a ledger showing only the positive results would be lying by selection.

**The registry is the only door.** Nothing is ingested that is not in
`src/migratlas/catalog/registry.yaml`, every adapter starts at `catalog.admit()`, and
`docs/data/PROVENANCE.md` is generated from the registry and tested for drift.

**Read the lake through `lake.reader.scan()`** with an explicit `source_id`, never `pl.scan_parquet`.
Both traps that module closes produce wrong answers rather than errors.

## Traps, each of which cost a run

- Movebank's event endpoint returns every fix a tag ever sent. Without `deployment_id` **and**
  `visible`, 89% of the rows are positions the data owners already marked wrong.
- `scan_parquet(hive_partitioning=True).group_by("source_id")` on polars 1.43 returns one row per
  *file*, each carrying the whole source's count. `reader.py` forces the projection; do not remove it.
- MapLibre must stay in `optimizeDeps.exclude` and its worker imported as `?worker&url`. Get either
  wrong and the globe renders an empty canvas at 60 fps with nothing in the console — which is why
  `web/tests/globe.spec.ts` asks the map what it actually drew, and why `scripts/check-build.mjs`
  exists.
- Frontend prose is authored in Python and rendered verbatim. Changing a sentence means editing
  `reports/`, regenerating the JSON, and updating the browser assertions that quote it.

## The gates

```bash
make check      # ruff, ruff format --check, mypy strict over src and tests, pytest
make web-test   # tsc, vite build + check-build.mjs, Playwright against preview (not dev)
```

CI runs exactly these. `make lake-check` reports schema drift and is not in CI because it needs a
lake. Open work is tracked in `docs/TASKS.md`.
