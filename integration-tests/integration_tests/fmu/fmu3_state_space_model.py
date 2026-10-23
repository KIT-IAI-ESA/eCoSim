"""
The expected outputs of the 'StateSpace' Reference FMU (FMI 3.0) with its default parameters, derived from its model
instead of recorded from a run. A = B = C = D = I and x0 = 0, so every vector component follows

    der(x) = x + u        y = x + u

The FMU integrates with forward Euler at a fixed solver step of 1 ms. Its 'doStep' loop stops before the solver step
that would pass the communication point, comparing times with 'isClose' (relative tolerance 1e-5) - from 100 s on that
tolerance is larger than a solver step, so the FMU does one extra solver step per communication step.

The tests feed u = factor * t at every communication point t (whole seconds), held for the step that ends there.
"""

from functools import cache

_SOLVER_STEP = 1e-3
_EPSILON = 1e-5


def _is_close(a: float, b: float) -> bool:
    return abs(a - b) <= _EPSILON or abs(a - b) <= _EPSILON * max(abs(a), abs(b))


def _passes(next_solver_time: float, communication_point: float) -> bool:
    return next_solver_time > communication_point and not _is_close(next_solver_time, communication_point)


@cache
def _state_at(second: int, factor: float) -> tuple[float, int]:
    """The state x and the number of solver steps done when the communication point 'second' is reached."""
    if second == 0:
        return 0.0, 0
    x, solver_steps = _state_at(second - 1, factor)
    while not _passes(solver_steps * _SOLVER_STEP + _SOLVER_STEP, second):
        x += _SOLVER_STEP * (x + factor * second)
        solver_steps += 1
    return x, solver_steps


def state_space_outputs(second: int, factors: tuple[float, ...]) -> list[float]:
    """The output vector y at the communication point 'second', for the inputs u = factor * second."""
    return [_state_at(second, factor)[0] + factor * second for factor in factors]
