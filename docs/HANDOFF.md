# Handoff

**As of 2026-08-07, `develop` at `9e596fe`.** A snapshot, and the only document here that is one.
Regenerate it wholesale rather than patching it — everything it says is true of a moment, and the
things that stay true live in the documents it links to.

What is *not* here, deliberately: how to work on the project (`CLAUDE.md`), the numbered work list
(`docs/TASKS.md`), the standing rules for admitting a source (`docs/DATASETS.md`), the research plan
(`docs/PLAN.md`), the ethics procedure (`docs/ETHICS.md`), or any individual pre-registration
(`docs/methods/`). This is the synthesis across them: what the project is, what state it is actually
in, what the research adds up to, and what has been learned about doing it.

---

## 1. What the project is

An interactive globe of animal movement, backed by a research pipeline. Live at
[jacpabt.github.io/migratlas](https://jacpabt.github.io/migratlas).

Three things have to be true at once or it is not worth doing:

1. **A shipped artifact** — a globe that is pleasant to use and cheap to host.
2. **Portfolio-grade engineering** — the code is part of the argument.
3. **Genuinely sound research** — not a dashboard with citations bolted on.

The third is the one that shapes everything. The research spine of the current arc is one sentence:
**everything this project knows, it knows from the northern hemisphere — go and check in the south.**
That is now half done, and the checking produced the two newest findings.

Two constraints outrank all the others and are enforced structurally rather than by convention:

- **Animal safety and legality come first.** `redact.PublicationClearance` is a *capability* — a tile
  builder that has not been handed one does not compile. Two sources (wolves, mountain caribou) are
  withheld entirely and their refusal is rendered as site content.
- **This is not a bird project.** `realm` is required on every source and every schema, and
  `tests/test_taxon_agnostic.py` parses the syntax tree of the core packages and fails on taxon words
  in identifiers. It drifts bird-ward on its own; the correction has to be structural.

---

## 2. Where we actually are

### The gap that matters

**The live site is six days and 60 commits behind.** `main` is at `4c19848` (2026-08-01) and serves
**five** findings. `develop` has **seven**. Everything since 1 August — the whole southern-hemisphere
atlas arc, the surface, the water factor, the elk work and the transfer test — **is not visible to
anyone**. Pages deploys only from `main`.

Also: **three commits are unpushed**, `origin/develop` sitting at the pre-registration.

This is the same failure that was found and fixed once already on 1 August, when `main` was 44
commits behind. It has re-accumulated. Whatever the next session does, this is the cheapest large
win available and it is a merge, not a build.

> **When merging: `gh pr merge --auto` does not wait here.** No status checks are *required*, and
> auto-merge only waits for required ones — it merged onto a red build within the second. Watch the
> run and merge explicitly.

### Stale prose

`README.md`'s status line says "Five findings … twenty registered sources". Actual: **seven findings,
24 sources**. That line was fixed once at the start of this arc and has drifted again — which is an
argument for computing it rather than writing it, the way every number on the site already is.

### The gates

Both green as of `9e596fe`:

```bash
make check      # ruff, ruff format --check, mypy strict, pytest -> 933 passed, 4 skipped
make web-test   # tsc, vite build + check-build.mjs, Playwright vs preview -> 80 passed
```

CI runs exactly these, on `main` and `develop`. `make lake-check` reports schema drift and is not in
CI because it needs a lake.

One known flake: `notebook.spec.ts` "changing claim never blocks the main thread" failed once under
full-suite load, then passed in isolation and in two subsequent full runs. Not investigated further.

---

## 3. What the research says

Seven findings, every number recomputed from the lake on every build. `reports/findings.py` is slow
on purpose — a figure typed once goes stale silently, which §2 has just demonstrated twice.

| key | dir | realm | what it says |
| --- | --- | --- | --- |
| `autumn-advance` | change | aerial | Nocturnal autumn passage advanced **−0.56 ± 0.25 days/decade**, 37–50°N. The project's only substantive positive claim. |
| `composition-stable` | change | aerial | Airspeed trend **−0.06 ± 0.08 m/s per decade** — flat. What is flying did not change, so the advance is timing and not composition. |
| `anthropogenic-share` | change | aerial | Human forcing accounts for **−0.30 of the −0.56**. Attributes the *warming*, not the migration. |
| `marine-null` | null | marine | **Median −0.011 °lat/decade** over 2,240 species×survey pairs. Surveys disagree even in direction. |
| `atlas-no-net-change` | null | terrestrial | **Median −0.007** occupancy change, deciles −0.075 to +0.048, 512 species on 496 shared cells. First southern, first non-radar finding. |
| `coverage-bias` | limit | all | **35.9%** of time-series rows are southern; **0.93%** of driver samples are. The evidence crossed the equator and the data that would explain it barely started. |
| `transfer-fails` | limit | all | Hold-one-out error **0.68** for the aerial realm against 0.06 and 0.02 for the other two. |

### What they add up to

The honest summary is **one positive result and a lot of well-characterised absence**, and that is a
respectable position rather than a disappointing one — the schema refuses to let a ledger show only
its positives, and three of the seven are nulls or limits by design.

The newest finding is the most interesting and the most fragile. `transfer-fails` measured a thermal
tracking ratio in three realms under one audit and found that **marine-north (−0.025) and
terrestrial-south (−0.014) are statistically indistinguishable** — 0.011 apart, Holm p 0.099, each
covering ~50% of the other — while **aerial-north (−0.706) sits 0.68 from both**. Two records
differing in hemisphere, realm, instrument, taxon and decade agreed; the one measuring *when* rather
than *where* did not.

Its ceiling is in its own caveat: **the two realms that agree, agree at no tracking at all**, and an
absence of response is much cheaper to reproduce than a response. And the failing leg is
simultaneously the only phenological one, the only radar one and the only one needing a unit
conversion — three confounds that three data points cannot separate.

### The open wound

The **2012 latitude-graded step** in the radar record is unexplained after four failed hypotheses
(truncation, panel composition, curvature, drought). It sits inside the headline claim as an `open`
ROBITT domain and is published as such. Not scheduled for a fifth attempt; leaving it exposed is the
honest move.

---

## 4. The architecture, in one pass

Python 3.14 / uv / polars / pyarrow / scipy on the analysis side; Svelte 5 runes / Vite / MapLibre
GL v6 / Playwright on the front. Static hosting, no server.

The load-bearing pieces, none of which should be worked around:

- **`catalog.admit()` is the only door.** Nothing is ingested that is not in `registry.yaml`; every
  adapter starts there. `docs/data/PROVENANCE.md` is generated from the registry and tested for drift.
- **`redact.PublicationClearance`** as a capability, not a check. See §1.
- **Seven Arrow schemas behind a `TableSpec` protocol**, with `realm` required. Four of the seven
  evidence types carry data; the remaining three are unused and the site says so. Of the four, the
  track sources support no trend at all — collar effort is not a measured denominator — so they
  widen coverage without widening what can be measured.
- **`lake.reader.scan()` with an explicit `source_id`** — never `pl.scan_parquet`. Both traps that
  module closes produce *wrong answers* rather than errors.
- **`reports/` computes every published number from the lake**, and every `Finding` carries a scope,
  a caveat and a six-domain ROBITT assessment the schema will not let it omit.
- **Frontend prose is authored in Python** and rendered verbatim. Changing a sentence means editing
  `reports/`, regenerating JSON, and updating the browser assertions that quote it.

`src/migratlas/models/` is one-third built: `occupancy.py` (267 lines, real) and `trends.py` (219).
`attribution/`, `forecast/` and `ssf/` are still `__init__.py` only.

**Environment**: Windows host, WSL Ubuntu for Python. Git and `gh` run on **Windows**. Venv lives
outside the tree at `~/.venvs/migratlas`; always go through `make`, because a bare `uv run` creates a
stray `./.venv` that then outranks the real one. **No sudo** — every dependency must be a wheel,
which is why there is no tippecanoe and no system GDAL. Machine specifics in the gitignored
`docs/DEVELOPMENT.local.md`.

---

## 5. What has been learned about working on this

Two patterns are worth more than any individual fix, because they predict where the next mistake
will be.

### Every serious bug here has been a silent wrong answer, not an error

ERA5 cached on field name only, so a southern request found a North American file and 496 points
snapped to the wrong continent — and the log said "already present". `round(4).cast(String)` dropped
a trailing zero, so two sources shared **0 of 496** site ids and the join returned zero rows instead
of raising. `n_unique()` on a latitude column counted 51 latitudes and capped a power check at 50
occupied cells when the real median was 168. Dividing by `dT/dlat` alone gave a survey an isotherm
velocity of −44 °latitude per decade.

None threw. Every one returned a plausible number. **The fixes that stuck are the ones that convert a
wrong answer into a crash** — the disjoint-write guard in `lake/writer.py`, `cell_site_id` as one
shared function, `nearest_cells(max_error_km=…)` raising "not describing the same place".

A related habit worth keeping: an instrument that measures a problem and is never read is not an
instrument. `Located.error_km` was computed on every point, faithfully recorded a wrong-continent
match, and was checked by nothing.

### Every structural guess has been wrong; every measurement has been right

The hatch, rough.js, the page turn, the same-machine performance ratio, ERA5 twice, the camera
framing, and — most expensively — the pre-registration's own list of confounds. Each time the guess
was wrong and the subsequent measurement was right. The rule that falls out: **measure before
deciding, even when the decision looks obvious**, and especially when it is a decision about what
cannot matter.

### The conventions that earn their keep

- **Pre-register before you fetch.** The method note goes in `docs/methods/` *before the download*.
  On the transfer test the power check ran first and killed two bad designs while it was still cheap.
- **A pre-registration that turned out wrong is recorded as a correction, not edited away.**
  `phase1i-transfer.md` carries two.
- **Stop conditions must be able to fire.** The aerial leg's nearly did, and was resolved by
  re-running under three windows rather than by argument.
- **Say what actually happened.** Truncated output that looked green has been reported as green here
  twice.
- **One change at a time.** Batching untested changes is how an 89%-garbage ingest survived a run.

### The uncomfortable one

The transfer test's two *design* failures — §6 omitting response type from its confound list, and
prediction 2 using an n-dependent criterion — were caught **by the result**, not by the process.
Had the answer come out differently, both would have shipped unnoticed. Pre-registration is supposed
to prevent exactly that and here it did not. Worth carrying into the next note: after writing the
confound list, ask what the *result* could look like that the list does not explain.

---

## 6. Where it goes

`docs/TASKS.md` is the list and numbers there are permanent. This is the judgement on top of it.

**Do first, and it is not a build:**

1. **Merge `develop` to `main`.** Seven findings instead of five, six days of work made visible, and
   the highest ratio of value to effort available. Push the three local commits first.
2. **Make the README status line compute itself**, or delete the counts from it. It has now drifted
   twice.

**Then, in rough order of value:**

3. **Publish the elk methodological finding** (`phase1h`). Judged as probably a wrong refusal
   earlier; publishing it would also unblock TASKS #14, which needs a terrestrial finding whose taxa
   are not birds before the ledger test can be tightened from realm to class.
4. **Connect species pages to claims.** There is no link in either direction today. The marine
   per-species view *is* `marine-null`'s argument — pick a species, watch it move north in one survey
   and south in another — and a reader currently cannot get from the claim to it.
5. **Presentation work on the site.** Explicitly deferred by the owner until after the model, and the
   model has now landed. This is the next agreed piece of work.
6. **TASKS #13, forecast A** — passage date under ScenarioMIP. The novelty mask is the headline.

**Carrying, not scheduled:** the 67-field "dead measurement" audit needs filtering against what the
frontend actually reads via `asdict()` before it means anything. `web/mocks/` contains source `.jpg`
paper scans that `tokens.css` documents measurements from — removal is the owner's call.
`docs/ideas/satellite-drivers-on-the-globe.md` is unassessed.

**Deliberately not scheduled:** the FluxRGNN-style nocturnal-flux nowcast. 220 GiB of vertical
profiles, GPU training, and direct competition with BirdCast on the same radar network.
`docs/methods/literature-2026-07.md` argues this is the wrong place to spend the project's scarcest
resource. Revisit only as an explicitly-labelled engineering showcase, never as the novelty claim.
