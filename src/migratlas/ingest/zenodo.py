"""Zenodo record metadata, with the distinction between concept and version DOIs."""

from dataclasses import dataclass
from typing import Any

import httpx

from migratlas.ingest.http import USER_AGENT, Checksum, RemoteFile

API = "https://zenodo.org/api"


@dataclass(frozen=True, slots=True)
class Record:
    """One Zenodo record version.

    ``version_doi`` pins an exact snapshot; ``concept_doi`` always resolves to whatever is
    newest. Provenance must cite the version, or a reader cannot reconstruct what we
    actually used.
    """

    record_id: str
    version_doi: str
    concept_doi: str
    version: str
    title: str
    published: str
    files: dict[str, RemoteFile]


def record(record_id: str) -> Record:
    """Fetch a record's metadata and file list with published checksums."""
    with httpx.Client(timeout=60.0, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(f"{API}/records/{record_id}")
        response.raise_for_status()
        payload: dict[str, Any] = response.json()

    files = {
        entry["key"]: RemoteFile(
            url=entry["links"]["self"],
            name=entry["key"],
            size=entry.get("size"),
            checksum=_checksum_of(entry),
        )
        for entry in payload.get("files", [])
    }
    meta = payload.get("metadata", {})
    return Record(
        record_id=str(payload.get("id", record_id)),
        version_doi=str(payload.get("doi", "")),
        concept_doi=str(payload.get("conceptdoi", "")),
        version=str(meta.get("version", "")),
        title=str(meta.get("title", "")),
        published=str(meta.get("publication_date", "")),
        files=files,
    )


def _checksum_of(entry: dict[str, Any]) -> Checksum | None:
    """Zenodo reports checksums as ``<algorithm>:<hex>``."""
    raw = str(entry.get("checksum", ""))
    algorithm, _, hexdigest = raw.partition(":")
    if not algorithm or not hexdigest:
        return None
    return Checksum(algorithm=algorithm, hexdigest=hexdigest)
