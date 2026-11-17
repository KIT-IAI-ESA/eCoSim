from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.config.simulator_directory import SimulatorDirectory, SimulatorDirectorySearch
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.config_parser import ConfigParserException
from ecosim_common.tech.close_name import closest_name
from ecosim_common.tech.one_line_errors import one_line_message
from ecosim_common_fmpy.config.simulator_client_type import client_type_of

from ecosim.check.findings import Findings, problem_of_ini_file
from ecosim.report_lines import and_joined


@dataclass(frozen=True)
class SimulatorDirectoryCheck:
    client_types: dict[ClientID, tuple[SimulatorDirectory, ClientType]]
    findings: Findings

    @staticmethod
    def of_directory(simulator_dir: Path, client_ids: list[ClientID], simulation_config_file: Path) -> SimulatorDirectoryCheck:
        if not simulator_dir.is_dir():
            problem = f"{simulator_dir} does not exist. Pass --simulator-dir if the folders of the simulators are somewhere else."
            return SimulatorDirectoryCheck(client_types={}, findings=Findings(problems=[problem]))
        search = SimulatorDirectorySearch.of(simulators_directory=simulator_dir, client_ids=client_ids)
        findings = Findings(problems=[_problem_of_unreadable(path=path, reason=reason) for path, reason in search.unreadable.items()])
        findings.add(_findings_of_unconfigured(search=search, simulation_config_file=simulation_config_file, simulator_dir=simulator_dir))
        findings.problems += [_problem_of_shared(client_id=client_id, directories=directories) for client_id, directories in search.shared.items()]
        client_types = {}
        for directory in [*search.found.values(), *search.without_model]:
            try:
                client_types[directory.client_id] = (directory, client_type_of(simulator_directory=directory))
            except ValueError as error:
                findings.problems.append(str(error))
            except Exception as error:
                findings.problems.append(_problem_of_unreadable_model(directory=directory, error=error))
        return SimulatorDirectoryCheck(client_types=client_types, findings=findings)


def _problem_of_unreadable_model(directory: SimulatorDirectory, error: Exception) -> str:
    # for example a git-lfs pointer instead of the FMU
    reason = error.args[0] if isinstance(error, KeyError) and error.args else one_line_message(error=error)
    return f"{directory.model_files()[0]} cannot be read: {reason}"


def _problem_of_unreadable(path: Path, reason: str) -> str:
    ini_files = sorted(path.glob("*.ini"))
    error = _error_of_reading(ini_file=ini_files[0]) if len(ini_files) == 1 else None
    # only the error has the missing section and key as fields
    return problem_of_ini_file(error=error, ini_file=ini_files[0]) if isinstance(error, ConfigParserException) else reason


def _error_of_reading(ini_file: Path) -> Exception | None:
    try:
        SimulatorDirectory.of_ini_file(ini_file=ini_file)
    except Exception as error:
        return error
    return None


def _findings_of_unconfigured(search: SimulatorDirectorySearch, simulation_config_file: Path, simulator_dir: Path) -> Findings:
    findings = Findings()
    # an unreadable folder with the name of a missing simulator explains it
    explained = [client_id for client_id in search.missing if client_id.simulator_name in [path.name for path in search.unreadable]]
    for directory in search.unconfigured:
        missing = _missing_simulator_close_to(client_id=directory.client_id, missing=search.missing)
        if missing is None:
            findings.warnings.append(f"{directory.path} is not used. {simulation_config_file} has no simulator {directory.client_id.simulator_name}.")
            continue
        explained.append(missing)
        findings.problems.append(_problem_of_typo(directory=directory, missing=missing, simulation_config_file=simulation_config_file))
    findings.problems += [
        _problem_of_missing(client_id=client_id, simulation_config_file=simulation_config_file, simulator_dir=simulator_dir)
        for client_id in search.missing
        if client_id not in explained
    ]
    return findings


def _problem_of_missing(client_id: ClientID, simulation_config_file: Path, simulator_dir: Path) -> str:
    ini_file_text = f"an ini file whose simulator_name is {client_id.simulator_name} and whose model_name is {client_id.model_name}"
    simulator_directory_path = simulator_dir / client_id.simulator_name
    if simulator_directory_path.is_dir() and not any(simulator_directory_path.glob("*.ini")):
        return f"{simulator_directory_path} has no ini file. Add {ini_file_text}."
    return f"{simulation_config_file}: simulator {client_id.simulator_name} has no folder in {simulator_dir}. Add a folder with {ini_file_text}."


def _missing_simulator_close_to(client_id: ClientID, missing: list[ClientID]) -> ClientID | None:
    same_simulator = [missing_id for missing_id in missing if missing_id.simulator_name == client_id.simulator_name]
    if same_simulator:
        return same_simulator[0]
    closest = closest_name(name=client_id.simulator_name, known_names=[missing_id.simulator_name for missing_id in missing])
    return next((missing_id for missing_id in missing if missing_id.simulator_name == closest), None)


def _problem_of_typo(directory: SimulatorDirectory, missing: ClientID, simulation_config_file: Path) -> str:
    ini_file = directory.config_parser.config_file
    if directory.client_id.simulator_name == missing.simulator_name:
        return (
            f"{ini_file}: model_name is '{directory.client_id.model_name}', "
            + f"but simulator {missing.simulator_name} in {simulation_config_file} has the model {missing.model_name}."
        )
    name = directory.client_id.simulator_name
    return f"{ini_file}: simulator_name is '{name}', but {simulation_config_file} has no simulator '{name}'. Did you mean {missing.simulator_name}?"


def _problem_of_shared(client_id: ClientID, directories: list[SimulatorDirectory]) -> str:
    paths = [str(directory.path) for directory in directories]
    both_or_all = "both" if len(paths) == 2 else "all"
    return f"{and_joined(texts=paths)} are {both_or_all} for simulator {client_id.simulator_name}. Keep one of them."
