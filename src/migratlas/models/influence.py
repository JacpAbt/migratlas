"""Does a cross-unit slope survive losing any one unit?

ADR 0016. Phase 3g asked this once, unregistered, after its result was in, and the answer decided
what the phase could claim: dropping one unit of sixteen took its slope from `-0.054 +/- 0.041` to
`-0.021 +/- 0.030` and it stopped clearing zero, so the phase published nothing. No other phase in
this project has ever asked, and three carry the same exposure -- an 18-unit regression, a 16-unit
one, and a set of ten group means.

The rule this module exists to make mechanical: **on a panel small enough for one unit to matter, a
verdict that does not survive the removal of any single unit is not a verdict.** It is stated as a
property of the estimate rather than of the estimator, so it applies to any cross-unit fit whatever
its design matrix, and it is computed by refitting rather than by a hat-matrix shortcut -- weights,
standardisation and a pseudoinverse all change when a row leaves, and an analytic influence measure
that assumed they did not would be answering a different question.

What it is not: an outlier test. Phase 3g's extreme unit was real -- the Gulf of St Lawrence deep
channel is among the best-documented cases of shelf deoxygenation anywhere and the ingested values
agreed with that literature unprompted. A true extreme with high leverage is worse than a bad point,
not better, because there is nothing to clean and the fit still rests on it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

# Above this many units, one row cannot plausibly carry a slope and the refits are noise. The
# figure is the order of magnitude Phase 3g, 3e and 1m all sit below rather than a threshold tuned
# against any of them: 16, 18 and 10 units.
SMALL_PANEL: Final = 30


@dataclass(frozen=True, slots=True)
class Influence:
    """What leaving each unit out in turn does to one coefficient."""

    units: int
    slope: float
    """The full-panel coefficient."""
    ci: float
    """The full-panel 95% half-width."""
    clears_at_full: bool
    """Whether the full panel's interval excludes zero."""
    survivals: tuple[tuple[str, float, float, bool], ...]
    """Per dropped unit: its name, the refitted slope and half-width, and whether it clears."""

    @property
    def small_panel(self) -> bool:
        """Whether the rule applies at all. Above the floor, one row cannot carry a slope."""
        return self.units < SMALL_PANEL

    @property
    def survives(self) -> bool:
        """True when every refit keeps the full panel's verdict, in the same direction."""
        return all(
            clears and (slope < 0) == (self.slope < 0) for _, slope, _, clears in self.survivals
        )

    @property
    def carried_by_one(self) -> bool:
        """The failure this measures: the panel clears zero and one unit is why."""
        return self.clears_at_full and not self.survives

    @property
    def publishable(self) -> bool:
        """The rule. A non-clearing estimate is unaffected -- a null has no leverage to lose."""
        return not (self.small_panel and self.carried_by_one)

    def worst(self) -> tuple[str, float, float] | None:
        """The unit whose removal moves the coefficient furthest, for the caveat to name."""
        if not self.survivals:
            return None
        name, slope, ci, _ = max(self.survivals, key=lambda row: abs(row[1] - self.slope))
        return (name, slope, ci)


def leave_one_out[T](
    units: Sequence[T],
    refit: Callable[[Sequence[T]], tuple[float, float]],
    *,
    name: Callable[[T], str],
) -> Influence | None:
    """Refit without each unit in turn and report what the coefficient does.

    `refit` takes a subset and returns `(slope, ci)` for the coefficient under test, so the caller
    keeps its own design, weights and standardisation and this function never has to know them.
    Returns None below three units, where dropping one leaves nothing to fit.
    """
    minimum = 3
    if len(units) < minimum:
        return None
    slope, ci = refit(units)
    survivals = []
    for index, unit in enumerate(units):
        rest = [item for position, item in enumerate(units) if position != index]
        one_slope, one_ci = refit(rest)
        survivals.append((name(unit), one_slope, one_ci, abs(one_slope) > one_ci))
    return Influence(
        units=len(units),
        slope=slope,
        ci=ci,
        clears_at_full=abs(slope) > ci,
        survivals=tuple(survivals),
    )
