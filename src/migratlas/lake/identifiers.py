"""SQL identifier quoting, and time-ordered run ids."""

import re
from string.templatelib import Interpolation, Template
from uuid import uuid7

_SAFE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class UnsafeIdentifierError(ValueError):
    """An identifier could not be safely used in SQL."""


def new_run_id() -> str:
    """A time-ordered identifier for one ingest or build run.

    UUIDv7 rather than v4 so provenance records sort chronologically on the key alone,
    and a directory listing comes out in the order things happened.
    """
    return str(uuid7())


def quote_identifier(name: str) -> str:
    """Quote a table or column name for DuckDB.

    Rejects anything that is not a plain identifier instead of trying to escape it.
    Everything this project generates is machine-made from the evidence schemas, so a
    name needing exotic quoting means something upstream is wrong rather than that the
    quoting needs to be cleverer.
    """
    if not _SAFE.match(name):
        msg = (
            f"Refusing to use {name!r} as a SQL identifier. Identifiers must match "
            f"{_SAFE.pattern} -- this one was probably built from untrusted input."
        )
        raise UnsafeIdentifierError(msg)
    return f'"{name}"'


def render_sql(template: Template) -> str:
    """Render a t-string into SQL, quoting every interpolated identifier.

    DuckDB binds *values* as parameters but not *identifiers*, so table and column names
    have to be interpolated. A t-string keeps that interpolation in one auditable place::

        render_sql(t"SELECT {col} FROM {table}")

    Values must still go through real parameter binding; this is for identifiers only.
    """
    parts: list[str] = []
    for item in template:
        if isinstance(item, Interpolation):
            parts.append(quote_identifier(str(item.value)))
        else:
            parts.append(item)
    return "".join(parts)
