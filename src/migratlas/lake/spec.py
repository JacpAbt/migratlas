"""What the lake needs to know about any table it stores.

The lake was built for evidence about animals, and drivers are not that: a sea-surface
temperature is a fact about water. Keeping them in separate tables is the honest modelling
choice, but they want identical storage machinery -- hive partitioning, zstd, idempotent
replacement, a manifest, and above all the schema-drift refusal, which exists because a mixed
directory is read by intersecting schemas and the newer columns vanish with no error.

So the writer, reader and drift check take anything shaped like this rather than an
``EvidenceSpec`` specifically. That is the whole purpose of this module.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import pyarrow as pa


@runtime_checkable
class TableSpec(Protocol):
    """A partitioned table the lake can store."""

    @property
    def name(self) -> str:
        """Directory name under the lake root."""

    @property
    def schema(self) -> pa.Schema: ...

    @property
    def partition_by(self) -> tuple[str, ...]: ...

    @property
    def time_column(self) -> str | None:
        """Column a derived ``year`` partition is computed from, if there is one."""

    def validate(self, table: pa.Table) -> None:
        """Raise if ``table`` does not conform."""
