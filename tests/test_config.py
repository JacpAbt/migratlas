"""Path resolution, including the raw/working-set split from ADR 0004."""

from pathlib import Path

import pytest

from migratlas.config import MissingCredentialError, Settings


@pytest.fixture(autouse=True)
def _isolate_from_machine_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Describe the code, not whichever machine runs the suite.

    ``.env`` is resolved relative to the working directory, so stepping outside the repo
    is enough to ignore it; the environment variables have to be cleared explicitly.
    """
    monkeypatch.chdir(tmp_path)
    for name in ("MIGRATLAS_DATA_DIR", "MIGRATLAS_RAW_DATA_DIR"):
        monkeypatch.delenv(name, raising=False)


def _settings(data_dir: Path = Path("/data"), raw_data_dir: Path | None = None) -> Settings:
    return Settings(data_dir=data_dir, raw_data_dir=raw_data_dir)


def test_derived_paths_hang_off_data_dir() -> None:
    s = _settings()
    assert s.lake_dir == Path("/data/lake")
    assert s.derived_dir == Path("/data/derived")
    assert s.tiles_dir == Path("/data/tiles")
    assert s.cache_dir == Path("/data/cache")
    assert s.duckdb_path == Path("/data/migratlas.duckdb")


def test_raw_defaults_under_data_dir() -> None:
    assert _settings().raw_dir == Path("/data/raw")


def test_raw_can_be_relocated_independently() -> None:
    """The point of ADR 0004: bulk archives on a big slow disk, working set on fast local
    storage."""
    s = _settings(raw_data_dir=Path("/mnt/bulk/raw"))
    assert s.raw_dir == Path("/mnt/bulk/raw")
    # Relocating raw must not drag anything else with it.
    assert s.lake_dir == Path("/data/lake")
    assert s.duckdb_path == Path("/data/migratlas.duckdb")


def test_ensure_dirs_creates_both_locations(tmp_path: Path) -> None:
    s = _settings(data_dir=tmp_path / "work", raw_data_dir=tmp_path / "bulk" / "raw")
    s.ensure_dirs()
    assert s.lake_dir.is_dir()
    assert s.raw_dir.is_dir()


def test_ensure_dirs_is_idempotent(tmp_path: Path) -> None:
    s = _settings(data_dir=tmp_path)
    s.ensure_dirs()
    s.ensure_dirs()
    assert s.lake_dir.is_dir()


def test_tilde_is_expanded() -> None:
    s = Settings(data_dir=Path("~/somewhere"), raw_data_dir=Path("~/bulk"))
    assert "~" not in str(s.data_dir)
    assert "~" not in str(s.raw_dir)


# --- Credentials -------------------------------------------------------------
def test_missing_credential_names_the_variable_and_where_to_get_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MIGRATLAS_CRED_EBIRD_API_KEY", raising=False)
    with pytest.raises(MissingCredentialError) as exc:
        Settings.credential("ebird_api_key")
    message = str(exc.value)
    assert "MIGRATLAS_CRED_EBIRD_API_KEY" in message
    assert "ebird.org/st/request" in message


def test_credential_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIGRATLAS_CRED_SOME_TOKEN", "abc123")
    assert Settings.credential("some_token") == "abc123"


def test_credentials_are_not_model_fields() -> None:
    """Secrets that are never fields cannot leak through a repr or a settings dump."""
    assert not any("cred" in name.lower() for name in Settings.model_fields)
