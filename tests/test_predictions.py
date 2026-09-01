"""The drift guard on the prediction record.

`predictions.yaml` is authored rather than parsed, for the reason its own header gives: the notes
grade in prose and eight of them use wording a regex misses. Authored data needs a guard, and the
guard that matters is completeness -- a phase must not be able to go uncounted by being forgotten,
which is exactly how the README's own counts drifted twice.
"""

from pathlib import Path

from migratlas.reports import predictions

METHODS = Path(__file__).resolve().parents[1] / "docs" / "methods"


def _listed(score: predictions.Score) -> list[str]:
    return [
        *(phase.note for phase in score.phases),
        *(note for note, _ in score.pending),
        *(note for note, _ in score.excluded),
    ]


def test_every_method_note_is_accounted_for() -> None:
    """Counted, pending, or excluded with a reason. Silence is not an option.

    This is the whole point of the file. A new phase that lands without an entry here would leave
    the published failure rate quietly describing an older, smaller project.
    """
    on_disk = {path.name for path in METHODS.glob("*.md")}
    listed = set(_listed(predictions.load()))

    assert not on_disk - listed, f"method notes with no entry: {sorted(on_disk - listed)}"
    assert not listed - on_disk, f"entries naming no note: {sorted(listed - on_disk)}"


def test_no_note_is_counted_twice() -> None:
    listed = _listed(predictions.load())
    assert len(listed) == len(set(listed)), "a note appears in more than one section"


def test_every_phase_accounts_for_all_of_its_predictions() -> None:
    """True plus false plus ungradeable is the number registered, per phase and in total."""
    score = predictions.load()
    for phase in score.phases:
        assert phase.consistent, (
            f"{phase.note}: {phase.graded_true} + {phase.graded_false} + {phase.ungradeable} "
            f"!= {phase.registered}"
        )
    assert score.graded + score.ungradeable == score.registered


def test_the_excluded_notes_each_carry_a_reason() -> None:
    for note, why in predictions.load().excluded:
        assert why.strip(), f"{note} is excluded with no reason given"


def test_the_convention_is_still_testing_something() -> None:
    """An alarm rather than a target.

    A project that registered only predictions it was sure of would show a failure rate near zero
    and would look, from outside, exactly like a project that was always right. If this ever fires,
    the thing to check is whether the predictions got safer -- not whether the bar is too high.
    """
    score = predictions.load()
    assert score.failure_rate > predictions.MEANINGFUL_FAILURE_RATE, (
        f"only {score.failure_rate:.1%} of graded predictions failed"
    )


def test_the_score_is_not_carried_by_one_phase() -> None:
    """Dropping any single phase must leave the rate above the floor.

    ADR 0016's rule, applied to this project's claim about itself: a failure rate that rests on one
    unlucky phase is a statement about that phase.
    """
    score = predictions.load()
    for dropped in score.phases:
        graded = score.graded - dropped.graded
        failed = score.graded_false - dropped.graded_false
        if not graded:
            continue
        assert failed / graded > predictions.MEANINGFUL_FAILURE_RATE, (
            f"without {dropped.note} the rate is {failed / graded:.1%}"
        )
