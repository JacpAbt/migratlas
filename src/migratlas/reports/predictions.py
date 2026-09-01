"""How often this project's own registered predictions turned out wrong.

The convention `CLAUDE.md` calls the most valuable thing in the repository is pre-registration:
numbered falsifiable predictions fixed before the fetch, graded in the same note whichever way they
went, and a wrong one recorded as a correction rather than edited away. The project had been doing
that for two months and had never published the score.

**A convention nobody scores is a habit.** This is the score, computed from
``docs/methods/predictions.yaml`` -- authored rather than parsed, because the notes grade in prose
and eight of them use wording a regex misses entirely. `tests/test_predictions.py` is the drift
guard: every method note must be listed as counted, pending or excluded-with-a-reason, so a phase
cannot go uncounted by being forgotten.

The failure rate is meant to be high. A registration that only ever confirms was not testing
anything, and the interesting thing about this number is not its size but that it exists at all.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml

log = logging.getLogger(__name__)

LEDGER: Final = Path(__file__).resolve().parents[3] / "docs" / "methods" / "predictions.yaml"

MEANINGFUL_FAILURE_RATE: Final = 0.15
"""Below this the convention has stopped testing anything, and the guard says so.

Not a target and not a threshold anyone should aim at -- an alarm. A project registering only
predictions it was sure of would show a rate near zero, and would look from outside exactly like a
project that was always right.
"""


@dataclass(frozen=True, slots=True)
class Phase:
    """One phase's grading record."""

    note: str
    registered: int
    graded_true: int
    graded_false: int
    ungradeable: int
    stop_conditions_fired: int
    comment: str | None

    @property
    def graded(self) -> int:
        return self.graded_true + self.graded_false

    @property
    def consistent(self) -> bool:
        """Every registered prediction is accounted for exactly once."""
        return self.graded + self.ungradeable == self.registered

    @property
    def failure_rate(self) -> float:
        return self.graded_false / self.graded if self.graded else float("nan")


@dataclass(frozen=True, slots=True)
class Score:
    """The whole record."""

    phases: tuple[Phase, ...]
    pending: tuple[tuple[str, int], ...]
    excluded: tuple[tuple[str, str], ...]

    @property
    def registered(self) -> int:
        return sum(phase.registered for phase in self.phases)

    @property
    def graded(self) -> int:
        return sum(phase.graded for phase in self.phases)

    @property
    def graded_false(self) -> int:
        return sum(phase.graded_false for phase in self.phases)

    @property
    def ungradeable(self) -> int:
        return sum(phase.ungradeable for phase in self.phases)

    @property
    def fired(self) -> int:
        return sum(phase.stop_conditions_fired for phase in self.phases)

    @property
    def failure_rate(self) -> float:
        return self.graded_false / self.graded if self.graded else float("nan")

    @property
    def pending_predictions(self) -> int:
        return sum(count for _, count in self.pending)

    @property
    def all_consistent(self) -> bool:
        return all(phase.consistent for phase in self.phases)

    @property
    def phases_wholly_wrong(self) -> int:
        """Phases where nothing gradeable held. The ones a habit would never produce."""
        return sum(1 for phase in self.phases if phase.graded and not phase.graded_true)

    @property
    def phases_wholly_right(self) -> int:
        """And the other tail, which is the one to be suspicious of."""
        return sum(1 for phase in self.phases if phase.graded and not phase.graded_false)


def load(path: Path = LEDGER) -> Score:
    """Read the authored record. No estimation happens here and none should."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    phases = tuple(
        Phase(
            note=str(entry["note"]),
            registered=int(entry["registered"]),
            graded_true=int(entry["true_"]),
            graded_false=int(entry["false_"]),
            ungradeable=int(entry["ungradeable"]),
            stop_conditions_fired=int(entry["stop_conditions_fired"]),
            comment=entry.get("comment"),
        )
        for entry in document["phases"]
    )
    return Score(
        phases=phases,
        pending=tuple(
            (str(entry["note"]), int(entry["registered"])) for entry in document["pending"]
        ),
        excluded=tuple((str(entry["note"]), str(entry["why"])) for entry in document["excluded"]),
    )


def render() -> str:
    """The score, worst-graded phase first, with one verdict line at the end."""
    score = load()
    out = [
        "How often the registered predictions were wrong",
        "=" * 78,
        "Authored in docs/methods/predictions.yaml and guarded against drift, because the notes",
        "grade in prose and a regex over that undercounts -- the first attempt found 65 graded",
        "predictions where a careful read finds 102.",
        "",
        f"{'note':34s} {'reg':>4s} {'true':>5s} {'false':>6s} {'ungr':>5s} "
        f"{'fail':>6s} {'stop':>5s}",
    ]
    for phase in sorted(score.phases, key=lambda item: (-item.failure_rate, item.note)):
        rate = f"{phase.failure_rate:.0%}" if phase.graded else "n/a"
        out.append(
            f"{phase.note:34s} {phase.registered:4d} {phase.graded_true:5d} "
            f"{phase.graded_false:6d} {phase.ungradeable:5d} {rate:>6s} "
            f"{phase.stop_conditions_fired:5d}"
        )
    out += [
        "",
        f"{len(score.phases)} phases graded. {score.registered} predictions registered, "
        f"{score.graded} graded, {score.ungradeable} never gradeable.",
        f"**{score.graded_false} of {score.graded} graded predictions were wrong: "
        f"{score.failure_rate:.1%}.**",
        f"{score.fired} registered stop conditions fired and changed what was published.",
        f"{score.phases_wholly_wrong} phases had nothing gradeable hold; "
        f"{score.phases_wholly_right} had nothing fail.",
        f"{score.pending_predictions} predictions are registered and not yet run, across "
        f"{len(score.pending)} phases.",
        f"{len(score.excluded)} notes are excluded with a stated reason.",
        "",
    ]
    if not score.all_consistent:
        broken = [phase.note for phase in score.phases if not phase.consistent]
        out.append(f"VERDICT: the record does not add up for {', '.join(broken)}.")
        return "\n".join(out)
    healthy = score.failure_rate > MEANINGFUL_FAILURE_RATE
    out.append(
        f"VERDICT: {score.failure_rate:.1%} of graded predictions failed, "
        f"{'above' if healthy else 'BELOW'} the {MEANINGFUL_FAILURE_RATE:.0%} below which a "
        "registration has stopped testing anything."
    )
    return "\n".join(out)
