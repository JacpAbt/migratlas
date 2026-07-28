"""Pytest configuration. Tests that reach outside the repo -- to a remote source, or to
operator-placed raw files -- are opt-in, so the suite never fails for reasons unrelated to
the code."""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="Run tests that hit real remote data sources.",
    )
    parser.addoption(
        "--run-localdata",
        action="store_true",
        default=False,
        help="Run tests that need operator-placed raw files.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for marker in ("network", "localdata"):
        if config.getoption(f"--run-{marker}"):
            continue
        skip = pytest.mark.skip(reason=f"needs --run-{marker}")
        for item in items:
            if marker in item.keywords:
                item.add_marker(skip)
