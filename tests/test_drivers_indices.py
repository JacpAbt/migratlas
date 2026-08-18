"""The index parsers, pinned against embedded samples of each NOAA layout."""

import numpy as np

from migratlas.drivers.indices import FILES, _to_frame, parse_oni, parse_table
from migratlas.drivers.schema import DRIVER_SAMPLES

ONI_SAMPLE = """\
 SEAS   YR   TOTAL  ANOM
  DJF  1950  24.72 -1.53
  JFM  1950  25.17 -1.34
  NDJ  1950  25.24 -1.44
  DJF  1951  25.25 -1.19
"""

TABLE_SAMPLE = """\
  1950  0.92  0.40 -0.36  0.73 -0.59 -0.06 -1.26 -0.05  0.25  0.85 -1.26 -1.02
  1951  0.08  0.70 -1.02 -0.22 -0.59 -1.64  1.37 -0.22 -1.36  1.87 -0.39  1.32
  2026 -0.11  0.25  0.50  0.42  0.11  0.33  0.12 99.99 99.99 99.99 99.99 99.99
"""


def test_oni_seasons_map_to_their_centre_months() -> None:
    rows = parse_oni(ONI_SAMPLE)
    assert (1950, 1, -1.53) in rows
    assert (1950, 2, -1.34) in rows
    # NDJ centres on December of its own row's year.
    assert (1950, 12, -1.44) in rows
    assert len(rows) == 4


def test_table_years_carry_twelve_months_and_sentinels_drop() -> None:
    rows = parse_table(TABLE_SAMPLE)
    full_years = [row for row in rows if row[0] in (1950, 1951)]
    assert len(full_years) == 24
    current = [row for row in rows if row[0] == 2026]
    # The five sentinel months of the unfinished year are absences, not values.
    assert len(current) == 7
    assert all(abs(value) < 10 for _, _, value in rows)


def test_header_and_footer_lines_are_skipped_by_shape() -> None:
    noisy = "PDO Index derived from ERSST V5\nyear jan feb\n" + TABLE_SAMPLE + "\n-9999\n"
    assert len(parse_table(noisy)) == len(parse_table(TABLE_SAMPLE))


def test_samples_conform_to_the_driver_schema() -> None:
    frame = _to_frame(FILES[0], [(1950, 1, -1.53), (1950, 2, -1.34)])
    table = frame.select(DRIVER_SAMPLES.schema.names).to_arrow().cast(DRIVER_SAMPLES.schema)
    DRIVER_SAMPLES.validate(table)
    assert table.num_rows == 2
    # The coordinates are NaN by design: a mode has no place.
    assert np.isnan(table.column("longitude").to_pylist()).all()
