"""Machine-local paths and credentials, overridable via ``MIGRATLAS_*`` env vars."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Final

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingCredentialError(RuntimeError):
    """A source needs a credential that has not been supplied."""


# Free-text hints only, so this stays a lookup table rather than logic.
_CREDENTIAL_HINTS: Final[dict[str, str]] = {
    "ebird_api_key": "Request one at https://ebird.org/st/request",
    "movebank_user": "Register free at https://www.movebank.org",
    "movebank_password": "Register free at https://www.movebank.org",
}


class Settings(BaseSettings):
    """Resolved runtime settings."""

    model_config = SettingsConfigDict(
        env_prefix="MIGRATLAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # Under $HOME rather than the working tree: the raw data runs to tens of
    # gigabytes and the repo may sit on a slower mount.
    data_dir: Path = Field(default=Path.home() / "migratlas-data")

    # Raw archives can live somewhere bulkier and slower than the working set, because
    # they are written once and read sequentially. See ADR 0004.
    raw_data_dir: Path | None = Field(default=None)

    @field_validator("data_dir", "raw_data_dir")
    @classmethod
    def _expand(cls, value: Path | None) -> Path | None:
        return value.expanduser() if value else value

    @property
    def raw_dir(self) -> Path:
        """Downloads exactly as the provider served them; never read by analysis.

        Separately configurable via ``MIGRATLAS_RAW_DATA_DIR`` so bulk archives can sit
        on a big slow disk while the lake stays on fast local storage.
        """
        return self.raw_data_dir or (self.data_dir / "raw")

    @property
    def lake_dir(self) -> Path:
        """Canonical evidence tables as hive-partitioned Parquet."""
        return self.data_dir / "lake"

    @property
    def derived_dir(self) -> Path:
        """Metrics and model outputs."""
        return self.data_dir / "derived"

    @property
    def tiles_dir(self) -> Path:
        """Publishable tiles. Everything here has passed the redaction gate."""
        return self.data_dir / "tiles"

    @property
    def cache_dir(self) -> Path:
        """HTTP and API response cache."""
        return self.data_dir / "cache"

    @property
    def duckdb_path(self) -> Path:
        """Working database of views over Parquet; not a source of truth."""
        return self.data_dir / "migratlas.duckdb"

    def ensure_dirs(self) -> None:
        """Create the lake skeleton. Idempotent."""
        for path in (self.raw_dir, self.lake_dir, self.derived_dir, self.tiles_dir, self.cache_dir):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def credential(name: str) -> str:
        """Read ``MIGRATLAS_CRED_<NAME>``, or raise explaining how to supply it.

        Not model fields: a field per source would put source-specific knowledge in
        the core, and secrets that are never fields cannot leak through a repr.
        """
        var = f"MIGRATLAS_CRED_{name.upper()}"
        value = os.environ.get(var)
        if not value:
            hint = _CREDENTIAL_HINTS.get(name.lower(), "")
            msg = f"Missing credential: set {var} in your environment or .env file. {hint}".strip()
            raise MissingCredentialError(msg)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
