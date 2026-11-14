from ecosim_common.tech.readable_count import readable_count

from ecosim.check.simulation_check import SimulationCheck
from ecosim.report_lines import length_line, simulator_lines, with_shown_paths
from ecosim.simulation_folder import SimulationFolder


def report_lines(check: SimulationCheck, simulation: SimulationFolder, check_command: str) -> list[str]:
    problems = check.findings.problems
    lines = [summary_line(check=check, simulation=simulation)]
    if check.length_is_known and check.simulation_config is not None:
        lines.append(length_line(simulation_config=check.simulation_config))
    lines += simulator_lines(simulators=check.simulators)
    lines += _section(title="Problems:", findings=problems)
    lines += _section(title="Warnings:", findings=check.findings.warnings)
    if problems:
        lines.append(f"Fix {'it' if len(problems) == 1 else 'them'} and run the check again: {check_command}")
    return [with_shown_paths(text=line) for line in lines]


def summary_line(check: SimulationCheck, simulation: SimulationFolder) -> str:
    """Like 'Checked building: 3 simulators, no problems.'"""
    counts = [] if check.simulator_count is None else [readable_count(count=check.simulator_count, noun="simulator")]
    counts.append(readable_count(count=len(check.findings.problems), noun="problem") if check.findings.problems else "no problems")
    if check.findings.warnings:
        counts.append(readable_count(count=len(check.findings.warnings), noun="warning"))
    return f"Checked {simulation.name}: {', '.join(counts)}."


def _section(title: str, findings: list[str]) -> list[str]:
    if not findings:
        return []
    # the lines after the first of a finding are indented further, so each finding stays one block
    return [title, *(f"  {line}" if index == 0 else f"    {line}" for finding in findings for index, line in enumerate(finding.splitlines()))]
