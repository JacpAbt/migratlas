"""The ERA5 request cache, and the collision that cost a lake partition.

Nothing here talks to CDS. What is tested is the naming: the archive caches on the filename, so the
filename has to distinguish every request that would return different bytes.
"""

from migratlas.drivers import era5


def test_the_cache_name_changes_with_the_region() -> None:
    """The exact collision that overwrote a lake partition.

    The archive caches on filename. When the name carried only the variable, a southern request
    found the North American file "already present", skipped the download and sampled the wrong
    continent. Two regions must never share a name.
    """
    field = era5.FIELDS["temperature"]
    years, months = [2010], [1]
    north = era5.request_tag(field, years, months, era5.CONUS_AREA)
    south = era5.request_tag(field, years, months, era5.SABAP_AREA)
    assert north != south


def test_the_cache_name_changes_with_the_years_and_the_months() -> None:
    """Same class of collision, one dimension over: a shorter span reusing a longer one's file."""
    field = era5.FIELDS["temperature"]
    base = era5.request_tag(field, [2010, 2011], [1, 2], era5.CONUS_AREA)
    assert era5.request_tag(field, [2010], [1, 2], era5.CONUS_AREA) != base
    assert era5.request_tag(field, [2010, 2011], [1], era5.CONUS_AREA) != base


def test_the_cache_name_is_stable_for_the_same_request() -> None:
    """A tag that moved between runs would re-download the archive every time."""
    field = era5.FIELDS["precipitation"]
    first = era5.request_tag(field, [1995, 1996], [3, 4], era5.CONUS_AREA)
    second = era5.request_tag(field, [1996, 1995], [4, 3], era5.CONUS_AREA)
    assert first == second
