"""The green-up date: the timing metric Phase 3a registers for the yearly NDVI series.

The green-wave tile collapses 41 years to a 24-bin climatology; the models need the years back.
The metric is defined here, alone and tested, before the reduction that will apply it to the
PKU archives is built — the definition is what `phase3a-skill.md` binds to, and a metric that
lived inside a 2.4 GB batch job would be a metric nobody could test in milliseconds.

Midpoint-of-amplitude is the standard green-up definition precisely because it is relative: a
dark conifer cell and a bright tundra cell green up on their own scales, and an absolute
threshold would hand the date to the brightness rather than the timing.
"""

from typing import Final

import numpy as np

from migratlas.tiles import greenwave

VARIABLE: Final = "greenup_day_of_year"

# A cell whose seasonal swing is smaller than this has no green-up to date: deserts, ice and
# evergreen canopy produce crossings that are noise crossing noise. NDVI units, the product's
# 0-1 scale.
MIN_AMPLITUDE: Final = 0.1

# Every bin of the year must hold data before a crossing date is trusted: a year whose winter
# half-months are missing would place its "first crossing" wherever the gap ends.
BINS_PER_YEAR: Final = greenwave.HALF_MONTHS


def greenup_day(values: np.ndarray) -> float | None:
    """Day of year when NDVI first crosses the midpoint of this year's amplitude, or None.

    ``values`` is one cell-year: 24 half-month means in order. None when any bin is missing (a
    gap would masquerade as timing), when the amplitude is below MIN_AMPLITUDE (nothing to
    date), or when the year opens already green — southern-hemisphere seasons put the crossing
    in the previous calendar year, and pretending day 1 was the green-up would fabricate a
    series with no variance. Linear interpolation inside the crossing bin, so the answer is a
    day rather than a half-month: consumers difference these across years, and a 15-day
    quantum would swallow the signal it exists to carry.
    """
    if values.shape != (BINS_PER_YEAR,) or np.isnan(values).any():
        return None
    low, high = float(values.min()), float(values.max())
    if high - low < MIN_AMPLITUDE:
        return None
    midpoint = low + (high - low) / 2.0
    above = values >= midpoint
    if above[0]:
        return None
    index = int(np.argmax(above))
    span = float(values[index] - values[index - 1])
    fraction = 0.5 if span == 0 else float(midpoint - values[index - 1]) / span
    return ((index - 1) + fraction + 0.5) * (365.0 / BINS_PER_YEAR)
