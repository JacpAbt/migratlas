# ADR 0003 — Python 3.14, and what of it we actually use

**Status:** accepted · 2026-07-28

## Context

3.14 is the current stable release. Choosing it needs a better reason than recency, and
several of its headline features are opt-in, so it is worth recording which ones this
project takes and which it declines.

Measured on the interpreter uv provides, rather than assumed:

| Capability | Present | Verdict |
| --- | --- | --- |
| PEP 649 deferred annotations | yes | **adopted** |
| Tail-call interpreter | yes, already enabled in this build | **free, nothing to do** |
| `uuid.uuid7()` | yes | **adopted** |
| t-strings (PEP 750) | yes | **adopted, narrowly** |
| `sys.remote_exec` (PEP 768) | yes | **adopted operationally** |
| `pathlib.Path.copy` / `.move` / `.info` | yes | adopted where it replaces `shutil` |
| `compression.zstd` (PEP 784) | yes | declined for now |
| Free-threading (PEP 779) | build available, all our wheels have `cp314t` | **declined, with a trigger** |
| `concurrent.interpreters` / `InterpreterPoolExecutor` (PEP 734) | yes | declined, with a trigger |

## Decision

**PEP 649 deferred annotations.** The reason 3.14 rather than 3.13. Annotations are lazy
by default, so `from __future__ import annotations` is obsolete and `TYPE_CHECKING`
imports work when something introspects them at runtime. One caveat found the hard way:
pydantic still resolves field annotations to build validators, so ruff's TC003 must be
told which bases are runtime-evaluated or it will move a needed import and break
validation at import time. Configured in `pyproject.toml`.

**Tail-call interpreter** is already compiled into the build uv ships, so the few percent
is banked without doing anything. Recorded here only so nobody goes looking for a flag.

**`uuid.uuid7()`** for ingest run identifiers. Time-ordered, so provenance records sort
chronologically without a separate timestamp column, and `ls` on a run directory comes
out in the order things happened.

**t-strings**, narrowly: DuckDB binds *values* as parameters but not *identifiers*, so
table and column names have to be interpolated. A `Template` lets that interpolation be
validated and quoted in one place instead of relying on every call site to be careful.
Values continue to use real parameter binding.

**`sys.remote_exec`** is an operational adoption, not a code one. Radar ingest runs for
hours; being able to attach to a live process and see where it is beats killing it and
adding a log line. Recorded in the local development notes.

**Free-threading declined, for now.** Tempting, because driver annotation and tile
generation are embarrassingly parallel. But the hot paths are pyarrow, numpy, rasterio
and DuckDB — extensions that already release the GIL — so a plain `ThreadPoolExecutor`
gets most of the parallelism on the standard build. Free-threading pays off for
Python-level loops, which we should be vectorising rather than parallelising.

*Trigger to revisit:* if profiling the annotation pipeline shows the process
GIL-bound with threads idle, and the work resists vectorisation. Then measure the
free-threaded build against `InterpreterPoolExecutor` on the same workload before
switching, because free-threaded builds still carry single-threaded overhead and library
thread-safety is less battle-tested.

**`compression.zstd` declined for now.** Parquet compression is selected through pyarrow,
which bundles its own zstd, and the raw downloads are already-compressed archives. A
synthetic benchmark of the stdlib module on raw float64 bytes showed almost no gain —
but that benchmark was unrepresentative, because Parquet applies dictionary and
byte-stream-split encoding *before* compressing, which is exactly what makes zstd
effective on columnar float data. The real comparison is Parquet-with-zstd against
Parquet-with-snappy on actual radar profiles, and that measurement belongs with the first
ingest rather than here.

## Consequences

Good: the two things that cost nothing (deferred annotations, tail-call) are taken, and
the two small things that improve correctness (`uuid7` ordering, t-string identifier
quoting) are taken where they belong rather than sprinkled around.

Bad: 3.14 is recent enough that a library may lack wheels. Verified at the outset by
installing and importing the full stack including torch 2.13, so the risk is known rather
than latent — but a future dependency could still force a decision.

Deliberately unresolved: the parallelism story. Threads on the standard build until
measurement says otherwise, with a written trigger so it gets revisited on evidence
instead of on enthusiasm.
