"""Machine-local paths and credentials, overridable via ``MIGRATLAS_*`` env vars."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Final

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingCredentialError(RuntimeError):
    """A source needs a credential that has not been supplied."""


_CREDENTIAL_PREFIX: Final = "CRED_"


def _dotenv() -> dict[str, str]:
    """MIGRATLAS_ assignments from ``.env``, read directly rather than through the model.

    Two reasons the file is parsed here. Credentials are deliberately not model fields, so
    pydantic-settings never exposes their values; and with extras ignored, a typo that lives only
    in .env would otherwise be invisible. Minimal on purpose -- ``NAME=value``, optional matching
    quotes, ``#`` comments -- because a fuller dotenv dialect is a dependency, not a feature.
    """
    dotenv = Path(".env")
    if not dotenv.is_file():
        return {}

    values: dict[str, str] = {}
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        name = name.strip().upper()
        if not name.startswith("MIGRATLAS_"):
            continue
        value = value.strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name] = value
    return values


def _prefixed_environment() -> set[str]:
    """MIGRATLAS_ variable names from the real environment and from ``.env``, upper-cased."""
    return {name.upper() for name in os.environ if name.upper().startswith("MIGRATLAS_")} | set(
        _dotenv()
    )


# Free-text hints only, so this stays a lookup table rather than logic.
_CREDENTIAL_HINTS: Final[dict[str, str]] = {
    "ebird_api_key": "Request one at https://ebird.org/st/request",
    "movebank_user": "Register free at https://www.movebank.org",
    "movebank_password": "Register free at https://www.movebank.org",
}


class Settings(BaseSettings):
    """Resolved runtime settings."""

    # `extra="ignore"`, not "forbid", because credentials share the MIGRATLAS_ namespace on
    # purpose and are deliberately not fields -- a field would put a secret in a repr, a log line
    # or a pydantic validation error. `_reject_unknown_settings` below restores the typo
    # detection that "forbid" was there for, without pulling credentials into the model.
    model_config = SettingsConfigDict(
        env_prefix="MIGRATLAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
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

    @model_validator(mode="after")
    def _reject_unknown_settings(self) -> Settings:
        """Fail on a misspelled MIGRATLAS_ variable, while allowing the credential namespace.

        A typo in MIGRATLAS_DATA_DIR is silent data loss -- the lake quietly appears somewhere
        else -- so unknown settings must be an error. Credentials are exempt because they are
        intentionally not fields; anything else under the prefix is a mistake.
        """
        known = {f"MIGRATLAS_{name.upper()}" for name in type(self).model_fields}
        unknown = sorted(
            name
            for name in _prefixed_environment()
            if name not in known and not name.startswith(f"MIGRATLAS_{_CREDENTIAL_PREFIX}")
        )
        if unknown:
            msg = (
                f"Unknown MIGRATLAS_ setting(s): {', '.join(unknown)}. Known settings are "
                f"{', '.join(sorted(known))}, and credentials must be named "
                f"MIGRATLAS_{_CREDENTIAL_PREFIX}<NAME>."
            )
            raise ValueError(msg)
        return self

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
        var = f"MIGRATLAS_{_CREDENTIAL_PREFIX}{name.upper()}"
        # A real environment variable wins, so a shell can override the file without editing it.
        value = os.environ.get(var) or _dotenv().get(var)
        if not value:
            hint = _CREDENTIAL_HINTS.get(name.lower(), "")
            msg = f"Missing credential: set {var} in your environment or .env file. {hint}".strip()
            raise MissingCredentialError(msg)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
