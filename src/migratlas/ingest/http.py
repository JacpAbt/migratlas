"""Resumable, checksum-verified downloads into the raw archive."""

import hashlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from migratlas.config import get_settings

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

USER_AGENT = "migratlas/0.1 (+https://github.com/JacpAbt/migratlas)"
CHUNK = 1 << 20


class ChecksumMismatchError(RuntimeError):
    """A download completed but did not match its published checksum."""


@dataclass(frozen=True, slots=True)
class RemoteFile:
    """A file to fetch, with the checksum its publisher stated."""

    url: str
    name: str
    size: int | None = None
    md5: str | None = None


def raw_path(source_id: str, name: str) -> Path:
    """Where a source's raw download lives."""
    return get_settings().raw_dir / source_id / name


def fetch(remote: RemoteFile, source_id: str, *, force: bool = False) -> Path:
    """Download ``remote`` if needed and return the local path.

    Resumes a partial download with a Range request rather than starting again, which
    matters when a single archive is several gigabytes over a domestic connection.
    Verifies the published MD5 before declaring success, so a truncated or corrupted
    file fails here rather than halfway through parsing.
    """
    destination = raw_path(source_id, remote.name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")

    if destination.exists() and not force:
        if remote.md5 and _md5(destination) != remote.md5:
            log.warning("%s exists but checksum differs; re-downloading", destination.name)
        else:
            size_mib = destination.stat().st_size / 2**20
            log.info("%s already present (%.1f MiB)", remote.name, size_mib)
            return destination

    already = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": USER_AGENT}
    if already:
        headers["Range"] = f"bytes={already}-"
        log.info("resuming %s at %.1f MiB", remote.name, already / 2**20)

    client = httpx.Client(timeout=httpx.Timeout(30.0, read=300.0), follow_redirects=True)
    with client, client.stream("GET", remote.url, headers=headers) as response:
        # A server that ignores the Range header sends 200 and the whole file, in
        # which case appending would corrupt it.
        if already and response.status_code == httpx.codes.OK:
            log.warning("server ignored Range; restarting %s", remote.name)
            already = 0
            partial.unlink(missing_ok=True)
        response.raise_for_status()

        mode = "ab" if already else "wb"
        with partial.open(mode) as handle:
            for chunk in response.iter_bytes(CHUNK):
                handle.write(chunk)

    if remote.md5:
        actual = _md5(partial)
        if actual != remote.md5:
            msg = (
                f"{remote.name} failed checksum: expected {remote.md5}, got {actual}. "
                f"Partial file kept at {partial} for inspection."
            )
            raise ChecksumMismatchError(msg)

    partial.replace(destination)
    log.info("fetched %s (%.1f MiB)", remote.name, destination.stat().st_size / 2**20)
    return destination


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()
