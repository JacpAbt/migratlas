"""GBIF Backbone client. The project's taxonomy spine for every kingdom."""

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Final

import httpx

API: Final = "https://api.gbif.org/v1"
USER_AGENT: Final = "migratlas/0.1 (+https://github.com/JacpAbt/migratlas)"

_ACCEPTABLE_MATCHES: Final = frozenset({"EXACT", "FUZZY"})
_MIN_CONFIDENCE: Final = 90


@dataclass(frozen=True, slots=True)
class TaxonMatch:
    """A name resolved against the Backbone."""

    usage_key: int
    """The *accepted* usage, following the Backbone's own redirect where the name is a synonym.

    Not the key the name itself carries. A spine that returned synonym keys would give two sources
    two different keys for one taxon whenever they used different names for it -- so a join across
    them would silently drop the species rather than fail. SABAP1 is where this showed up: its
    ``Psalidoprocne holomelas`` is a synonym of the subspecies ``Psalidoprocne pristoptera
    holomelas``, and anything else calling that bird by its current name would not have met it.
    """
    scientific_name: str
    canonical_name: str
    rank: str
    status: str
    """As GBIF reported it for the name asked about, so a synonym stays visible in the audit trail
    even though ``usage_key`` points at the accepted taxon."""
    match_type: str
    confidence: int

    @property
    def is_synonym(self) -> bool:
        return self.status != "ACCEPTED"


class TaxonomyError(RuntimeError):
    """A name could not be resolved to an acceptable Backbone match."""


def client(timeout: float = 20.0) -> httpx.Client:
    """An httpx client identifying itself, as GBIF's terms ask."""
    return httpx.Client(
        base_url=API,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


def match_name(http: httpx.Client, name: str) -> TaxonMatch:
    """Resolve a scientific name to a Backbone usage key.

    Refuses low-confidence and HIGHERRANK matches rather than returning a genus when
    asked for a species: a silently wrong key would attach the wrong sensitivity
    policy downstream.
    """
    response = http.get("/species/match", params={"name": name, "strict": "false"})
    response.raise_for_status()
    payload: dict[str, Any] = response.json()

    match_type = str(payload.get("matchType", "NONE"))
    confidence = int(payload.get("confidence", 0))
    usage_key = payload.get("usageKey")

    if usage_key is None or match_type not in _ACCEPTABLE_MATCHES:
        msg = f"No acceptable GBIF match for {name!r} (matchType={match_type})"
        raise TaxonomyError(msg)
    if confidence < _MIN_CONFIDENCE:
        msg = f"Low-confidence GBIF match for {name!r} (confidence={confidence})"
        raise TaxonomyError(msg)

    # Follow the Backbone to the accepted usage. See TaxonMatch.usage_key for why a synonym key
    # would be worse than useless across two sources that name the same bird differently.
    accepted = payload.get("acceptedUsageKey")
    return TaxonMatch(
        usage_key=int(accepted if accepted is not None else usage_key),
        scientific_name=str(payload.get("scientificName", name)),
        canonical_name=str(payload.get("canonicalName", name)),
        rank=str(payload.get("rank", "UNRANKED")),
        status=str(payload.get("status", "UNKNOWN")),
        match_type=match_type,
        confidence=confidence,
    )


# Banding and ringing codes ("WHST", "BWTE") are published as vernacular names but are
# not what anyone types into a search box.
_CODE = re.compile(r"^[A-Z0-9]{2,6}$")


@dataclass(frozen=True, slots=True)
class TaxonNames:
    """What the Backbone calls a taxon, looked up by key rather than by a source's own label.

    Both names come from one usage record, which is the point. A source's `taxon_label` is
    whatever that dataset happened to publish, and 95 keys in this lake carry two or more of
    them -- *Grus canadensis* and *Antigone canadensis* are one bird and one key. Showing a
    reader whichever spelling the build read first is a coin toss, so the display name is
    resolved from the key instead.
    """

    scientific: str
    vernacular: str
    """Empty when GBIF publishes no usable English name, which is a real answer and is cached."""


def names_for(http: httpx.Client, usage_key: int, *, language: str = "eng") -> TaxonNames:
    """Both display names for one usage key, in two requests rather than three.

    The species record carries the canonical name and the curated vernacular, and the
    vernacularNames list is needed to corroborate the latter -- so they are fetched together
    rather than by two callers each paying for the detail record.
    """
    candidates = _published_names(http, usage_key, language)

    detail = http.get(f"/species/{usage_key}")
    detail.raise_for_status()
    record: dict[str, Any] = detail.json()
    curated = clean_vernacular(str(record.get("vernacularName", "")))

    # The curated field carries no language guarantee -- for the hoary bat it returns
    # "Eisgraue Haarschwanzfledermaus" -- so it counts only when corroborated by the
    # language-filtered list.
    vernacular = (
        titlecase(curated)
        if curated and not _CODE.match(curated) and curated.casefold() in candidates
        else _most_published_name(candidates)
    )
    return TaxonNames(
        scientific=str(record.get("canonicalName") or record.get("scientificName") or ""),
        vernacular=vernacular or "",
    )


def vernacular_name(http: httpx.Client, usage_key: int, *, language: str = "eng") -> str | None:
    """Best common name for a taxon, or ``None`` if GBIF has none.

    Prefers the curated ``vernacularName`` on the species record. The full
    vernacularNames list is a poor substitute: it pools every regional name ever
    published, so picking by frequency yields "Maneater" for the great white shark and
    "Kelt" — a post-spawning condition, not a species — for Atlantic salmon.
    """
    return names_for(http, usage_key, language=language).vernacular or None


_QUALIFIER = re.compile(r"[\[(][^\])]*[\])]")


def clean_vernacular(name: str) -> str:
    """Reduce a GBIF vernacular string to one plain name.

    The field is not always a single name: bluefin tuna arrives as
    "Atlantic Bluefin Tuna, Northern Bluefin Tuna, Blue-fin Tunny", and the monarch as
    "Milkweed [butterfly]". Take the first alternative and drop any bracketed
    qualifier.
    """
    first = re.split(r"[,;/]", name, maxsplit=1)[0]
    return " ".join(_QUALIFIER.sub(" ", first).split())


def _published_names(http: httpx.Client, usage_key: int, language: str) -> Counter[str]:
    """Case-folded counts of published names in one language.

    Folding matters: "Great white shark" and "Great White Shark" are the same name and
    would otherwise split the vote against a single-published oddity.
    """
    response = http.get(f"/species/{usage_key}/vernacularNames", params={"limit": 100})
    response.raise_for_status()
    results: list[dict[str, Any]] = response.json().get("results", [])

    counts: Counter[str] = Counter()
    for entry in results:
        if entry.get("language") != language:
            continue
        name = clean_vernacular(str(entry.get("vernacularName", "")))
        if name and not _CODE.match(name):
            counts[name.casefold()] += 1
    return counts


def _most_published_name(candidates: Counter[str]) -> str | None:
    if not candidates:
        return None
    # Ties broken by shorter name: "White Stork" over "European White Stork".
    best = max(candidates.items(), key=lambda kv: (kv[1], -len(kv[0])))[0]
    return titlecase(best)


def titlecase(name: str) -> str:
    """Capitalise each word without mangling hyphens or apostrophes the way
    ``str.title()`` does (it turns "Swainson's" into "Swainson'S")."""
    return " ".join(part[:1].upper() + part[1:] for part in name.split(" ") if part)
