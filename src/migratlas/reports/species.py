"""What this project knows about one animal, as a page per animal.

The site could already draw a species and could not say anything about it. Selecting a taxon lit up
its cells and stopped there, which is a range map -- the thing every other biodiversity site
already has. What this project has that they do not is a per-species *result* and an audit of it.

The four kinds of card, and each is honest about which it is:

- **A distribution shift.** FISHGLOB, from Phase 1b, which already fits a latitudinal trend for
  every species in every survey and then takes the median of 2,240 of them. That median is the
  `marine-null` finding and the per-species rows behind it were computed and thrown away. They are
  the finding's own argument: the claim is that surveys disagree *in direction*, and a reader
  could not see one species going north in the North Sea and south off Newfoundland because the
  only thing published was the number that averages them out.
- **A tracked animal.** Where it went, over how long, from how many collars -- and the Phase 1d
  result that no track source can carry a timing trend, because changing the collar moves the
  measured date by more than forty days.
- **A refusal.** Wolves and mountain caribou are in the lake and are drawn nowhere. A page that
  quietly skipped them would read as a map with no wolves in it, when the lake holds 174,443 wolf
  fixes. The refusal is re-derived from the gate rather than asserted, exactly as
  `detectability.py` does it.
- **Extent only.** A species OBIS or MegaMove records and nothing measures. Published as "there is
  no study here", rather than as a blank, because an absence explains nothing.

Sharded on the taxon key, 64 ways, the same scheme `tiles/species.py` already uses for the
surfaces -- so a selection fetches one bounded file and the two shards agree about where a taxon
lives.
"""

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.evidence import EvidenceType
from migratlas.lake.reader import scan
from migratlas.lake.reader import sources as lake_sources
from migratlas.redact import PublicationRefusedError, clear_for_publication
from migratlas.tiles.species import SHARDS

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 1

# Below this a "trend" over a handful of surveys is a rounding artefact of which cells were
# sampled. The same floor Phase 1b fits on, restated here so a card cannot quote a looser one.
MIN_YEARS: Final = 15

# A species-survey pair whose shift is smaller than this is reported as "no clear movement" rather
# than as a direction. Half a kilometre a year, at which point the sign is noise and printing it
# would invite a reader to read one.
FLAT_DEGREES: Final = 0.02


@dataclass(frozen=True, slots=True)
class Row:
    """One line of evidence inside a study: a survey, a population, a source."""

    label: str
    value: str
    detail: str


@dataclass(frozen=True, slots=True)
class Study:
    """One thing known about one animal."""

    kind: str
    """`shift`, `tracked`, `withheld` or `extent`. The frontend groups on this, not on the prose."""

    headline: str
    """Plain language, on the ledger's rule: it may drop precision and may never add reach."""

    value: str
    """The number, formatted, or empty where there is not one. Never recomputed downstream."""

    detail: str
    caveat: str
    method: str
    """Path to the method note, relative to the repository root. Tested to resolve."""

    source_id: str

    taxon: str = ""
    """What this study's source calls the animal.

    Carried per study rather than looked up once, because the card may exist for a taxon that has
    no surface and therefore no entry in the search index -- a withheld animal has none by
    construction, which is the point of it.
    """

    rows: list[Row] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SpeciesCard:
    taxon_key: int
    scientific: str
    vernacular: str
    realm: str
    drawn: bool
    """Whether a surface for this taxon exists on the globe. False is a fact, not a gap."""

    studies: list[Study] = field(default_factory=list)


def _fmt(value: float, unit: str) -> str:
    return f"{value:+.3f} {unit}"


def _direction(per_decade: float) -> str:
    if abs(per_decade) < FLAT_DEGREES:
        return "no clear movement"
    return "north" if per_decade > 0 else "south"


def marine_studies() -> dict[int, Study]:
    """One study per marine species, from the rows Phase 1b already computes.

    Runs Phase 1b's own three steps in its own order rather than re-preparing the data. A second
    copy of the preparation is a second thing that can drift from the published method, and this
    has to agree with `marine-null` exactly -- the whole point of the card is that it is the
    finding's own evidence rather than a similar calculation.
    """
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415
    from migratlas.reports import phase1b  # noqa: PLC0415

    _results, pooled, _series = phase1b.analyse(
        range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    )
    if pooled.is_empty():
        return {}

    studies: dict[int, Study] = {}
    for (key,), group in pooled.group_by(["taxon_key"], maintain_order=True):
        if key is None:
            continue
        shifts = group["per_decade"].to_numpy().astype(float)
        label = str(group["taxon_label"][0])
        rows = [
            Row(
                label=str(unit),
                value=_fmt(float(per_decade), "°lat per decade"),
                detail=f"{int(years)} years, {_direction(float(per_decade))}",
            )
            for unit, per_decade, years in zip(
                group["survey_unit"], group["per_decade"], group["years"], strict=True
            )
        ]

        north = int((shifts > FLAT_DEGREES).sum())
        south = int((shifts < -FLAT_DEGREES).sum())
        # The sentence is built from the counts rather than chosen from a list, because the
        # interesting case -- one species going both ways -- is the one a hand-written headline
        # would forget to cover.
        if north and south:
            headline = (
                f"{label} moved north in {north} "
                f"{'survey' if north == 1 else 'surveys'} and south in {south}."
            )
        elif north:
            headline = f"{label} moved north in every survey long enough to measure it."
        elif south:
            headline = f"{label} moved south in every survey long enough to measure it."
        else:
            headline = f"{label} stayed where it was, in every survey long enough to measure it."

        studies[int(key)] = Study(
            kind="shift",
            headline=headline,
            value=_fmt(float(np.median(shifts)), "°latitude per decade"),
            detail=(
                f"Median across {len(rows)} bottom-trawl "
                f"{'survey' if len(rows) == 1 else 'surveys'}, "
                f"each at least {MIN_YEARS} years long."
            ),
            caveat=(
                "A trawl survey samples trawlable ground, in a fixed season. A species that moved "
                "into rocky habitat, or moved its timing rather than its place, would not show up "
                "here at all."
            ),
            method="docs/methods/phase1b-marine.md",
            source_id=phase1b.SOURCE_ID,
            taxon=label,
            rows=rows,
        )
    log.info("%d marine species carry a distribution shift", len(studies))
    return studies


def tracked_studies() -> dict[int, Study]:
    """One study per tracked mammal the gate will publish, plus what Phase 1d found out.

    The sensor break is the result worth carrying here. Phase 1d could not fit a timing trend to
    any of these animals, and the reason is not that they were not followed for long enough -- it
    is that changing a radio collar for a GPS collar moves the measured date by 46.8 days against a
    trend of order one day per decade.
    """
    studies: dict[int, Study] = {}
    for source_id in lake_sources(EvidenceType.TRACK):
        source = catalog.get(source_id)
        if source.taxon_scope is None:  # pragma: no cover -- a TRACK source always has one
            msg = f"{source_id} is a track source with no taxon scope; it cannot be cleared."
            raise RuntimeError(msg)
        scope = source.taxon_scope
        frame = (
            scan(EvidenceType.TRACK, source_id=source_id)
            .group_by("taxon_key", "taxon_label")
            .agg(
                fixes=pl.len(),
                individuals=pl.col("individual_id").n_unique(),
                first=pl.col("timestamp").dt.year().min(),
                last=pl.col("timestamp").dt.year().max(),
                sensors=pl.col("sensor_type").n_unique(),
            )
            .collect()
        )
        for key, label, fixes, individuals, first, last, sensors in frame.iter_rows():
            if key is None:
                continue
            try:
                clear_for_publication(
                    source_id=source_id,
                    evidence_type=EvidenceType.TRACK,
                    realm=source.realm,
                    sensitivity=source.sensitivity_for(
                        taxon_key=int(key), evidence_type=EvidenceType.TRACK, realm=source.realm
                    ),
                    taxon_scope=scope,
                    taxon_key=int(key),
                    redistribution_allowed=source.redistribution.allowed,
                )
            except PublicationRefusedError:
                # Handled by `withheld_studies`, which says so by name rather than leaving a gap.
                continue

            existing = studies.get(int(key))
            rows = [
                *(existing.rows if existing else []),
                Row(
                    label=source.title,
                    value=f"{individuals} tracked",
                    detail=f"{first}-{last}, {fixes:,} fixes, {sensors} sensor type(s)",
                ),
            ]
            studies[int(key)] = Study(
                kind="tracked",
                headline=(
                    f"{label} has been followed by collar, and the record cannot say whether its "
                    "timing has changed."
                ),
                value=f"{sum(int(row.value.split()[0]) for row in rows)} animals tracked",
                detail=(
                    "Individual tracks, never published as locations: every published surface is "
                    "gridded and delayed, and this card carries no coordinate at all."
                ),
                caveat=(
                    "Collar effort is not a measured denominator -- a collar goes on an animal "
                    "someone could catch, in a place they could reach, in a year that was funded. "
                    "And swapping a radio collar for a GPS collar moves the measured date by 46.8 "
                    "days, against a trend of order one day per decade."
                ),
                method="docs/methods/phase1d-tracks.md",
                source_id=source_id,
                taxon=str(label),
                rows=rows,
            )
    log.info("%d tracked species carry a study", len(studies))
    return studies


def withheld_studies() -> dict[int, Study]:
    """The animals the lake holds and the gate refuses to draw.

    Re-derived rather than listed. If the gate ever cleared one of these, this raises instead of
    quietly publishing a page that says "withheld" over a species the exporter is drawing.
    """
    from migratlas.reports.detectability import WITHHELD_SOURCES  # noqa: PLC0415

    studies: dict[int, Study] = {}
    for source_id in WITHHELD_SOURCES:
        source = catalog.get(source_id)
        if source.taxon_scope is None:  # pragma: no cover -- as above
            msg = f"{source_id} is listed as withheld and has no taxon scope to be withheld under."
            raise RuntimeError(msg)
        scope = source.taxon_scope
        for rule in source.taxon_sensitivity:
            sensitivity = source.sensitivity_for(rule.taxon_key)
            try:
                clear_for_publication(
                    source_id=source_id,
                    evidence_type=EvidenceType.TRACK,
                    realm=source.realm,
                    sensitivity=sensitivity,
                    taxon_scope=scope,
                    taxon_key=rule.taxon_key,
                    redistribution_allowed=source.redistribution.allowed,
                )
            except PublicationRefusedError:
                pass
            else:
                msg = (
                    f"{source_id}/{rule.taxon_key} is published as withheld and the gate cleared "
                    f"it. Either the classification changed or this page is stale."
                )
                raise RuntimeError(msg)

            frame = (
                scan(EvidenceType.TRACK, source_id=source_id)
                .filter(pl.col("taxon_key") == rule.taxon_key)
                .select(
                    label=pl.col("taxon_label").drop_nulls().first(),
                    fixes=pl.len(),
                    individuals=pl.col("individual_id").n_unique(),
                    first=pl.col("timestamp").dt.year().min(),
                    last=pl.col("timestamp").dt.year().max(),
                )
                .collect()
            )
            if frame.is_empty() or not frame["fixes"][0]:
                continue
            label = str(frame["label"][0] or rule.taxon_key)
            studies[rule.taxon_key] = Study(
                kind="withheld",
                headline=f"{label} is in this project's data, and none of it is drawn.",
                value=f"{int(frame['fixes'][0]):,} locations held back",
                detail=(
                    f"{int(frame['individuals'][0])} animals, {int(frame['first'][0])}-"
                    f"{int(frame['last'][0])}, classified {sensitivity.value}."
                ),
                caveat=rule.rationale,
                method="docs/methods/tracks-and-sensitivity.md",
                source_id=source_id,
                taxon=label,
            )
    log.info("%d species are held and drawn nowhere", len(studies))
    return studies


def _published_taxa(root: Path) -> dict[int, tuple[str, str, str]]:
    """Every taxon with a surface on the globe: key -> (scientific, vernacular, layer)."""
    index = json.loads((root / "taxon-index.json").read_text(encoding="utf-8"))
    return {
        int(entry["key"]): (entry["scientific"], entry["vernacular"], entry["layer"])
        for entry in index["taxa"]
    }


def collect(root: Path) -> list[SpeciesCard]:
    """Every species card, from the lake and from what was actually published."""
    drawn = _published_taxa(root)
    shifts = marine_studies()
    tracked = tracked_studies()
    withheld = withheld_studies()

    names: dict[int, tuple[str, str]] = {
        key: (scientific, vernacular) for key, (scientific, vernacular, _layer) in drawn.items()
    }
    realms = {"shift": "marine", "tracked": "terrestrial", "withheld": "terrestrial"}

    cards: dict[int, SpeciesCard] = {}
    for key in sorted({*drawn, *shifts, *tracked, *withheld}):
        found = (shifts.get(key), tracked.get(key), withheld.get(key))
        studies = [study for study in found if study]
        scientific, vernacular = names.get(key, ("", ""))
        if not scientific:
            # From whichever study knows a name, for a species that is measured and not drawn.
            # Never from a row label: those are survey names, and reading one as a species name
            # put a bottom-trawl programme on the Atlantic mackerel's page.
            scientific = next((study.taxon for study in studies if study.taxon), str(key))

        if not studies:
            studies = [
                Study(
                    kind="extent",
                    headline=f"{scientific} is recorded here, and nothing here measures it.",
                    value="",
                    detail=(
                        "The sources that cover this animal are a single pooled period, so there "
                        "is no second point to compare against and no trend to fit."
                    ),
                    caveat=(
                        "Absence of a result is not a result. This says the data cannot answer "
                        "the question, not that the answer is no."
                    ),
                    method="docs/methods/detectability.md",
                    source_id="",
                )
            ]

        realm = next((realms[s.kind] for s in studies if s.kind in realms), "marine")
        cards[key] = SpeciesCard(
            taxon_key=key,
            scientific=scientific,
            vernacular=vernacular,
            realm=realm,
            drawn=key in drawn,
            studies=studies,
        )
    return list(cards.values())


def write_index(cards: list[SpeciesCard], root: Path) -> int:
    """The searchable entries for animals that have a study and no surface.

    A second file rather than an addition to `taxon-index.json`, and the reason is a scar: two
    commands writing one index is how 3,072 taxa were once silently replaced by thirty. One writer
    per file. The frontend loads both and searches the union.

    Without this, 689 of the 755 species carrying a measured distribution shift are unreachable --
    FISHGLOB is a survey, not a published layer, so the animals this project has the most to say
    about could not be found in its own search box.
    """
    entries = [
        {
            "key": card.taxon_key,
            "scientific": card.scientific,
            "vernacular": card.vernacular,
            # No surface, and the frontend has to know rather than infer: an empty layer is the
            # difference between "here is what is known" and a failed fetch reported as an error.
            "layer": "",
            "layer_title": "study only",
            "cells": 0,
            "shard": card.taxon_key % SHARDS,
            "studied": True,
        }
        for card in sorted(cards, key=lambda card: card.taxon_key)
        if not card.drawn and any(study.kind != "extent" for study in card.studies)
    ]
    body = json.dumps(
        {"shards": SHARDS, "taxa": entries}, ensure_ascii=False, separators=(",", ":")
    )
    (root / "species-index.json").write_text(body + "\n", encoding="utf-8")
    log.info("%d studied taxa are searchable without a surface", len(entries))
    return len(body)


def _key_of(card: dict[str, object]) -> int:
    key = card["taxon_key"]
    return key if isinstance(key, int) else 0


def write(cards: list[SpeciesCard], root: Path) -> int:
    """Write the sharded study documents. Returns bytes written."""
    shards: dict[int, list[dict[str, object]]] = defaultdict(list)
    for card in cards:
        shards[card.taxon_key % SHARDS].append(asdict(card))

    written = 0
    for shard in range(SHARDS):
        # Sorted, and every shard written even when empty: a missing file is a 404 in the browser,
        # and an unordered one makes every rebuild touch all 64 for no reason.
        payload = {
            "schema_version": SCHEMA_VERSION,
            "species": sorted(shards.get(shard, []), key=_key_of),
        }
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        (root / f"species-study-{shard:02d}.json").write_text(body + "\n", encoding="utf-8")
        written += len(body)
    return written
