"""SABAP2: the second Southern African Bird Atlas, via the GBIF download API.

25,687,526 records over 2007-2026, and the late half of the atlas-against-atlas comparison
`sabap1.py` provides the early half of. Two routes were tested on 2026-07-30 and only this one
works, which is recorded in docs/methods/geographic-coverage.md:

- The publisher's own IPT at `aduipt.uct.ac.za:8080` times out, on the archive and on its small EML
  alike. Treat the advertised DwC-A as unavailable.
- The atlas's API (`api.birdmap.africa`) serves per-pentad card counts and reporting rates, already
  split by protocol, but **pooled over 2007-present** with no per-year endpoint. Good for a map,
  useless for a series.
- The GBIF download API works, needs a free account, and issues a **DOI per download** -- which is
  better provenance than either archive, because it pins the exact records a result was computed on.

Downloads are asynchronous: a request is queued, GBIF prepares an archive over minutes to hours, and
the key it returns is the handle. So this module submits and polls rather than blocking.

**The Darwin Core archive, after SIMPLE_CSV turned out to be insufficient.** SIMPLE_CSV was asked
for first, on the belief that `catalogNumber` carried the card id. It does not: in the download it
repeats `occurrenceID` (`urn:fiao:sabap2:fullprot:rid10002350`). Reading the search API's own fields
back in order shows where the card id actually lives:

| field | content | in SIMPLE_CSV? |
| --- | --- | --- |
| `occurrenceID` | `urn:fiao:sabap2:fullprot:rid...` — carries the **protocol** | yes |
| `fieldNotes` | `2215_1730_004876_20201115` — the **card**: pentad, observer, date | **no** |
| `eventRemarks` | `TotalHour observing:3 ...` — hours per card | **no** |
| `verbatimLocality` | `2215_1730` — the **pentad** | **no** |

The card is the effort denominator, so a download without it cannot produce a reporting rate. The
pentad *is* recoverable from the coordinates -- they are pentad centroids on a 1/12 degree grid,
with a sub-arcsecond offset from `COORDINATE_ROUNDED` -- but the card is not recoverable from
anything. A proxy of (pentad, observer, date) would split a card that spans several days, and a
full-protocol card may cover its pentad over up to five, so the proxy would inflate effort by an
unknown factor and do it unevenly between observers.

What SIMPLE_CSV does get right, and what is worth keeping: GBIF's `taxonKey` and `speciesKey` are
*accepted* backbone keys, so this source needs no name resolution and cannot inherit the synonym
problem `sabap1.py` ran into. The DwC-A carries those too, beside the verbatim fields.
"""

import logging
from typing import TYPE_CHECKING, Any, Final

from migratlas.config import get_settings

if TYPE_CHECKING:
    from pathlib import Path

    import httpx

log = logging.getLogger(__name__)

SOURCE_ID: Final = "sabap2"
API: Final = "https://api.gbif.org/v1"

DATASET_KEY: Final = "906e6978-e292-4a8b-9c39-adf6bb0f3323"
"""SABAP2 on GBIF. Not 282d0ccb-..., which is SABAP1 -- the docs named the wrong one until
2026-07-30, and the two atlases are twenty years apart."""

FORMAT: Final = "DWCA"
"""The archive format. See the module docstring: SIMPLE_CSV omits the card id and so cannot produce
an effort denominator."""

SIMPLE_CSV_KEY: Final = "0018183-260721160103020"
"""The first download, kept for the record rather than used.

25,687,526 records, 2.35 GiB, doi 10.15468/dl.8zjvpv. Requested in SIMPLE_CSV on the mistaken belief
that `catalogNumber` held the card id; it holds a copy of `occurrenceID`. Left here because a
superseded download is part of the provenance, and because re-requesting it would be the obvious
mistake to make twice."""

# GBIF asks that a client identify itself, and a download is attributable to an account.
USER_AGENT: Final = "migratlas (+https://github.com/JacpAbt/migratlas)"

TIMEOUT_S: Final = 60.0


class DownloadError(RuntimeError):
    """GBIF refused a request or a download."""


def predicate() -> dict[str, Any]:
    """Every record in the SABAP2 dataset, and nothing else.

    Deliberately not filtered further. Restricting to the full protocol here would bake an analysis
    decision into the archive the DOI refers to, and the ad-hoc records are needed anyway -- to be
    excluded knowingly, and to be counted when saying how many were excluded.
    """
    return {"type": "equals", "key": "DATASET_KEY", "value": DATASET_KEY}


def _client() -> httpx.Client:
    import httpx  # noqa: PLC0415 -- a runtime dependency of this module only

    settings = get_settings()
    return httpx.Client(
        base_url=API,
        timeout=TIMEOUT_S,
        headers={"User-Agent": USER_AGENT},
        # The password, never a field on anything and never logged. GBIF's download API has no
        # separate key, which is why config.py's hint says to put it in .env and nowhere else.
        auth=(settings.credential("gbif_user"), settings.credential("gbif_password")),
        follow_redirects=True,
    )


def request_download(*, notify: bool = False) -> str:
    """Queue the download and return its key.

    The key is the only thing worth keeping from this call: it is how the archive is polled, fetched
    and cited, and GBIF keeps a prepared download for six months.
    """
    body = {
        "creator": get_settings().credential("gbif_user"),
        "sendNotification": notify,
        "format": FORMAT,
        "predicate": predicate(),
    }
    with _client() as http:
        response = http.post("/occurrence/download/request", json=body)
        if response.status_code >= 400:  # noqa: PLR2004 -- httpx has no constant for this
            msg = (
                f"GBIF refused the download request ({response.status_code}): {response.text[:200]}"
            )
            raise DownloadError(msg)
        key = response.text.strip()
    log.info("queued GBIF download %s for dataset %s", key, DATASET_KEY)
    return key


def status(key: str) -> dict[str, Any]:
    """What GBIF says about a queued download: its status, size, record count and DOI."""
    with _client() as http:
        response = http.get(f"/occurrence/download/{key}")
        if response.status_code >= 400:  # noqa: PLR2004 -- httpx has no constant for this
            msg = f"GBIF would not describe download {key} ({response.status_code})"
            raise DownloadError(msg)
        payload: dict[str, Any] = response.json()
    return payload


def describe(key: str) -> str:
    """One line about a download, for a CLI or a log."""
    found = status(key)
    size = found.get("size") or 0
    return (
        f"{key}: {found.get('status')} | {found.get('totalRecords', 0):,} records | "
        f"{size / 1024**2:.0f} MiB | doi {found.get('doi', '-')}"
    )


def fetch_archive(key: str) -> Path:
    """Download a prepared archive, resuming if a previous attempt was cut short.

    The archive URL is public once the download has succeeded, so this needs no credential -- and
    the DOI is what a result should cite, not the key. Refuses a download that is not ready rather
    than saving GBIF's "not finished" response as a zip.
    """
    from migratlas.ingest.http import RemoteFile, fetch  # noqa: PLC0415 -- avoids a cycle

    found = status(key)
    state = found.get("status")
    if state != "SUCCEEDED":
        msg = f"download {key} is {state}, not SUCCEEDED -- nothing to fetch yet"
        raise DownloadError(msg)

    log.info(
        "fetching %s: %s records, %.2f GiB, doi %s",
        key,
        f"{found.get('totalRecords', 0):,}",
        (found.get("size") or 0) / 1024**3,
        found.get("doi", "-"),
    )
    remote = RemoteFile(
        url=f"{API}/occurrence/download/request/{key}.zip",
        name=f"{key}.zip",
    )
    return fetch(remote, SOURCE_ID)
