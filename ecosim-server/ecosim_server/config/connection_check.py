from typing import Any

from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.tech.close_name import did_you_mean

_NOT_LISTED = "no logical delay in its delay_path lists it in output_connections, so it would never get a value"


def check_connections(raw_simulators: list[dict[str, Any]], raw_logical_delays: list[dict[str, Any]]) -> None:
    problems = connection_problems(raw_simulators=raw_simulators, raw_logical_delays=raw_logical_delays)
    if problems:
        lines = "\n".join(f"- {problem}" for problem in problems)
        raise RuntimeError(f"The simulation config has invalid connections:\n{lines}")


def connection_problems(raw_simulators: list[dict[str, Any]], raw_logical_delays: list[dict[str, Any]]) -> list[str]:
    return [
        f"simulator '{simulator['name']}', interface '{interface['name']}': {problem}"
        for own_index, simulator in enumerate(raw_simulators)
        for interface in simulator["interfaces"]
        for problem in _problems_of_interface(interface=interface, own_index=own_index, simulators=raw_simulators, delays=raw_logical_delays)
    ]


def _problems_of_interface(interface: dict[str, Any], own_index: int, simulators: list[dict[str, Any]], delays: list[dict[str, Any]]) -> list[str]:
    connections = interface.get("connected_to") or []
    if not isinstance(connections, list):
        return [f"connected_to must be a list, not {type(connections).__name__}"]
    if not connections and _is_input(interface):
        return ["the input has no connection in connected_to, so it would never get a value"]
    problems = [f"connected_to has {len(connections)} connections, only one is possible"] if len(connections) > 1 else []
    for connection in connections:
        problems += _problems_of_connection(connection=connection, own_interface=interface, own_index=own_index, simulators=simulators, delays=delays)
    return problems


def _problems_of_connection(
    connection: Any,
    own_interface: dict[str, Any],
    own_index: int,
    simulators: list[dict[str, Any]],
    delays: list[dict[str, Any]],
) -> list[str]:
    if not isinstance(connection, dict):
        return [f"a connection must be an object, not {type(connection).__name__}"]
    target_problem = _problem_of_target(connection=connection, own_interface=own_interface, own_index=own_index, simulators=simulators)
    own_simulator = simulators[own_index]["name"]
    delay_problems = _problems_of_delay_path(connection=connection, own_interface=own_interface, own_simulator=own_simulator, delays=delays)
    return [target_problem, *delay_problems] if target_problem else delay_problems


def _problem_of_target(connection: dict[str, Any], own_interface: dict[str, Any], own_index: int, simulators: list[dict[str, Any]]) -> str | None:
    target_index = _target_index(raw_index=connection.get("simulator"), simulator_count=len(simulators))
    if target_index is None:
        return f"simulator index '{connection.get('simulator')}' is not between 0 and {len(simulators) - 1}"
    simulator = simulators[target_index]
    name = connection.get("interface")
    if not _interfaces_named(simulator=simulator, name=name):
        hint = did_you_mean(name=str(name), known_names=_names_to_suggest(own_interface=own_interface, simulator=simulator))
        return f"simulator '{simulator['name']}' has no interface '{name}'" + (f".{hint}" if hint else "")
    return _problem_of_link(connection=connection, own_interface=own_interface, simulator=simulator, is_own_simulator=target_index == own_index)


def _names_to_suggest(own_interface: dict[str, Any], simulator: dict[str, Any]) -> list[str]:
    # an input takes its value from an output, and no interface is connected to itself
    return [
        interface["name"]
        for interface in simulator["interfaces"]
        if interface is not own_interface and not (_is_input(own_interface) and _is_input(interface))
    ]


def _target_index(raw_index: Any, simulator_count: int) -> int | None:
    try:
        index = int(raw_index)
    except (TypeError, ValueError):
        return None
    return index if 0 <= index < simulator_count else None


def _is_input(interface: dict[str, Any]) -> bool:
    return str(interface.get("type")).lower() == InterfaceType.INPUT.value


def _interfaces_named(simulator: dict[str, Any], name: Any) -> list[dict[str, Any]]:
    return [interface for interface in simulator["interfaces"] if interface["name"] == name]


def _problem_of_link(connection: dict[str, Any], own_interface: dict[str, Any], simulator: dict[str, Any], is_own_simulator: bool) -> str | None:
    name = connection.get("interface")
    targets = _interfaces_named(simulator=simulator, name=name)
    if is_own_simulator and name == own_interface["name"] and all(_is_input(target) == _is_input(own_interface) for target in targets):
        return "it is connected to itself"
    # the server ignores the connections of an output, which can name the input it feeds
    if not _is_input(own_interface):
        return None
    if all(_is_input(target) for target in targets):
        return f"interface '{name}' of simulator '{simulator['name']}' is an input, connect to an output"
    # the server never hands a client its own output directly, only through a logical delay
    return f"output '{name}' of its own simulator needs a logical delay" if is_own_simulator and not connection.get("delay_path") else None


def _problems_of_delay_path(connection: dict[str, Any], own_interface: dict[str, Any], own_simulator: str, delays: list[dict[str, Any]]) -> list[str]:
    delay_path = connection.get("delay_path", [])
    if not isinstance(delay_path, list):
        return [f"delay_path must be a list, not {type(delay_path).__name__}"]
    if not delay_path or not _is_input(own_interface):
        return []
    # the server finds a logical delay by its position, as text
    unknown = [entry for entry in delay_path if entry not in [str(position) for position in range(1, len(delays) + 1)]]
    if unknown:
        return [f"delay_path entry {entry!r} names no logical delay, the config has {len(delays)}, counted from '1'" for entry in unknown]
    named = [delays[int(entry) - 1] for entry in delay_path]
    return [] if _any_lists_input(named_delays=named, simulator=own_simulator, interface=own_interface["name"]) else [_NOT_LISTED]


def _any_lists_input(named_delays: list[dict[str, Any]], simulator: str, interface: str) -> bool:
    return any(
        connection.get("destination_simulator_name") == simulator and connection.get("destination_interface_name") == interface
        for delay in named_delays
        for connection in delay.get("output_connections") or []
    )
