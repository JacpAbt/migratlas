"""The two-state model, on sequences simulated from a model whose answer is known.

A hidden Markov model is easy to write and easy to write wrongly, and the failures are quiet: a
forward pass that underflows returns a posterior of one half everywhere, and a label switch returns
the right model with its states swapped. Both would read as a result downstream, so both are tested.
"""

import numpy as np
import pytest

from migratlas.models import statespace


def _simulate(
    *,
    n: int = 1500,
    stay: float = 0.95,
    encamped: tuple[float, float] = (2.0, 0.05),
    travelling: tuple[float, float] = (3.0, 0.8),
    seed: int = 3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Steps from a known two-state chain. Returns steps, angles and the true states."""
    rng = np.random.default_rng(seed)
    states = np.zeros(n, dtype=int)
    for t in range(1, n):
        states[t] = states[t - 1] if rng.random() < stay else 1 - states[t - 1]
    steps = np.empty(n)
    angles = np.empty(n)
    for state, (shape, scale) in enumerate((encamped, travelling)):
        mask = states == state
        steps[mask] = rng.gamma(shape, scale, size=int(mask.sum()))
        # Encamped turns are tortuous and travelling turns are directed.
        spread = 2.0 if state == 0 else 0.4
        angles[mask] = rng.normal(np.pi if state == 0 else 0.0, spread, size=int(mask.sum()))
    return steps, np.arctan2(np.sin(angles), np.cos(angles)), states


def test_the_fit_recovers_the_two_means_it_was_simulated_from() -> None:
    steps, angles, _ = _simulate()
    model = statespace.fit([(steps, angles)])
    assert model is not None
    assert model.states[0].mean_step == pytest.approx(2.0 * 0.05, rel=0.35)
    assert model.states[1].mean_step == pytest.approx(3.0 * 0.8, rel=0.35)


def test_the_states_come_back_ordered_by_step_length_whatever_the_data() -> None:
    """A label switch returns the right model with every downstream fraction inverted."""
    for seed in (1, 2, 3, 4, 5):
        steps, angles, _ = _simulate(seed=seed)
        model = statespace.fit([(steps, angles)])
        assert model is not None
        assert model.states[0].mean_step < model.states[1].mean_step
        assert model.separation > 1.0


def test_the_posterior_finds_the_state_the_step_was_drawn_from() -> None:
    steps, angles, truth = _simulate()
    model = statespace.fit([(steps, angles)])
    assert model is not None
    posterior = statespace.decode(model, steps, angles)
    guessed = (posterior[:, 1] > 0.5).astype(int)
    assert (guessed == truth).mean() > 0.8


def test_a_long_sequence_does_not_underflow() -> None:
    """Unscaled, a forward pass over thousands of steps returns zeros and a flat posterior."""
    steps, angles, _ = _simulate(n=6000)
    model = statespace.fit([(steps, angles)])
    assert model is not None
    posterior = statespace.decode(model, steps, angles)
    assert np.isfinite(posterior).all()
    assert posterior[:, 1].std() > 0.1
    assert np.isfinite(model.log_likelihood)


def test_one_state_data_does_not_separate_and_says_so() -> None:
    """The guard prediction 2 rests on: a mixture that is not there must not look like one."""
    rng = np.random.default_rng(11)
    steps = rng.gamma(3.0, 0.5, size=2000)
    angles = rng.uniform(-np.pi, np.pi, size=2000)
    model = statespace.fit([(steps, angles)])
    assert model is not None
    assert model.separation < 3.0


def test_several_animals_share_one_model() -> None:
    sequences = [_simulate(n=600, seed=s)[:2] for s in (7, 8, 9)]
    model = statespace.fit(list(sequences))
    assert model is not None
    assert model.separation > 3.0
    assert model.transition.shape == (statespace.STATES, statespace.STATES)
    assert model.transition.sum(axis=1) == pytest.approx(np.ones(statespace.STATES))


def test_an_empty_or_degenerate_input_returns_none_rather_than_a_model() -> None:
    assert statespace.fit([]) is None
    assert statespace.fit([(np.array([1.0]), np.array([0.0]))]) is None


def test_the_fit_is_deterministic() -> None:
    steps, angles, _ = _simulate()
    first = statespace.fit([(steps, angles)])
    second = statespace.fit([(steps, angles)])
    assert first is not None
    assert second is not None
    assert first.states[1].mean_step == pytest.approx(second.states[1].mean_step, abs=1e-12)
    assert first.log_likelihood == pytest.approx(second.log_likelihood, abs=1e-9)
