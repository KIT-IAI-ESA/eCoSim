from __future__ import annotations

from ecosim.new.delayed_input import DelayedInput
from ecosim.new.input_connections import Connection
from ecosim.report_lines import and_joined


def ensure_no_loop(connections: tuple[Connection, ...], delayed: list[DelayedInput]) -> None:
    # the server starts a model only when all its inputs have a value
    loops = loops_of(connections=connections, delayed=delayed)
    if not loops:
        return
    lines = []
    for loop in loops:
        models = sorted({connection.input.model for connection in loop})
        lines.append(f"{and_joined(texts=models)} form a loop:")
        lines += [f"  {connection.input}  <-  {connection.output}" for connection in loop]
    delays = [f"--logical-delay {connection.input}" for loop in loops for connection in breaking_connections(loop=loop)]
    raise ValueError("\n".join([*lines, "Break the loop with a logical delay, for example:", f"  {' '.join(delays)}"]))


def loops_of(connections: tuple[Connection, ...], delayed: list[DelayedInput]) -> list[list[Connection]]:
    """Returns the connections without a delay of each group of models that reach each other."""
    delayed_inputs = [delayed_input.input for delayed_input in delayed]
    direct = [connection for connection in connections if connection.input not in delayed_inputs]
    connected_models: dict[str, set[str]] = {}
    for connection in direct:
        connected_models.setdefault(connection.output.model, set()).add(connection.input.model)
    reachable = {model: _reachable_from(model=model, connected_models=connected_models) for model in connected_models}
    groups = {frozenset(other for other in reachable if other in reachable[model] and model in reachable[other]) for model in reachable}
    return [
        [connection for connection in direct if {connection.input.model, connection.output.model} <= group]
        for group in sorted(groups, key=sorted)
        if len(group) > 1
    ]


def breaking_connections(loop: list[Connection]) -> list[Connection]:
    """Returns the connections out of the one model whose delay breaks the loop, else all of the loop."""
    output_models = sorted(
        {connection.output.model for connection in loop},
        key=lambda model: (sum(connection.output.model == model for connection in loop), model),
    )
    for model in output_models:
        others = tuple(connection for connection in loop if connection.output.model != model)
        if not loops_of(connections=others, delayed=[]):
            return [connection for connection in loop if connection.output.model == model]
    return loop


def _reachable_from(model: str, connected_models: dict[str, set[str]]) -> set[str]:
    reached: set[str] = set()
    waiting = list(connected_models.get(model, ()))
    while waiting:
        current = waiting.pop()
        if current not in reached:
            reached.add(current)
            waiting.extend(connected_models.get(current, ()))
    return reached
