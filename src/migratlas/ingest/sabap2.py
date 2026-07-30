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

**SIMPLE_CSV rather than the Darwin Core archive**, for two reasons beyond size. It carries GBIF's
own `taxonKey` and `speciesKey`, which are *accepted* backbone keys -- so this source needs no name
resolution and cannot inherit the synonym problem `sabap1.py` ran into. And everything the design
needs survives in it: `catalogNumber` embeds the pentad and the card ("2215_1730_004876_20201115" is
pentad, observer, date), `occurrenceID` carries "fullprot" or "adhocprot", and the coordinates are
pentad centroids. What it drops is `fieldNotes`, which holds hours-observed per card -- a refinement
on the card as the effort unit, not a requirement of it.
"""

import logging
from typing import TYPE_CHECKING, Any, Final

from migratlas.config import get_settings

if TYPE_CHECKING:
    import httpx

log = logging.getLogger(__name__)

SOURCE_ID: Final = "sabap2"
API: Final = "https://api.gbif.org/v1"

DATASET_KEY: Final = "906e6978-e292-4a8b-9c39-adf6bb0f3323"
"""SABAP2 on GBIF. Not 282d0ccb-..., which is SABAP1 -- the docs named the wrong one until
2026-07-30, and the two atlases are twenty years apart."""

FORMAT: Final = "SIMPLE_CSV"

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
