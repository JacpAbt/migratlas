"""Decisions that more than one module has to agree about.

Not a dumping ground for every literal in the project. What belongs here is narrow and testable:
a value that **two or more modules must share or a published result becomes wrong**. Anything a
single module owns stays with that module — each driver's `SOURCE_ID`, each ingest's `EFFORT_UNIT`,
each report's own `SEED` — because moving those here would couple every module to one file and
teach a reader nothing.

Why it exists at all. Every constant below was previously defined twice, in two modules, with the
same value and no link between them. That arrangement works right up until somebody changes one
copy, and then it fails silently and in the worst possible way: the analysis and the layer, or the
fetch and the fit, go on running and quietly stop describing the same thing. The project had already
met this once and solved it locally — `CLAIM_BAND` was pinned by a test asserting the two copies
were equal — but seven others had no such pin.

**Changing a value here changes a published number.** Each one records which, so nobody moves a
floor on a hunch.
"""

from typing import Final

# --- The radar network's window -----------------------------------------------------------------

CONUS_LAT: Final[tuple[float, float]] = (24.0, 50.0)
CONUS_LON: Final[tuple[float, float]] = (-125.0, -66.0)
"""The contiguous United States, as Horton et al. 2020 drew it.

Shared by the radar analysis and by the eBird ingest, which exists to cross-check that analysis
over the same ground. Two different boxes would make the cross-check compare two regions and
report the difference as a finding about birds.
"""

MIN_COVERAGE: Final = 0.9
"""Least share of a night a station must have observed for that night to be usable.

Shared by every phenology report and by `tiles/layers.py`, which builds the published surface. If
these disagreed, the map would draw a different set of nights than the claim beside it is computed
from — and the project's own rule is that the picture and the regression must not be able to
disagree.
"""

MIN_NIGHTS: Final = 40
"""Least usable nights in a season-year for that unit to enter a fit.

Lives here beside `MIN_COVERAGE` because the two are one decision about what counts as an observed
season, and splitting them across files is how one gets changed alone.
"""

CLAIM_BAND: Final[tuple[int, int]] = (37, 50)
"""The latitude band the aerial claim is published in, and the only band attributed.

Phase 1c found a latitude-graded step around 2012 that survived four candidate explanations; this
band is where that step is near zero and the estimate is stable across all three robustness tests.
Shared by the attribution fit, the confound sandbox and the response dial, all three of which
report numbers *for this band* and would otherwise be free to report them for different ones.
"""

# --- The registered windows ---------------------------------------------------------------------

PRE_SEASON: Final[tuple[int, ...]] = (6, 7)
"""June and July: the pre-season window the attribution was pre-registered on.

Chosen to sit before the August-November passage window without touching it, because a predictor
overlapping the response is partly the response. Shared by `phase2a_timing`, which fits the thermal
sensitivity `S` over these months, and by `drivers/cmip6`, which fetches the counterfactual
temperature for them. If those two drifted apart, `S` would be fitted on one window and multiplied
by warming measured over another, and the attribution would be wrong while looking fine.
"""

TARGET_YEARS: Final[tuple[int, ...]] = tuple(range(2017, 2025))
"""The eight years the Phase 3d dress rehearsal stood at and was graded on.

Shared by `drivers/seas5`, which fetches the forecast actually issued in each of those Junes, and
by `phase3d`, which grades the prediction against what happened. A mismatch would grade a
prediction for a year whose forecast was never fetched.
"""

# --- Names in the data contract -----------------------------------------------------------------

CHANGE_VARIABLE: Final = "surface_water_change_km2"
"""The driver column the JRC surface-water ingest writes and Phase 1g reads.

A column name shared between a writer and a reader, which is the most dangerous kind of duplicate:
rename it in the ingest alone and the report reads an empty frame. Phase 1g published a null, so an
empty read would have looked exactly like the result it reported.
"""

# --- Physical -----------------------------------------------------------------------------------

EARTH_KM: Final = 6371.0088
"""Mean Earth radius, IUGG. Shared by the track cleaner and the displacement report, which have to
measure the same journey the same way.
"""
