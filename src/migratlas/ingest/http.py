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
class Checksum:
    """A publisher-stated digest. Repositories differ: Zenodo states MD5, Dryad SHA-256."""

    algorithm: str
    hexdigest: str

    def __post_init__(self) -> None:
        if self.normalised_algorithm not in hashlib.algorithms_available:
            msg = f"Unsupported checksum algorithm: {self.algorithm!r}"
            raise ValueError(msg)

    @property
    def normalised_algorithm(self) -> str:
        """``sha-256`` and ``SHA256`` both mean ``sha256`` to hashlib."""
        return self.algorithm.replace("-", "").replace("_", "").lower()

    def of(self, path: Path) -> str:
        """Digest ``path`` with this algorithm."""
        digest = hashlib.new(self.normalised_algorithm, usedforsecurity=False)
        with path.open("rb") as handle:
            while chunk := handle.read(CHUNK):
                digest.update(chunk)
        return digest.hexdigest()

    def matches(self, path: Path) -> bool:
        return self.of(path).lower() == self.hexdigest.lower()


@dataclass(frozen=True, slots=True)
class RemoteFile:
    """A file to fetch, with the checksum its publisher stated."""

    url: str
    name: str
    size: int | None = None
    checksum: Checksum | None = None


class FileNotPlacedError(RuntimeError):
    """A source requires a manually placed file that is not there yet."""


def raw_path(source_id: str, name: str) -> Path:
    """Where a source's raw download lives."""
    return get_settings().raw_dir / source_id / name


def require_local(
    source_id: str,
    name: str,
    *,
    checksum: Checksum | None = None,
    instructions: str = "",
) -> Path:
    """Return a file the operator must supply by hand, or explain how to supply it.

    Some academic repositories gate downloads behind interactive authentication, so a
    pipeline cannot fetch them unattended. Rather than pretend otherwise, those sources
    declare the requirement explicitly and fail with instructions naming the exact path.
    The published checksum is still verified, so provenance is no weaker than an
    automated fetch -- only the acquisition step is manual.

    Raises:
        FileNotPlacedError: if the file is absent, or present but fails its checksum.
    """
    path = raw_path(source_id, name)
    if not path.exists():
        msg = f"{name} is not present. Place it at:\n  {path}\n{instructions}".rstrip()
        raise FileNotPlacedError(msg)

    if checksum and not checksum.matches(path):
        msg = (
            f"{path} failed {checksum.algorithm}: expected {checksum.hexdigest}, "
            f"got {checksum.of(path)}. The file is corrupt or is not the published version."
        )
        raise FileNotPlacedError(msg)

    log.info("using operator-placed %s (%.2f MiB)", name, path.stat().st_size / 2**20)
    return path


def fetch(remote: RemoteFile, source_id: str, *, force: bool = False) -> Path:
    """Download ``remote`` if needed and return the local path.

    Resumes a partial download with a Range request rather than starting again, which
    matters when a single archive is several gigabytes over a domestic connection.
    Verifies the published checksum before declaring success, so a truncated or corrupted
    file fails here rather than halfway through parsing.
    """
    destination = raw_path(source_id, remote.name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")

    if destination.exists() and not force:
        if remote.checksum and not remote.checksum.matches(destination):
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

    if remote.checksum and not remote.checksum.matches(partial):
        msg = (
            f"{remote.name} failed {remote.checksum.algorithm}: expected "
            f"{remote.checksum.hexdigest}, got {remote.checksum.of(partial)}. "
            f"Partial file kept at {partial} for inspection."
        )
        raise ChecksumMismatchError(msg)

    partial.replace(destination)
    log.info("fetched %s (%.1f MiB)", remote.name, destination.stat().st_size / 2**20)
    return destination
