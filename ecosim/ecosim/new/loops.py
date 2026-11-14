"""Models that feed each other within a step. The server starts a model only when all its inputs have a value, so it could start none of them."""

from __future__ import annotations

from ecosim.new.delayed_input import DelayedInput
from ecosim.new.wiring import Connection
from ecosim.report_lines import and_joined


def ensure_no_loop(connections: tuple[Connection, ...], delayed: list[DelayedInput]) -> None:
    """Raises ValueError with the connections of every loop and the inputs whose delay breaks it."""
    loops = loops_of(connections=connections, delayed=delayed)
    if not loops:
        return
    lines = []
    for loop in loops:
        models = sorted({connection.input.model for connection in loop})
        lines.append(f"{and_joined(texts=models)} feed each other, so the server could start none of them:")
        lines += [f"  {connection.input}  <-  {connection.output}" for connection in loop]
    delays = [f"--logical-delay {connection.input}" for loop in loops for connection in breaking_connections(loop=loop)]
    raise ValueError("\n".join([*lines, "Give inputs the value of the step before to break the loop, for example:", f"  {' '.join(delays)}"]))


def loops_of(connections: tuple[Connection, ...], delayed: list[DelayedInput]) -> list[list[Connection]]:
    """The connections without a delay of each group of models that reach each other through them."""
    delayed_inputs = [delayed_input.input for delayed_input in delayed]
    direct = [connection for connection in connections if connection.input not in delayed_inputs]
    feeds: dict[str, set[str]] = {}
    for connection in direct:
        feeds.setdefault(connection.output.model, set()).add(connection.input.model)
    reachable = {model: _reachable_from(model=model, feeds=feeds) for model in feeds}
    groups = {frozenset(other for other in reachable if other in reachable[model] and model in reachable[other]) for model in reachable}
    return [
        [connection for connection in direct if {connection.input.model, connection.output.model} <= group]
        for group in sorted(groups, key=sorted)
        if len(group) > 1
    ]


def breaking_connections(loop: list[Connection]) -> list[Connection]:
    """The connections out of the one model whose delay breaks the loop, from the model with the fewest of them, else all of the loop."""
    output_models = sorted(
        {connection.output.model for connection in loop},
        key=lambda model: (sum(connection.output.model == model for connection in loop), model),
    )
    for model in output_models:
        others = tuple(connection for connection in loop if connection.output.model != model)
        if not loops_of(connections=others, delayed=[]):
            return [connection for connection in loop if connection.output.model == model]
    return loop


def _reachable_from(model: str, feeds: dict[str, set[str]]) -> set[str]:
    reached: set[str] = set()
    waiting = list(feeds.get(model, ()))
    while waiting:
        current = waiting.pop()
        if current not in reached:
            reached.add(current)
            waiting.extend(feeds.get(current, ()))
    return reached
